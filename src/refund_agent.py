import uuid
import sys
import csv
import json
import time
from pathlib import Path

# --------------------------------------------------
# 1. PROJECT PATHS AND IMPORTS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
STATE_DIR = BASE_DIR / "state"
import mock_llm

from src.refund_tools import (
    TOOLS_SPEC,
    TOOL_MAP
)

SCENARIOS_FILE = BASE_DIR / "data" / "raw" / "agent_scenarios.csv"
OUTPUT_DIR = BASE_DIR / "outputs"
AGENT_RUNS_FILE = OUTPUT_DIR / "agent_runs.jsonl"


# --------------------------------------------------
# 2. AGENT SYSTEM PROMPT
# --------------------------------------------------

SYSTEM_PROMPT = """
AGENT

You are a Swiggy Instamart refund support agent.

You must use the available tools to handle refund requests.

Follow these rules:

1. Always look up the order using get_order.
2. If the order does not exist, return NOT_FOUND.
3. Only completed orders are eligible for refunds.
4. Orders delivered in more than 45 minutes receive a
   full refund of the order amount.
5. Orders delivered in 45 minutes or less receive
   no refund.
6. Use search_policy to retrieve the relevant refund policy.
7. Use calculate_refund to calculate the refund amount.
8. Refunds above INR 1000 must be escalated to a human.
9. Refunds of INR 1000 or less may be issued automatically.
10. Never invent order information or refund amounts.
11. Return a clear final response beginning with one of:
    REFUND:
    ESCALATE:
    DENIED:
    NOT_FOUND:
    NEEDS_INFO:
12. If you cannot safely complete the request, explain
    that human support is required.
"""


# --------------------------------------------------
# 3. HELPER FUNCTIONS
# --------------------------------------------------

def get_field(obj, field, default=None):
    """
    Read a field from either a dictionary or an object.
    """

    if isinstance(obj, dict):
        return obj.get(field, default)

    return getattr(obj, field, default)


def parse_arguments(arguments):
    """
    Convert tool arguments into a Python dictionary.

    The mock LLM may provide arguments as either
    a dictionary or a JSON string.
    """

    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        return json.loads(arguments)

    return {}


def get_status(final_answer):
    """
    Extract the status appearing before the colon.
    """

    if not final_answer:
        return "FALLBACK"

    first_part = final_answer.split(":", 1)[0]

    return first_part.strip().upper()


def make_fallback(status, explanation):
    """
    Create a short human-handoff response.
    """

    return (
        f"{status}: This request could not be safely "
        f"completed automatically. {explanation} "
        "Please hand this request over to human support."
    )


def save_checkpoint(
    run_id,
    scenario_id,
    messages,
    tokens_used,
    llm_calls,
    steps,
    max_iterations,
    token_limit,
    time_limit_seconds
):
    """
    Save the complete agent state after each tool observation.
    """

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "messages": messages,
        "tokens_used": tokens_used,
        "llm_calls": llm_calls,
        "step_number": len(steps),
        "tools_already_executed": steps,
        "max_iterations": max_iterations,
        "token_limit": token_limit,
        "time_limit_seconds": time_limit_seconds
    }

    checkpoint_path = STATE_DIR / f"{run_id}.json"

    with open(
        checkpoint_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(checkpoint, file, indent=4)

    return checkpoint_path


def load_checkpoint(run_id):
    """
    Load a previously saved agent checkpoint.
    """

    checkpoint_path = STATE_DIR / f"{run_id}.json"

    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"No checkpoint found for run: {run_id}"
        )

    with open(
        checkpoint_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)

# --------------------------------------------------
# 4. MAIN REACT AGENT
# --------------------------------------------------


def _run_agent(
    user_message,
    scenario_id,
    run_id,
    max_iterations=6,
    token_limit=6000,
    time_limit_seconds=10,
    crash_after_tools=None,
    initial_state=None
):
    """
    Internal ReAct execution function.

    Supports fresh execution, simulated crashes,
    and resuming from a saved checkpoint.
    """

    if initial_state is None:

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        steps = []
        llm_calls = 0
        tokens_used = 0

    else:

        # Restore the previous execution state.
        messages = initial_state["messages"]
        steps = initial_state["tools_already_executed"]
        llm_calls = initial_state["llm_calls"]
        tokens_used = initial_state["tokens_used"]

    start_time = time.monotonic()

    while True:

        # TIME LIMIT
        elapsed_time = time.monotonic() - start_time

        if elapsed_time >= time_limit_seconds:

            final_answer = make_fallback(
                "FALLBACK_TIMEOUT",
                "The agent reached its execution time limit."
            )

            return {
                "run_id": run_id,
                "status": "FALLBACK_TIMEOUT",
                "final_answer": final_answer,
                "steps": steps,
                "llm_calls": llm_calls,
                "tokens_used": tokens_used
            }

        # MAXIMUM ITERATIONS
        if llm_calls >= max_iterations:

            final_answer = make_fallback(
                "FALLBACK_MAX_ITERATIONS",
                "The agent reached its maximum reasoning iterations."
            )

            return {
                "run_id": run_id,
                "status": "FALLBACK_MAX_ITERATIONS",
                "final_answer": final_answer,
                "steps": steps,
                "llm_calls": llm_calls,
                "tokens_used": tokens_used
            }

        # CALL THE MOCK LLM
        response = mock_llm.chat(
            messages,
            tools=TOOLS_SPEC
        )

        llm_calls += 1

        message = response.choices[0].message

        call_tokens = response.usage.total_tokens
        tokens_used += call_tokens

        # TOKEN LIMIT
        if tokens_used > token_limit:

            final_answer = make_fallback(
                "FALLBACK_TOKEN_LIMIT",
                "The agent exceeded its allowed token budget."
            )

            return {
                "run_id": run_id,
                "status": "FALLBACK_TOKEN_LIMIT",
                "final_answer": final_answer,
                "steps": steps,
                "llm_calls": llm_calls,
                "tokens_used": tokens_used
            }

        tool_calls = message.tool_calls

        # MODEL HAS RETURNED A FINAL ANSWER
        if not tool_calls:

            final_answer = message.content or (
                "NEEDS_INFO: The agent could not produce "
                "a final response."
            )

            return {
                "run_id": run_id,
                "status": get_status(final_answer),
                "final_answer": final_answer,
                "steps": steps,
                "llm_calls": llm_calls,
                "tokens_used": tokens_used
            }

        # APPEND ASSISTANT TOOL-CALL MESSAGE
        assistant_tool_calls = []

        for tool_call in tool_calls:

            tool_id = get_field(tool_call, "id")
            tool_name = get_field(tool_call, "name")

            raw_arguments = get_field(
                tool_call,
                "arguments",
                {}
            )

            arguments = parse_arguments(raw_arguments)

            assistant_tool_calls.append({
                "id": tool_id,
                "name": tool_name,
                "arguments": arguments
            })

        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": assistant_tool_calls
        })

        # EXECUTE EACH REQUESTED TOOL
        for tool_call in assistant_tool_calls:

            tool_name = tool_call["name"]
            tool_id = tool_call["id"]
            arguments = tool_call["arguments"]

            if tool_name not in TOOL_MAP:

                observation = {
                    "error": f"Unknown tool: {tool_name}"
                }

            else:

                try:

                    tool_function = TOOL_MAP[tool_name]

                    observation = tool_function(**arguments)

                except Exception as error:

                    observation = {
                        "error": str(error)
                    }

            # Append tool observation to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": tool_name,
                "content": json.dumps(observation)
            })

            # Record the completed tool execution
            steps.append({
                "tool_name": tool_name,
                "args": arguments,
                "observation": observation
            })

            # SAVE CHECKPOINT AFTER EVERY OBSERVATION
            save_checkpoint(
                run_id=run_id,
                scenario_id=scenario_id,
                messages=messages,
                tokens_used=tokens_used,
                llm_calls=llm_calls,
                steps=steps,
                max_iterations=max_iterations,
                token_limit=token_limit,
                time_limit_seconds=time_limit_seconds
            )

            # SIMULATE A CRASH AFTER THE REQUESTED TOOL COUNT
            if (
                crash_after_tools is not None
                and len(steps) >= crash_after_tools
            ):

                return {
                    "run_id": run_id,
                    "status": "SIMULATED_CRASH",
                    "final_answer": (
                        "SIMULATED_CRASH: Execution stopped "
                        "after saving the checkpoint."
                    ),
                    "steps": steps,
                    "llm_calls": llm_calls,
                    "tokens_used": tokens_used
                }


def run_agent(
    user_message,
    scenario_id,
    max_iterations=6,
    token_limit=6000,
    time_limit_seconds=10
):
    """
    Public function for starting a new agent run.
    """

    run_id = f"{scenario_id}_{uuid.uuid4().hex[:8]}"

    return _run_agent(
        user_message=user_message,
        scenario_id=scenario_id,
        run_id=run_id,
        max_iterations=max_iterations,
        token_limit=token_limit,
        time_limit_seconds=time_limit_seconds
    )


def resume_agent(run_id):
    """
    Resume agent execution from its saved checkpoint.
    """

    checkpoint = load_checkpoint(run_id)

    print(f"\nResuming run: {run_id}")
    print(
        "Previously executed tools:",
        [
            step["tool_name"]
            for step in checkpoint["tools_already_executed"]
        ]
    )

    return _run_agent(
        user_message=None,
        scenario_id=checkpoint["scenario_id"],
        run_id=run_id,
        max_iterations=checkpoint["max_iterations"],
        token_limit=checkpoint["token_limit"],
        time_limit_seconds=checkpoint["time_limit_seconds"],
        initial_state=checkpoint
    )


# --------------------------------------------------
# 5. RUN ALL SEVEN INSTRUCTOR SCENARIOS
# --------------------------------------------------

def run_all_scenarios():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        SCENARIOS_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        scenarios = list(csv.DictReader(file))

    print("\nREFUND AGENT SCENARIO EVALUATION")
    print("=" * 75)

    results = []

    for scenario in scenarios:

        scenario_id = scenario["scenario_id"]
        customer_message = scenario["message"]

        print(f"\nRunning {scenario_id}...")
        print("Customer:", customer_message)

        result = run_agent(
            user_message=customer_message,
            scenario_id=scenario_id
        )

        expected_status = scenario["expected_outcome"]

        # FALLBACK is the expected broad outcome for S7.
        if expected_status == "FALLBACK":
            passed = result["status"].startswith("FALLBACK")
        else:
            passed = result["status"] == expected_status

        result_record = {
            "scenario_id": scenario_id,
            "status": result["status"],
            "final_answer": result["final_answer"],
            "llm_calls": result["llm_calls"],
            "tokens_used": result["tokens_used"],
            "steps": result["steps"]
        }

        results.append(result_record)

        # Append one JSON record per scenario run
        with open(
            AGENT_RUNS_FILE,
            "a",
            encoding="utf-8"
        ) as output_file:

            output_file.write(
                json.dumps(result_record) + "\n"
            )

        print("Expected status:", expected_status)
        print("Actual status:", result["status"])
        print("Final answer:", result["final_answer"])
        print("Model calls:", result["llm_calls"])
        print("Tokens used:", result["tokens_used"])
        print("Tools executed:", len(result["steps"]))
        print("Result:", "PASS" if passed else "CHECK")

    return results


# --------------------------------------------------
# 6. TOKEN-LIMIT AND TIME-LIMIT DEMONSTRATIONS
# --------------------------------------------------

def demonstrate_guardrails():

    print("\n\nGUARDRAIL DEMONSTRATIONS")
    print("=" * 75)

    # Token limit demonstration
    token_result = run_agent(
        user_message=(
            "My order ORD-100048 reached me very late. "
            "I would like a refund."
        ),
        scenario_id="S1_TOKEN_DEMO",
        token_limit=200
    )

    print("\n1. TOKEN LIMIT DEMONSTRATION")
    print("Expected: FALLBACK_TOKEN_LIMIT")
    print("Actual:", token_result["status"])
    print("Model calls:", token_result["llm_calls"])
    print("Tokens used:", token_result["tokens_used"])
    print("Tools executed:", len(token_result["steps"]))

    # Time limit demonstration
    time_result = run_agent(
        user_message=(
            "My order ORD-100048 reached me very late. "
            "I would like a refund."
        ),
        scenario_id="S1_TIME_DEMO",
        time_limit_seconds=0
    )

    print("\n2. TIME LIMIT DEMONSTRATION")
    print("Expected: FALLBACK_TIMEOUT")
    print("Actual:", time_result["status"])
    print("Model calls:", time_result["llm_calls"])
    print("Tokens used:", time_result["tokens_used"])
    print("Tools executed:", len(time_result["steps"]))


def demonstrate_resumability():

    print("\n\nTASK 8: CHECKPOINT AND RESUME DEMONSTRATION")
    print("=" * 75)

    run_id = "S1_RESUME_DEMO"

    customer_message = (
        "My order ORD-100048 reached me very late. "
        "I would like a refund."
    )

    # PART 1: START THE AGENT AND SIMULATE A CRASH
    print("\n1. STARTING S1")

    first_result = _run_agent(
        user_message=customer_message,
        scenario_id="S1",
        run_id=run_id,
        max_iterations=6,
        token_limit=6000,
        time_limit_seconds=10,
        crash_after_tools=2
    )

    print("Status:", first_result["status"])
    print("Tools executed before crash:")

    for step in first_result["steps"]:
        print("-", step["tool_name"])

    print("Checkpoint saved:", STATE_DIR / f"{run_id}.json")

    # PART 2: RESUME FROM THE SAVED CHECKPOINT
    print("\n2. RESUMING S1")

    resumed_result = resume_agent(run_id)

    print("\nFinal status:", resumed_result["status"])
    print("Final answer:", resumed_result["final_answer"])
    print("Total model calls:", resumed_result["llm_calls"])
    print("Total tokens:", resumed_result["tokens_used"])

    # PART 3: VERIFY TOOL EXECUTION ORDER
    executed_tools = [
        step["tool_name"]
        for step in resumed_result["steps"]
    ]

    expected_tools = [
        "get_order",
        "search_policy",
        "calculate_refund",
        "issue_refund"
    ]

    print("\n3. TOOL EXECUTION VERIFICATION")
    print("Expected:", expected_tools)
    print("Actual:  ", executed_tools)

    tools_correct = executed_tools == expected_tools

    print(
        "No repeated tool executions:",
        "PASS" if tools_correct else "FAIL"
    )

    print(
        "Final refund status:",
        "PASS" if resumed_result["status"] == "REFUND" else "FAIL"
    )

    print(
        "Final refund amount:",
        resumed_result["final_answer"]
    )

    if not tools_correct:
        raise AssertionError(
            "Unexpected tool execution sequence after resume."
        )

    if resumed_result["status"] != "REFUND":
        raise AssertionError(
            "S1 did not complete successfully after resume."
        )

    print("\nTASK 8 RESUMABILITY DEMONSTRATION COMPLETED")


# --------------------------------------------------
# 7. MAIN
# --------------------------------------------------

def main():

    demonstrate_resumability()


if __name__ == "__main__":
    main()