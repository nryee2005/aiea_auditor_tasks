import json
import os
import sys

# Allow importing sibling modules when run from task5/
sys.path.insert(0, os.path.dirname(__file__))

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from run_prompts import load_module, get_prompt_items
from pipeline import run_pipeline_item

datasets = ["proofwriter", "pro_onto_qa"]
out_dir = os.path.join(os.path.dirname(__file__), "outputs")


def print_result(result, dataset):
    # Print stage-by-stage output for one pipeline item
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Dataset: {dataset}  |  ID: {result['id']}")
    print(sep)

    print(f"\n--- Context ---\n{result['context']}")
    print(f"\n--- Question ---\n{result['question']}")

    for att in result["attempts"]:
        print(f"\n--- Generated Prolog [attempt {att['attempt']}] ---")
        print(att["program"])
        if att["success"]:
            print(f"\n  -> Execution OK: {att['stdout']}")
        else:
            print(f"\n  -> FAILED: {att['stderr'] or '(no output)'}")

    print(f"\n--- Result ---")
    print(f"  Final answer : {result['final_answer']}")
    print(f"  Expected     : {result['expected']}")
    correct_str = {True: "CORRECT", False: "INCORRECT", None: "N/A"}[result["correct"]]
    print(f"  Verdict      : {correct_str}")
    if result["refined"]:
        print(f"  (refined after {result['num_attempts']} attempts)")
    print()


# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not set. Export it or add to .env file.")
    sys.exit(1)

os.makedirs(out_dir, exist_ok=True)

all_results = []
totals = {"total": 0, "correct": 0, "incorrect": 0, "unknown": 0, "refined": 0}

for ds_name in datasets:
    print(f"\n{'#' * 60}")
    print(f"#  Dataset: {ds_name}")
    print(f"{'#' * 60}")

    mod = load_module(ds_name)
    items = get_prompt_items(mod)

    for item in items:
        result = run_pipeline_item(item, mod, dataset=ds_name)
        result["dataset"] = ds_name
        all_results.append(result)
        print_result(result, ds_name)

        totals["total"] += 1
        if result["correct"] is True:
            totals["correct"] += 1
        elif result["correct"] is False:
            totals["incorrect"] += 1
        else:
            totals["unknown"] += 1
        if result["refined"]:
            totals["refined"] += 1

# Print summary
print("\n" + "=" * 60)
print("  SUMMARY")
print("=" * 60)
print(f"  Total items : {totals['total']}")
print(f"  Correct     : {totals['correct']}")
print(f"  Incorrect   : {totals['incorrect']}")
print(f"  Unknown     : {totals['unknown']}  (no expected answer)")
print(f"  Refined     : {totals['refined']}  (needed >1 attempt)")
print("=" * 60)

# Save results to JSON
out_path = os.path.join(out_dir, "pipeline_results.json")
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\nResults saved to {out_path}")
