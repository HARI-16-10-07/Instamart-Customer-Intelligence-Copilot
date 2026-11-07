
import sys
import json
import csv
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# 1. PROJECT DIRECTORIES AND IMPORTS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

# Make the project root available so mock_llm.py can be imported.
sys.path.insert(0, str(BASE_DIR))

import mock_llm


POLICY_DIR = BASE_DIR / "data" / "policies"
OUTPUT_DIR = BASE_DIR / "outputs"


# ============================================================
# 2. CHUNKING CONFIGURATION
# ============================================================

CHUNK_SIZE = 40
CHUNK_OVERLAP = 10
CHUNK_STEP = CHUNK_SIZE - CHUNK_OVERLAP

EXPECTED_CHUNK_COUNTS = {
    "refund_policy.txt": 4,
    "delivery_policy.txt": 3,
    "escalation_policy.txt": 3,
    "payment_policy.txt": 3,
    "privacy_policy.txt": 2,
}


# ============================================================
# 3. TASK 1 - DOCUMENT CHUNKING
# ============================================================

def chunk_document(file_path, chunk_size=CHUNK_SIZE,
                   overlap=CHUNK_OVERLAP):
    """
    Split one policy document into word-based chunks.

    Normal configuration:
        Chunk size = 40 words
        Overlap = 10 words
        Step = 30 words
    """

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Overlap must be between 0 and chunk_size - 1."
        )

    text = file_path.read_text(encoding="utf-8")
    words = text.split()

    chunks = []

    step = chunk_size - overlap
    start = 0

    while start < len(words):

        end = min(start + chunk_size, len(words))

        chunk_text = " ".join(words[start:end])

        chunks.append({
            "source": file_path.name,
            "start_word": start,
            "end_word": end - 1,
            "text": chunk_text
        })

        # Stop after the first chunk reaches the document end.
        if end >= len(words):
            break

        start += step

    return chunks


def chunk_all_documents(overlap=CHUNK_OVERLAP):
    """
    Read all five policy documents and combine their chunks.

    Expected chunk counts are checked only for the normal
    10-word-overlap configuration.
    """

    all_chunks = []

    for filename in EXPECTED_CHUNK_COUNTS:

        file_path = POLICY_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required policy document not found: {file_path}"
            )

        document_chunks = chunk_document(
            file_path,
            chunk_size=CHUNK_SIZE,
            overlap=overlap
        )

        # Expected counts apply to the normal 10-word overlap only.
        if overlap == CHUNK_OVERLAP:

            expected = EXPECTED_CHUNK_COUNTS[filename]

            if len(document_chunks) != expected:
                raise AssertionError(
                    f"{filename}: expected {expected} chunks, "
                    f"but generated {len(document_chunks)}"
                )

        all_chunks.extend(document_chunks)

    return all_chunks


# ============================================================
# 4. TASK 2 - TF-IDF RETRIEVAL
# ============================================================

CHUNKS = None
VECTORIZER = None
CHUNK_MATRIX = None


def build_retriever(overlap=CHUNK_OVERLAP):
    """
    Build the TF-IDF retrieval system.

    The overlap parameter allows us to compare:
        10-word overlap
        Zero overlap
    """

    global CHUNKS, VECTORIZER, CHUNK_MATRIX

    CHUNKS = chunk_all_documents(overlap=overlap)

    VECTORIZER = TfidfVectorizer()

    CHUNK_MATRIX = VECTORIZER.fit_transform(
        [chunk["text"] for chunk in CHUNKS]
    )


def retrieve(query, k=3):
    """
    Retrieve the k most relevant policy chunks.

    Returns a list of dictionaries containing:
        source
        score
        text
    """

    global CHUNKS, VECTORIZER, CHUNK_MATRIX

    if VECTORIZER is None or CHUNK_MATRIX is None:
        build_retriever()

    query_vector = VECTORIZER.transform([query])

    similarities = cosine_similarity(
        query_vector,
        CHUNK_MATRIX
    ).flatten()

    # Rank chunks by similarity, highest first.
    ranked_indices = sorted(
        range(len(similarities)),
        key=lambda index: (-similarities[index], index)
    )

    results = []

    for index in ranked_indices[:k]:

        results.append({
            "source": CHUNKS[index]["source"],
            "score": float(similarities[index]),
            "text": CHUNKS[index]["text"]
        })

    return results


# ============================================================
# 5. TASK 3 - POLICY QUESTION ANSWERING
# ============================================================

def answer(question):
    """
    Answer a policy question using exactly three retrieved chunks.

    Sends exactly two messages to mock_llm.chat:
        1. System message
        2. User message

    Returns:
        Model-generated answer
        Source filenames used
    """

    # Retrieve exactly three chunks.
    retrieved_chunks = retrieve(question, k=3)

    # Prepare context with source filenames.
    context_parts = []

    for chunk in retrieved_chunks:

        context_parts.append(
            f"[{chunk['source']}]\n{chunk['text']}"
        )

    context = "\n".join(context_parts)

    # Required user message format.
    user_message = (
        "CONTEXT:\n"
        + context
        + "\nQUESTION:\n"
        + question
    )

    # System instruction.
    system_message = (
        "POLICY ASSISTANT\n"
        "You are a policy assistant for Swiggy Instamart support.\n"
        "Answer the user's question using only the supplied policy context.\n"
        "Do not use outside knowledge or invent policy information.\n"
        "If the supplied context does not contain the answer, "
        "respond with a sentence beginning exactly: "
        "'I could not find the information in the supplied policies.'"
    )

    # Exactly two messages are sent to the model.
    messages = [
        {
            "role": "system",
            "content": system_message
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    response = mock_llm.chat(messages)

    answer_text = response.choices[0].message.content

    # Collect unique source filenames in retrieval order.
    sources = list(dict.fromkeys(
        chunk["source"] for chunk in retrieved_chunks
    ))

    return answer_text, sources


# ============================================================
# 6. TASK 4 - POLICY RETRIEVAL EVALUATION
# ============================================================

def evaluate_policy_retrieval():
    """
    Evaluate retrieval and answer grounding using policy_eval.csv.
    """

    evaluation_file = (
        BASE_DIR / "data" / "raw" / "policy_eval.csv"
    )

    if not evaluation_file.exists():
        raise FileNotFoundError(
            f"Evaluation file not found: {evaluation_file}"
        )

    with open(
        evaluation_file,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        questions = list(csv.DictReader(file))

    answerable_doc_correct = 0
    answerable_fact_correct = 0
    unanswerable_fallback_correct = 0

    answerable_total = 0
    unanswerable_total = 0

    failures = []

    for row in questions:

        question = row["question"].strip()
        expected_doc = row["expected_doc"].strip()
        expected_fact = row["expected_fact"].strip()

        # Retrieve top three chunks.
        retrieved = retrieve(question, k=3)

        retrieved_sources = [
            item["source"] for item in retrieved
        ]

        # Generate policy answer.
        answer_text, sources_used = answer(question)

        if expected_doc != "NONE":

            answerable_total += 1

            # Check expected document in top three.
            if expected_doc in retrieved_sources:
                answerable_doc_correct += 1

            # Check exact, case-sensitive expected fact.
            if expected_fact in answer_text:
                answerable_fact_correct += 1

            else:
                failures.append({
                    "question": question,
                    "expected_doc": expected_doc,
                    "expected_fact": expected_fact,
                    "answer": answer_text,
                    "retrieved": retrieved
                })

        else:

            unanswerable_total += 1

            # Check whether the answer starts with the fallback.
            if answer_text.strip().startswith("I could not find"):
                unanswerable_fallback_correct += 1

            else:
                failures.append({
                    "question": question,
                    "expected_doc": "NONE",
                    "expected_fact": "",
                    "answer": answer_text,
                    "retrieved": retrieved
                })

    results = {
        "answerable_document_correct": answerable_doc_correct,
        "answerable_total": answerable_total,
        "answerable_fact_correct": answerable_fact_correct,
        "unanswerable_fallback_correct": (
            unanswerable_fallback_correct
        ),
        "unanswerable_total": unanswerable_total,
        "failures": failures
    }

    return results


def print_evaluation_results(title, results):
    """
    Print evaluation metrics in a readable format.
    """

    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)

    print(
        "Expected document in top 3:",
        f"{results['answerable_document_correct']}/"
        f"{results['answerable_total']}"
    )

    print(
        "Expected fact in answer:",
        f"{results['answerable_fact_correct']}/"
        f"{results['answerable_total']}"
    )

    print(
        "Unanswerable questions with fallback:",
        f"{results['unanswerable_fallback_correct']}/"
        f"{results['unanswerable_total']}"
    )

    if results["failures"]:

        print("\nFAILED QUESTIONS:")

        for number, failure in enumerate(
            results["failures"],
            start=1
        ):

            print(f"\nFailure {number}")
            print("Question:", failure["question"])
            print("Expected document:", failure["expected_doc"])
            print("Expected fact:", failure["expected_fact"])
            print("Generated answer:", failure["answer"])

            if failure["expected_doc"] != "NONE":

                print("Retrieved chunk sources:")

                for item in failure["retrieved"]:

                    print(
                        f"- {item['source']} "
                        f"(score: {item['score']:.4f})"
                    )

    else:
        print("\nNo failed questions.")


def run_task4_evaluation():
    """
    Compare normal overlapping chunks with zero-overlap chunks.
    """

    # --------------------------------------------------------
    # Evaluation 1: Normal 10-word overlap
    # --------------------------------------------------------

    print("\nRunning evaluation with 10-word overlap...")

    build_retriever(overlap=CHUNK_OVERLAP)

    normal_results = evaluate_policy_retrieval()

    print_evaluation_results(
        "TASK 4 - NORMAL OVERLAP (10 WORDS)",
        normal_results
    )

    # --------------------------------------------------------
    # Evaluation 2: Zero overlap
    # --------------------------------------------------------

    print("\nRunning evaluation with zero overlap...")

    build_retriever(overlap=0)

    zero_overlap_results = evaluate_policy_retrieval()

    print_evaluation_results(
        "TASK 4 - ZERO OVERLAP",
        zero_overlap_results
    )

    # Restore normal retriever for later Part D tasks.
    build_retriever(overlap=CHUNK_OVERLAP)

    return normal_results, zero_overlap_results


# ============================================================
# 7. MAIN PROGRAM - TASKS 1 TO 4
# ============================================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # TASK 1 - Chunk documents
    # --------------------------------------------------------

    chunks = chunk_all_documents()

    # --------------------------------------------------------
    # TASK 2 - Build TF-IDF retrieval system
    # --------------------------------------------------------

    build_retriever()

    print("\nTF-IDF RETRIEVAL TEST")
    print("-" * 55)

    query = "refund policy late delivery"

    results = retrieve(query, k=3)

    print("Query:", query)
    print("\nTOP 3 RETRIEVED CHUNKS:")

    for rank, result in enumerate(results, start=1):

        print(f"\nRank {rank}")
        print("Source:", result["source"])
        print("Similarity score:", round(result["score"], 4))
        print("Text:", result["text"])

    # Save chunks to JSON.
    output_path = OUTPUT_DIR / "policy_chunks.json"

    with output_path.open("w", encoding="utf-8") as file:

        json.dump(
            chunks,
            file,
            indent=4,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # TASK 3 - Policy assistant test
    # --------------------------------------------------------

    print("\nPOLICY ASSISTANT TEST")
    print("-" * 55)

    question = "What is the refund rule for late delivery?"

    policy_answer, sources = answer(question)

    print("Question:", question)
    print("\nANSWER:")
    print(policy_answer)

    print("\nSOURCES USED:")

    for source in sources:
        print("-", source)

    # --------------------------------------------------------
    # TASK 1 - Display chunking results
    # --------------------------------------------------------

    print("\nPOLICY CHUNKING RESULTS")
    print("-" * 55)

    for filename, expected_count in EXPECTED_CHUNK_COUNTS.items():

        actual_count = sum(
            1 for chunk in chunks
            if chunk["source"] == filename
        )

        print(
            f"{filename:<25} "
            f"Expected: {expected_count} | Actual: {actual_count}"
        )

    print("-" * 55)
    print("Total documents:", len(EXPECTED_CHUNK_COUNTS))
    print("Total chunks:", len(chunks))
    print("Chunk size:", CHUNK_SIZE, "words")
    print("Overlap:", CHUNK_OVERLAP, "words")
    print("Step between chunks:", CHUNK_STEP, "words")

    print("\nCHUNK BOUNDARIES")

    for index, chunk in enumerate(chunks, start=1):

        print(
            f"{index:02d}. {chunk['source']:<25} "
            f"words {chunk['start_word']}-{chunk['end_word']} "
            f"({len(chunk['text'].split())} words)"
        )

    print("\nSaved chunks to:", output_path)

    assert len(chunks) == 15, (
        "Total chunk count should be 15."
    )

    print("\nTASK 1 CHECKS PASSED")

    # --------------------------------------------------------
    # TASK 4 - Evaluate retrieval and grounding
    # --------------------------------------------------------

    normal_results, zero_overlap_results = (
        run_task4_evaluation()
    )

    print("\nTASK 4 EVALUATION COMPLETED")

    # The normal configuration is restored by run_task4_evaluation.


if __name__ == "__main__":
    main()
