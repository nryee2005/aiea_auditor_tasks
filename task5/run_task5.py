from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path


TASK5_DIR = Path(__file__).resolve().parent
PROMPTS_SCRIPT = TASK5_DIR / "run_prompts.py"

# Adjust if your KB lives elsewhere (I'm defaulting to task_4 location that I used before)
DEFAULT_KB_PATH = (TASK5_DIR.parent / "task4" / "knowledge_base.pl").resolve()

# Where we save outputs
OUT_DIR = TASK5_DIR / "outputs"
OUT_DIR.mkdir(exist_ok=True)

SWIPL_OUT = OUT_DIR / "swipl_kb_results.txt"
PROMPTS_OUT = OUT_DIR / "prompts_output.txt"
FULL_LOG = OUT_DIR / "task5_full_run.log"


class Tee(io.TextIOBase):
    """Write to both the original stream and a StringIO buffer."""

    def __init__(self, original: io.TextIOBase):
        self._original = original
        self.buffer = io.StringIO()

    def write(self, s: str) -> int:
        self._original.write(s)
        self.buffer.write(s)
        return len(s)

    def flush(self):
        self._original.flush()


def run_cmd(cmd: list[str], cwd: Path | None = None) -> int:
    """Run a command, stream output to terminal, return exit code."""
    print(f"\n$ {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    return p.returncode


def run_cmd_capture(cmd: list[str], outfile: Path, cwd: Path | None = None) -> int:
    """Run a command, capture stdout+stderr to outfile (and also print)."""
    print(f"\n$ {' '.join(cmd)}")
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    outfile.write_text(p.stdout, encoding="utf-8")
    print(f"\n--- saved output to: {outfile} ---\n")
    print(p.stdout)
    return p.returncode


def swipl_kb_tests(kb_path: Path) -> int:
    """
    Run a few deterministic SWI-Prolog queries against the Family Guy KB.

    This prints results without the interactive 'false.' issue by halting after listing solutions.
    """
    if not kb_path.exists():
        print(f"ERROR: KB file not found: {kb_path}")
        print("Fix: update DEFAULT_KB_PATH in run_task5.py or move/copy knowledge_base.pl there.")
        return 2

    # Prolog program we feed into swipl:
    # - consult the KB
    # - run queries and print all solutions
    # - halt cleanly
    kb_posix = kb_path.as_posix()
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

    # Write to temp file and run (more reliable than piping stdin to swipl)
    print("\nRunning SWI-Prolog KB tests...")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pl", delete=False
    ) as tmp:
        tmp.write(prolog_script)
        tmp_path = tmp.name

    cmd = ["swipl", "-q", tmp_path]
    p = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    Path(tmp_path).unlink(missing_ok=True)

    SWIPL_OUT.write_text(p.stdout, encoding="utf-8")
    print(f"\n--- saved SWI-Prolog results to: {SWIPL_OUT} ---\n")
    print(p.stdout)

    if p.returncode != 0:
        print("ERROR: SWI-Prolog tests failed (non-zero exit code).")
        return 3

    # Minimal sanity check: ensure expected names appear
    expected = ["chris", "stewie", "meg"]
    if not all(e in p.stdout for e in expected):
        print("WARNING: SWI-Prolog output did not include all expected answers.")
        print("Check your KB facts/rules, and check outputs file.")
        # Don't hard-fail; still return 0 so you can proceed
    return 0


DATASETS = ["proofwriter", "pro_onto_qa", "folio", "logical_deduction", "ar_lsat"]


def run_prompts() -> int:
    """Run run_prompts.py for each dataset and capture output."""
    if not PROMPTS_SCRIPT.exists():
        print(f"ERROR: Missing {PROMPTS_SCRIPT}")
        print("Fix: make sure run_prompts.py is in the same folder as run_task5.py.")
        return 2

    print("\nRunning prompt formatting demo (run_prompts.py)...")
    all_output = []
    for ds in DATASETS:
        cmd = [sys.executable, str(PROMPTS_SCRIPT), ds, "--all"]
        print(f"\n$ {' '.join(cmd)}")
        p = subprocess.run(
            cmd,
            cwd=str(TASK5_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        print(p.stdout)
        all_output.append(p.stdout)
        if p.returncode != 0:
            print(f"WARNING: run_prompts.py {ds} returned {p.returncode}")

    PROMPTS_OUT.write_text("\n".join(all_output), encoding="utf-8")
    print(f"\n--- saved output to: {PROMPTS_OUT} ---")
    return 0


def main() -> int:
    print("=== Task 5 Runner: KB tests + Prompt demo ===")

    # 1) SWI-Prolog KB tests
    rc = swipl_kb_tests(DEFAULT_KB_PATH)
    if rc != 0:
        return rc

    # 2) Prompt demo
    rc = run_prompts()
    if rc != 0:
        return rc

    print("\n Done.")
    print(f"- SWI-Prolog KB results: {SWIPL_OUT}")
    print(f"- Prompt outputs:        {PROMPTS_OUT}")

    return 0


if __name__ == "__main__":
    tee = Tee(sys.stdout)
    sys.stdout = tee
    try:
        rc = main()
    finally:
        sys.stdout = tee._original
        FULL_LOG.write_text(tee.buffer.getvalue(), encoding="utf-8")
        print(f"- Full terminal log:     {FULL_LOG}")
    raise SystemExit(rc)