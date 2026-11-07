import json
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parents[1]
POLICY_DIR = BASE_DIR / "data" / "policies"
OUTPUT_DIR = BASE_DIR / "outputs"

# Chunking configuration
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


def chunk_document(file_path, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split one policy document into overlapping word-based chunks.

    Each chunk contains at most 40 words.
    Consecutive chunks overlap by 10 words.
    """

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

        # Stop after the first chunk that reaches the document's end.
        if end >= len(words):
            break

        start += step

    return chunks


def chunk_all_documents():
    """
    Read all five policy documents and combine their chunks.
    """

    all_chunks = []

    for filename in EXPECTED_CHUNK_COUNTS:
        file_path = POLICY_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Required policy document not found: {file_path}"
            )

        document_chunks = chunk_document(file_path)

        expected = EXPECTED_CHUNK_COUNTS[filename]

        if len(document_chunks) != expected:
            raise AssertionError(
                f"{filename}: expected {expected} chunks, "
                f"but generated {len(document_chunks)}"
            )

        all_chunks.extend(document_chunks)

    return all_chunks


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chunks = chunk_all_documents()

    output_path = OUTPUT_DIR / "policy_chunks.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=4, ensure_ascii=False)

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

    assert len(chunks) == 15, "Total chunk count should be 15."

    print("\nTASK 1 CHECKS PASSED")


if __name__ == "__main__":
    main()
