import io
import subprocess
import sys
import tempfile
import os

task5_dir = os.path.dirname(os.path.abspath(__file__))
prompts_script = os.path.join(task5_dir, "run_prompts.py")
kb_path = os.path.join(task5_dir, "..", "task4", "knowledge_base.pl")

# Output paths
out_dir = os.path.join(task5_dir, "outputs")
os.makedirs(out_dir, exist_ok=True)
swipl_out = os.path.join(out_dir, "swipl_kb_results.txt")
prompts_out = os.path.join(out_dir, "prompts_output.txt")
full_log = os.path.join(out_dir, "task5_full_run.log")

datasets = ["proofwriter", "pro_onto_qa", "folio", "logical_deduction", "ar_lsat"]


# Captures everything printed to stdout so we can save it to a log file
class Tee:
    def __init__(self, original):
        self.original = original
        self.buffer = io.StringIO()

    def write(self, s):
        self.original.write(s)
        self.buffer.write(s)
        return len(s)

    def flush(self):
        self.original.flush()


def run_kb_tests():
    # Check that the KB file exists
    if not os.path.exists(kb_path):
        print(f"ERROR: KB file not found: {kb_path}")
        return 1

    # Build a prolog script that loads the KB and runs queries
    kb_posix = kb_path.replace("\\", "/")
    prolog_script = "\n".join([
        f":- ['{kb_posix}'].",
        ":- writeln('--- Query 1: mother(lois, X) ---'),",
        "   forall(mother(lois, X), writeln(X)).",
        ":- writeln('--- Query 2: father(peter, X) ---'),",
        "   forall(father(peter, X), writeln(X)).",
        ":- writeln('--- Query 3: brother(chris, X) ---'),",
        "   forall(brother(chris, X), writeln(X)).",
        ":- halt.",
        "",
    ])

    # Write to temp file and run with swipl
    print("\nRunning SWI-Prolog KB tests...")
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pl", delete=False)
    tmp.write(prolog_script)
    tmp.close()

    result = subprocess.run(
        ["swipl", "-q", tmp.name],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    os.unlink(tmp.name)

    # Save and print results
    with open(swipl_out, "w") as f:
        f.write(result.stdout)
    print(result.stdout)
    print(f"Saved to {swipl_out}")

    # Check that expected names show up
    for name in ["chris", "stewie", "meg"]:
        if name not in result.stdout:
            print(f"WARNING: '{name}' not found in output")

    return result.returncode


def run_all_prompts():
    print("\nRunning prompt formatting for all datasets...")
    all_output = []

    for ds in datasets:
        cmd = [sys.executable, prompts_script, ds, "--all"]
        result = subprocess.run(
            cmd, cwd=task5_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        print(result.stdout)
        all_output.append(result.stdout)

        if result.returncode != 0:
            print(f"WARNING: {ds} returned exit code {result.returncode}")

    # Save combined output
    with open(prompts_out, "w") as f:
        f.write("\n".join(all_output))
    print(f"Saved to {prompts_out}")
    return 0


# Capture all output with Tee so we can save the full log
tee = Tee(sys.stdout)
sys.stdout = tee

print("Task 5: KB Tests + Prompt Demo")

# Run KB tests
rc = run_kb_tests()
if rc != 0:
    print("KB tests failed")

# Run prompt formatting
run_all_prompts()

print("\nDone.")

# Save the full terminal log
sys.stdout = tee.original
with open(full_log, "w") as f:
    f.write(tee.buffer.getvalue())
print(f"Full log saved to {full_log}")
