
import re
import json
import pandas as pd
import sys
from pathlib import Path

# Add the project root to Python's module search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import mock_llm

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

INPUT_FILE = "data/raw/tickets.csv"
MAX_INPUT_TOKENS = 400

ALLOWED_CATEGORIES = {
    "billing",
    "delivery",
    "technical",
    "fraud"
}

# ---------------------------------------------------------
# PRIVACY REDACTION PATTERNS
# Apply them in the instructor's exact order.
# ---------------------------------------------------------

EMAIL_PATTERN = r"[\w.+-]+@[\w-]+\.[\w.]+"
PHONE_PATTERN = r"\b[6-9]\d{9}\b"
ORDER_PATTERN = r"ORD-\d{6}"


def redact_ticket(text):
    """
    Redact email addresses, phone numbers and order IDs.
    Return the redacted text and substitution counts.
    """

    text = str(text)

    text, email_count = re.subn(
        EMAIL_PATTERN, "[EMAIL]", text
    )

    text, phone_count = re.subn(
        PHONE_PATTERN, "[PHONE]", text
    )

    text, order_count = re.subn(
        ORDER_PATTERN, "[ORDER_ID]", text
    )

    counts = {
        "emails": email_count,
        "phones": phone_count,
        "order_ids": order_count
    }

    return text, counts


def contains_personal_information(text):
    """
    Return True if any protected pattern remains.
    """

    patterns = [
        EMAIL_PATTERN,
        PHONE_PATTERN,
        ORDER_PATTERN
    ]

    return any(
        re.search(pattern, text) is not None
        for pattern in patterns
    )

# ---------------------------------------------------------
# CLASSIFICATION PROMPTS
# ---------------------------------------------------------

ZERO_SHOT_PROMPT = """
CLASSIFY the customer's support ticket.

Choose exactly one category from:
- billing
- delivery
- technical
- fraud

Return only valid JSON in this exact format:
{"category": "...", "reason": "..."}

Do not include Markdown, explanations outside JSON, or any
category other than the four allowed categories.
"""

FEW_SHOT_PROMPT = """
CLASSIFY the customer's support ticket.

Choose exactly one category from:
- billing
- delivery
- technical
- fraud

EXAMPLES:
Ticket: I was charged twice for the same order.
JSON: {"category": "billing", "reason": "duplicate charge"}

Ticket: My account was hacked and someone placed an order.
JSON: {"category": "fraud", "reason": "unauthorized account activity"}

Ticket: The rider marked my order delivered, but I did not receive it.
JSON: {"category": "delivery", "reason": "order not received"}

Return only valid JSON in this exact format:
{"category": "...", "reason": "..."}

Do not include Markdown, explanations outside JSON, or any
category other than the four allowed categories.
"""


# Check the prompt requirements
assert "CLASSIFY" in ZERO_SHOT_PROMPT
assert "CLASSIFY" in FEW_SHOT_PROMPT

for category in ALLOWED_CATEGORIES:
    assert category in ZERO_SHOT_PROMPT
    assert category in FEW_SHOT_PROMPT

assert "EXAMPLES:" not in ZERO_SHOT_PROMPT
assert "EXAMPLES:" in FEW_SHOT_PROMPT

print("\nClassification prompts validated.")


# ---------------------------------------------------------
# RETRY CONFIGURATION
# ---------------------------------------------------------

import random
import time

BASE_DELAY = 0.05
MAX_RETRIES = 3


def call_with_retry(messages, ticket_id):
    """
    Call the mock LLM.
    Retry transient errors up to three times.
    """

    for retry_number in range(MAX_RETRIES + 1):

        try:
            response = mock_llm.chat(messages)
            return response

        except mock_llm.TransientLLMError:

            # No more retries after the third retry
            if retry_number == MAX_RETRIES:
                raise

            wait_time = (
                BASE_DELAY
                * (2 ** retry_number)
                * random.uniform(0.9, 1.15)
            )

            print(
                f"RETRY | ticket_id={ticket_id} | "
                f"retry={retry_number} | "
                f"wait={wait_time:.5f}s"
            )

            time.sleep(wait_time)

# ---------------------------------------------------------
# MODEL OUTPUT VALIDATION
# ---------------------------------------------------------

def validate_response(response_text):
    """
    Validate the model response.

    Returns:
        category, status
    """

    # First attempt: parse as JSON
    try:
        parsed = json.loads(response_text)

        # Valid JSON with an allowed category
        if (
            isinstance(parsed, dict)
            and parsed.get("category") in ALLOWED_CATEGORIES
        ):
            return parsed["category"], "classified_json"

        # Valid JSON, but category is not allowed
        return "", "flagged_invalid_output"

    except (json.JSONDecodeError, TypeError):

        # Invalid JSON: extract lowercase words
        words = re.findall(
            r"[a-z]+",
            response_text.lower()
        )

        # Find allowed category words
        matched_categories = [
            word for word in words
            if word in ALLOWED_CATEGORIES
        ]

        # Accept only when exactly one category is found
        if len(matched_categories) == 1:
            return matched_categories[0], "classified_keyword"

        return "", "flagged_invalid_output"

# ---------------------------------------------------------
# LOAD TICKETS
# ---------------------------------------------------------

tickets = pd.read_csv(
    INPUT_FILE,
    keep_default_na=False
)

print("Total tickets loaded:", len(tickets))


# ---------------------------------------------------------
# INPUT GUARDRAILS AND REDACTION
# ---------------------------------------------------------

processed_tickets = []

total_emails = 0
total_phones = 0
total_order_ids = 0

for _, row in tickets.iterrows():

    ticket_id = row["ticket_id"]
    original_text = row["text"]

    # Guardrail 1: Empty ticket
    if not original_text.strip():

        processed_tickets.append({
            "ticket_id": ticket_id,
            "customer_id": row["customer_id"],
            "true_category": row["true_category"],
            "original_text": original_text,
            "redacted_text": "",
            "status": "skipped_empty"
        })

        continue

    # Guardrail 2: Long ticket
    estimated_tokens = mock_llm.est_tokens(original_text)

    if estimated_tokens > MAX_INPUT_TOKENS:

        processed_tickets.append({
            "ticket_id": ticket_id,
            "customer_id": row["customer_id"],
            "true_category": row["true_category"],
            "original_text": original_text,
            "redacted_text": "",
            "status": "flagged_long"
        })

        continue

    # Redact personal information
    redacted_text, counts = redact_ticket(original_text)

    total_emails += counts["emails"]
    total_phones += counts["phones"]
    total_order_ids += counts["order_ids"]

    # Privacy assertion
    assert not contains_personal_information(redacted_text), (
        f"Personal information remains in ticket {ticket_id}"
    )

    processed_tickets.append({
        "ticket_id": ticket_id,
        "customer_id": row["customer_id"],
        "true_category": row["true_category"],
        "original_text": original_text,
        "redacted_text": redacted_text,
        "status": "ready"
    })


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("\nINPUT GUARDRAIL RESULTS")

status_counts = pd.Series(
    [ticket["status"] for ticket in processed_tickets]
).value_counts()

print(status_counts)

print("\nPRIVACY REDACTION RESULTS")

print("Emails redacted:", total_emails)
print("Phones redacted:", total_phones)
print("Order IDs redacted:", total_order_ids)

total_redactions = (
    total_emails + total_phones + total_order_ids
)

print("Total substitutions:", total_redactions)

# Verify all eligible redacted tickets again
eligible_tickets = [
    ticket for ticket in processed_tickets
    if ticket["status"] == "ready"
]

remaining_personal_info = sum(
    contains_personal_information(ticket["redacted_text"])
    for ticket in eligible_tickets
)

assert remaining_personal_info == 0

print("Personal information remaining:", remaining_personal_info)

print("\nStep 5 completed successfully.")


def estimate_classification_call_tokens(messages):
    """
    Estimate the maximum possible token usage of one
    classification call using the instructor's mock LLM.

    Includes both prompt tokens and completion tokens.
    """

    # Calculate prompt tokens exactly as mock_llm does.
    prompt_tokens = sum(
        mock_llm.est_tokens(
            message.get("content") or ""
        )
        for message in messages
    )

    # Possible responses generated by mock_llm._classify().
    possible_responses = []

    categories = [
        "fraud",
        "technical",
        "billing",
        "delivery"
    ]

    for category in categories:

        # Normal JSON response
        possible_responses.append(
            json.dumps({
                "category": category,
                "reason": "keyword match"
            })
        )

        # Chatty non-JSON response
        possible_responses.append(
            f"The customer appears to have a {category}-related problem."
        )

    # Invalid-category JSON response
    possible_responses.append(
        json.dumps({
            "category": "shipping",
            "reason": "parcel movement"
        })
    )

    # Find the largest possible completion token count.
    maximum_completion_tokens = max(
        mock_llm.est_tokens(response)
        for response in possible_responses
    )

    return prompt_tokens + maximum_completion_tokens
# ---------------------------------------------------------
# FULL CLASSIFICATION PIPELINE
# ---------------------------------------------------------

def run_classification(prompt, run_name, token_budget=None):

    # Reset mock model immediately before every full run
    mock_llm.reset()

    results = []
    running_total_tokens = 0

    print(f"\n{'=' * 60}")
    print(f"STARTING {run_name.upper()} CLASSIFICATION")
    print(f"{'=' * 60}")

    for ticket in processed_tickets:

        ticket_id = ticket["ticket_id"]

        # Preserve tickets rejected by input guardrails
        if ticket["status"] != "ready":

            results.append({
                **ticket,
                "category": "",
                "tokens_used": 0
            })

            continue

        # Check whether the NEXT complete model call fits
        # within the remaining token budget.

        redacted_text = ticket["redacted_text"]

        messages = [
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": redacted_text
            }
        ]

        estimated_call_tokens = estimate_classification_call_tokens(
            messages
        )

        if (
            token_budget is not None
            and running_total_tokens + estimated_call_tokens > token_budget
        ):

            results.append({
                **ticket,
                "status": "budget_exhausted",
                "category": "",
                "tokens_used": 0
            })

            continue

       # Privacy assertion before every model call
        assert not contains_personal_information(redacted_text)

        # User message contains ONLY redacted ticket text
        assert messages[-1]["content"] == redacted_text

        assert messages[-1]["content"] == redacted_text

        # Call model with retry protection
        response = call_with_retry(messages, ticket_id)

        # Extract model response and token usage
        response_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        running_total_tokens += tokens_used
        # Strict token-budget verification
        if token_budget is not None:
            assert running_total_tokens <= token_budget, (
                f"Token budget exceeded: "
                f"{running_total_tokens} > {token_budget}"
            )
        # Validate model output
        category, classification_status = validate_response(
            response_text
        )

        results.append({
            **ticket,
            "status": classification_status,
            "category": category,
            "tokens_used": tokens_used
        })

    results_df = pd.DataFrame(results)

    print(f"\n{run_name} RESULTS")
    print("Tickets processed:", len(results_df))
    print("Total model tokens:", running_total_tokens)

    print("\nCLASSIFICATION STATUS COUNTS")
    print(results_df["status"].value_counts())

    classified_df = results_df[
        results_df["status"].isin([
            "classified_json",
            "classified_keyword"
        ])
    ]

    print("\nClassified tickets:", len(classified_df))

    if len(classified_df) > 0:

        accuracy = (
            classified_df["category"]
            == classified_df["true_category"]
        ).mean() * 100

        print(f"Accuracy: {accuracy:.2f}%")

        print(
            "Tokens per classified ticket:",
            round(running_total_tokens / len(classified_df), 2)
        )

    return results_df, running_total_tokens


# ---------------------------------------------------------
# ZERO-SHOT AND FEW-SHOT COMPARISON
# ---------------------------------------------------------

zero_shot_results, zero_shot_tokens = run_classification(
    ZERO_SHOT_PROMPT,
    "Zero-shot"
)

few_shot_results, few_shot_tokens = run_classification(
    FEW_SHOT_PROMPT,
    "Few-shot"
)

# ---------------------------------------------------------
# ZERO-SHOT CONFUSION TABLE AND PROMPT COMPARISON
# ---------------------------------------------------------

zero_shot_classified = zero_shot_results[
    zero_shot_results["status"].isin([
        "classified_json",
        "classified_keyword"
    ])
]

confusion_table = pd.crosstab(
    zero_shot_classified["true_category"],
    zero_shot_classified["category"]
)

category_order = [
    "billing",
    "delivery",
    "technical",
    "fraud"
]

confusion_table = confusion_table.reindex(
    index=category_order,
    columns=category_order,
    fill_value=0
)

print("\nZERO-SHOT CONFUSION TABLE")
print(confusion_table)

print("\nPROMPT COMPARISON")
print("Zero-shot total tokens:", zero_shot_tokens)
print("Few-shot total tokens:", few_shot_tokens)

extra_tokens = few_shot_tokens - zero_shot_tokens

print("Additional tokens used by few-shot:", extra_tokens)

print(
    "Additional tokens per classified ticket:",
    round(extra_tokens / 147, 2)
)

print(
    "Few-shot token increase (%):",
    round((extra_tokens / zero_shot_tokens) * 100, 2)
)

# ---------------------------------------------------------
# TOKEN BUDGET DEMONSTRATION
# ---------------------------------------------------------

TOKEN_BUDGET = 6000

budget_results, budget_total_tokens = run_classification(
    ZERO_SHOT_PROMPT,
    "Zero-shot budget demonstration",
    token_budget=TOKEN_BUDGET
)

Path("outputs").mkdir(parents=True, exist_ok=True)

budget_results.to_csv(
    "outputs/triage_budget_demo.csv",
    index=False
)

print("\nTOKEN BUDGET SUMMARY")
print("Configured token budget:", TOKEN_BUDGET)
print("Actual tokens consumed:", budget_total_tokens)

print("\nBUDGET STATUS COUNTS")
print(budget_results["status"].value_counts())

print("\nBudget demonstration saved:")
print("outputs/triage_budget_demo.csv")

assert "budget_exhausted" in budget_results["status"].values

print("\nTOKEN BUDGET TEST PASSED")


# ---------------------------------------------------------
# FINAL FEW-SHOT CLASSIFICATION AND CUSTOMER ROUTING
# ---------------------------------------------------------

print("\nFINAL PART C CLASSIFICATION AND ROUTING")

# Run few-shot classification with the required large budget
final_results, final_total_tokens = run_classification(
    FEW_SHOT_PROMPT,
    "Final few-shot classification",
    token_budget=100000
)

# Load customer segments generated by Part B
segments = pd.read_csv("outputs/customer_segments.csv")

# Keep only the fields needed for ticket routing
segments = segments[
    ["customer_id", "segment_name", "is_premium"]
].copy()

# Convert premium indicator safely to Boolean
segments["is_premium"] = (
    segments["is_premium"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

# Attach customer segment information to each ticket
final_results = final_results.merge(
    segments,
    on="customer_id",
    how="left"
)

# Missing segment means the customer is not premium
final_results["is_premium"] = (
    final_results["is_premium"].fillna(False)
)

final_results["segment_name"] = (
    final_results["segment_name"].fillna("")
)

# Default routing
final_results["priority"] = "NORMAL"
final_results["route"] = "human_review"

# Identify tickets that require human review
human_review_statuses = [
    "skipped_empty",
    "flagged_long",
    "flagged_invalid_output",
    "budget_exhausted"
]

needs_human_review = final_results["status"].isin(
    human_review_statuses
)

# Fraud tickets go to the security team
fraud_tickets = (
    ~needs_human_review
    & (final_results["category"] == "fraud")
)

final_results.loc[fraud_tickets, "route"] = "security_team"
final_results.loc[fraud_tickets, "priority"] = "HIGH"

# Other premium customers go to the premium desk
premium_tickets = (
    ~needs_human_review
    & (final_results["category"] != "fraud")
    & final_results["is_premium"]
)

final_results.loc[premium_tickets, "route"] = "premium_desk"
final_results.loc[premium_tickets, "priority"] = "HIGH"

# All remaining classified tickets go to the support queue
support_tickets = (
    ~needs_human_review
    & (final_results["category"] != "fraud")
    & (~final_results["is_premium"])
)

final_results.loc[support_tickets, "route"] = "support_queue"

# Select the exact columns required by the instructor
required_columns = [
    "ticket_id",
    "customer_id",
    "status",
    "category",
    "segment_name",
    "priority",
    "route",
    "tokens_used"
]

final_output = final_results[required_columns].copy()

# Save final Part C output
final_output.to_csv(
    "outputs/triage_results.csv",
    index=False
)

# ---------------------------------------------------------
# FINAL OUTPUT VALIDATION
# ---------------------------------------------------------

print("\nFINAL ROUTING COUNTS")
print(final_output["route"].value_counts())

print("\nFINAL PRIORITY COUNTS")
print(final_output["priority"].value_counts())

print("\nFINAL STATUS COUNTS")
print(final_output["status"].value_counts())

print("\nFINAL OUTPUT SHAPE:", final_output.shape)
print("FINAL OUTPUT COLUMNS:", final_output.columns.tolist())

assert len(final_output) == 164
assert final_output.columns.tolist() == required_columns

assert not final_output[
    ["ticket_id", "customer_id", "status", "priority", "route"]
].isnull().any().any()

assert final_output.loc[
    final_output["status"].isin(human_review_statuses),
    "route"
].eq("human_review").all()

assert final_output.loc[
    final_output["status"].isin(human_review_statuses),
    "priority"
].eq("NORMAL").all()

assert final_output.loc[
    final_output["category"] == "fraud",
    "route"
].eq("security_team").all()

print("\nFinal few-shot tokens used:", final_total_tokens)
print("Saved: outputs/triage_results.csv")
print("\nALL FINAL PART C CHECKS PASSED")
