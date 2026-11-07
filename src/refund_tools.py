
import sys
import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# 1. PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

# Allow imports from the project root.
sys.path.insert(0, str(BASE_DIR))

DB_PATH = BASE_DIR / "data" / "instamart.db"
OUTPUT_DIR = BASE_DIR / "outputs"
REFUND_LEDGER = OUTPUT_DIR / "refund_ledger.jsonl"


# Reuse the existing Part D policy retrieval implementation.
from src.policy_rag import retrieve


# ============================================================
# 2. TOOL 1 - GET ORDER
# ============================================================

def get_order(order_id):
    """
    Retrieve an order from the existing Part A SQLite database.

    Returns:
        order_id
        status
        order_amount
        delivery_minutes

    If the order does not exist, returns an error dictionary.
    """

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                order_id,
                status,
                order_amount,
                delivery_minutes
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return {"error": "order not found"}

        return {
            "order_id": row[0],
            "status": row[1],
            "order_amount": float(row[2]),
            "delivery_minutes": (
                float(row[3]) if row[3] is not None else None
            )
        }

    finally:
        connection.close()


# ============================================================
# 3. TOOL 2 - SEARCH POLICY
# ============================================================

def search_policy(query):
    """
    Search the existing TF-IDF policy retrieval system.

    Returns the retrieved policy chunks under the results key.
    """

    results = retrieve(query, k=3)

    return {
        "results": results
    }


# ============================================================
# 4. TOOL 3 - CALCULATE REFUND
# ============================================================

def calculate_refund(order_amount, delivery_minutes):
    """
    Calculate the refund according to the Instamart policy.

    Rules:
        More than 45 minutes: 100% refund.
        45 minutes or less: zero refund.
    """

    order_amount = float(order_amount)
    delivery_minutes = float(delivery_minutes)

    if order_amount < 0:
        raise ValueError("Order amount cannot be negative.")

    if delivery_minutes < 0:
        raise ValueError("Delivery minutes cannot be negative.")

    if delivery_minutes > 45:
        refund_amount = order_amount
    else:
        refund_amount = 0.0

    return {
        "refund_inr": round(refund_amount, 2)
    }


# ============================================================
# 5. COMMON FUNCTION - WRITE REFUND LEDGER
# ============================================================

def append_refund_ledger(tool_name, order_id, refund_inr):
    """
    Append one JSON record to refund_ledger.jsonl.

    Each record contains:
        timestamp
        tool_name
        order_id
        refund_inr
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "order_id": order_id,
        "refund_inr": round(float(refund_inr), 2)
    }

    with REFUND_LEDGER.open(
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )


# ============================================================
# 6. TOOL 4 - ISSUE REFUND
# ============================================================

def issue_refund(order_id, refund_inr):
    """
    Record an automatically approved refund only when
    the order satisfies all refund policy conditions.
    """

    # Retrieve the order from the existing database.
    order = get_order(order_id)

    # Stop if the order does not exist.
    if "error" in order:
        return {"error": "Order not found. Refund cannot be issued."}

    # Only completed orders are eligible.
    if order["status"].lower() != "completed":
        return {"error": "Refund denied. Order is not completed."}

    # A full refund is allowed only when delivery exceeds 45 minutes.
    if float(order["delivery_minutes"]) <= 45:
        return {"error": "Refund denied. Delivery time did not exceed 45 minutes."}

    refund_inr = round(float(refund_inr), 2)

    # Reject negative or zero refund amounts.
    if refund_inr <= 0:
        return {"error": "Refund amount must be greater than zero."}

    # Do not allow a refund amount greater than the actual order amount.
    if abs(refund_inr - float(order["order_amount"])) > 0.01:
        return {"error": "Refund amount does not match the eligible order amount."}

    # Refunds above INR 1000 must be escalated to a human.
    if refund_inr > 1000:
        return {"error": "Refund exceeds INR 1000. Human escalation is required."}

    # Record the approved refund.
    append_refund_ledger(
        tool_name="issue_refund",
        order_id=order_id,
        refund_inr=refund_inr
    )

    return {
        "refund_inr": refund_inr
    }

# ============================================================
# 7. TOOL 5 - ESCALATE TO HUMAN
# ============================================================

def escalate_to_human(order_id, refund_inr):
    """
    Record a refund requiring human approval.

    Only eligible completed orders with a refund
    above INR 1000 can be escalated.
    """

    # Retrieve the order from the existing database.
    order = get_order(order_id)

    if "error" in order:
        return {"error": "Order not found. Escalation cannot proceed."}

    # Only completed orders are eligible.
    if order["status"].lower() != "completed":
        return {"error": "Escalation denied. Order is not completed."}

    # Delivery must exceed 45 minutes.
    if float(order["delivery_minutes"]) <= 45:
        return {"error": "Escalation denied. Delivery time did not exceed 45 minutes."}

    refund_inr = round(float(refund_inr), 2)

    if refund_inr <= 1000:
        return {"error": "Human escalation is required only for refunds above INR 1000."}

    # Verify that the requested refund matches the actual order amount.
    if abs(refund_inr - float(order["order_amount"])) > 0.01:
        return {"error": "Refund amount does not match the eligible order amount."}

    # Record the escalation request.
    append_refund_ledger(
        tool_name="escalate_to_human",
        order_id=order_id,
        refund_inr=refund_inr
    )

    return {
        "refund_inr": refund_inr,
        "status": "PENDING_HUMAN_APPROVAL"
    }

# ============================================================
# 8. TOOL SPECIFICATIONS
# ============================================================

TOOLS_SPEC = [

    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "Retrieve order status, amount and delivery time "
                "from the Instamart orders database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Instamart order ID."
                    }
                },
                "required": ["order_id"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": (
                "Search the supplied Instamart policy documents "
                "for information relevant to a query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The policy search query."
                    }
                },
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "calculate_refund",
            "description": (
                "Calculate the refund amount using the order amount "
                "and delivery duration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_amount": {
                        "type": "number",
                        "description": "The order amount in INR."
                    },
                    "delivery_minutes": {
                        "type": "number",
                        "description": "The delivery time in minutes."
                    }
                },
                "required": [
                    "order_amount",
                    "delivery_minutes"
                ]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": (
                "Record an automatically approved refund "
                "in the refund ledger."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Instamart order ID."
                    },
                    "refund_inr": {
                        "type": "number",
                        "description": "The approved refund in INR."
                    }
                },
                "required": ["order_id", "refund_inr"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Record a refund requiring human support lead "
                "approval in the refund ledger."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The Instamart order ID."
                    },
                    "refund_inr": {
                        "type": "number",
                        "description": "The refund amount requiring approval."
                    }
                },
                "required": ["order_id", "refund_inr"]
            }
        }
    }

]


# ============================================================
# 9. TOOL MAP
# ============================================================

# Maps the model-requested tool name to its Python function.

TOOL_MAP = {
    "get_order": get_order,
    "search_policy": search_policy,
    "calculate_refund": calculate_refund,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human
}


# ============================================================
# 10. BASIC TOOL TESTS
# ============================================================

if __name__ == "__main__":

    print("\nREFUND AGENT TOOL TESTS")
    print("=" * 60)

    # Test 1: Existing order lookup.
    print("\n1. GET ORDER")

    order_result = get_order("ORD-110093")
    print(order_result)

    # Test 2: Non-existing order lookup.
    print("\n2. GET NON-EXISTING ORDER")

    missing_order = get_order("ORD-999999")
    print(missing_order)

    # Test 3: Policy retrieval.
    print("\n3. SEARCH POLICY")

    policy_result = search_policy(
        "refund policy late delivery"
    )

    for result in policy_result["results"]:
        print(
            result["source"],
            "| Score:",
            round(result["score"], 4)
        )

    # Test 4: Refund calculation above 45 minutes.
    print("\n4. CALCULATE REFUND - ABOVE 45 MINUTES")

    print(calculate_refund(128.25, 60))

    # Test 5: Refund calculation at or below 45 minutes.
    print("\n5. CALCULATE REFUND - 45 MINUTES")

    print(calculate_refund(128.25, 45))

    # Check tool definitions.
    print("\n6. TOOL DEFINITIONS")

    print("Number of tools:", len(TOOLS_SPEC))
    print("Tool names:", list(TOOL_MAP.keys()))

    print("\nTASK 5 BASIC TOOL TESTS COMPLETED")
