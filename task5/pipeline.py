"""
Logic-LM pipeline: prompt → LLM translates to Prolog → execute via swipl → self-refine → compare.

Supports ProofWriter and PrOntoQA datasets.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import openai


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Thin wrapper around the OpenAI chat completions API."""
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


TRANSLATE_SYSTEM = """\
You are an expert logic programmer. Given a natural-language logic problem \
(context + question + answer format), produce a **complete, self-contained \
SWI-Prolog program**.

STRICT RULES for SWI-Prolog:
- Declare facts and rules as normal clauses.
- The query MUST be a :- directive (e.g., :- (goal -> ... ; ...), halt.).
- Do NOT write bare goals or ?- queries. Only use :- directives.
- The LAST line must be :- halt.
- The program must print EXACTLY ONE WORD as the answer using write/1 and nl/0.
- No other output. No sentences. Just the single answer word.

Output ONLY the Prolog code. No explanation."""


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences from LLM output."""
    raw = re.sub(r"^```(?:prolog)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*$", "", raw, flags=re.MULTILINE)
    return raw.strip()


# Answer format hints per dataset type
ANSWER_FORMATS = {
    "proofwriter": "Print exactly one of: entailed, contradicted, or unknown",
    "pro_onto_qa": "Print exactly one of: true or false",
}


def translate_to_prolog(context: str, question: str, dataset: str = "") -> str:
    """Ask GPT to translate a logic problem into a SWI-Prolog program."""
    answer_hint = ANSWER_FORMATS.get(dataset, "Print exactly one of: true or false")
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer format: {answer_hint}"
    )
    raw = call_llm(TRANSLATE_SYSTEM, user_prompt)
    return _strip_fences(raw)


# ---------------------------------------------------------------------------
# Prolog execution
# ---------------------------------------------------------------------------

def run_prolog_program(program: str) -> Dict[str, Any]:
    """Write *program* to a temp file and execute it with swipl.

    Returns dict with keys: success (bool), stdout (str), stderr (str).
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".pl", delete=False
    ) as tmp:
        tmp.write(program)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["swipl", "-q", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        # Treat as failure if returncode != 0, or if stderr has ERROR
        # (swipl can return 0 even when directives fail)
        has_error = "ERROR:" in stderr
        success = result.returncode == 0 and not has_error
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "swipl not found on PATH",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Execution timed out (10s)",
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Self-refinement
# ---------------------------------------------------------------------------

REFINE_SYSTEM = """\
You are an expert Prolog debugger. The user will give you:
- The original logic problem (context + question)
- A Prolog program that failed
- The error output

STRICT RULES for SWI-Prolog:
- The query MUST be a :- directive (e.g., :- (goal -> ... ; ...), halt.).
- Do NOT write bare goals or ?- queries. Only use :- directives.
- The LAST line must be :- halt.
- The program must print EXACTLY ONE WORD as the answer using write/1 and nl/0.

Produce a CORRECTED, complete SWI-Prolog program. Output ONLY the Prolog code."""

def refine_prolog(program: str, error: str, context: str, question: str) -> str:
    """Ask GPT to fix a failing Prolog program."""
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Failing program:\n```prolog\n{program}\n```\n\n"
        f"Error:\n{error}"
    )
    raw = call_llm(REFINE_SYSTEM, user_prompt)
    return _strip_fences(raw)


# ---------------------------------------------------------------------------
# Answer interpretation
# ---------------------------------------------------------------------------

def interpret_result(stdout: str, expected: str | None) -> Dict[str, Any]:
    """Normalize Prolog output and compare with expected answer."""
    raw_answer = stdout.strip().lower()
    if expected is None:
        return {"answer": raw_answer, "expected": None, "correct": None}

    norm_expected = expected.strip().lower()

    # Keyword sets for canonicalization
    true_words = {"true", "yes", "entailed"}
    false_words = {"false", "no", "contradicted"}
    unknown_words = {"unknown", "neither"}

    def canonicalize(val: str) -> str:
        """Try exact match first, then search for keywords in longer strings."""
        val = val.strip().rstrip(".")
        # Exact match
        if val in true_words:
            return "true"
        if val in false_words:
            return "false"
        if val in unknown_words:
            return "unknown"
        # Keyword search in longer output (e.g. "Yes, alex is bright.")
        words = set(re.findall(r"[a-z]+", val))
        for w in ("entailed", "true", "yes"):
            if w in words:
                return "true"
        for w in ("contradicted", "false", "no"):
            if w in words:
                return "false"
        for w in ("unknown", "neither"):
            if w in words:
                return "unknown"
        return val

    canon_answer = canonicalize(raw_answer)
    canon_expected = canonicalize(norm_expected)

    return {
        "answer": raw_answer,
        "expected": expected,
        "correct": canon_answer == canon_expected,
    }


# ---------------------------------------------------------------------------
# Main pipeline orchestrator
# ---------------------------------------------------------------------------

def run_pipeline_item(item: Dict[str, Any], mod: Any, dataset: str = "") -> Dict[str, Any]:
    """Run the full pipeline for a single problem item.

    Steps:
      1. Format the prompt for display (via existing format_one)
      2. Translate to Prolog
      3. Execute Prolog
      4. Self-refine up to 3 times on failure
      5. Interpret and compare answer
    """
    # Lazy import to avoid circular deps
    from run_prompts import format_one

    context = item.get("context", "")
    question = item.get("question", "")
    expected = item.get("expected")

    # 1. Format for display
    formatted_prompt = format_one(mod, item)

    # 2. Translate to Prolog
    program = translate_to_prolog(context, question, dataset=dataset)

    # 3-4. Execute with up to 3 refinement attempts
    max_attempts = 3
    attempts = []
    exec_result = None

    for attempt in range(1, max_attempts + 1):
        exec_result = run_prolog_program(program)
        attempts.append({
            "attempt": attempt,
            "program": program,
            "success": exec_result["success"],
            "stdout": exec_result["stdout"],
            "stderr": exec_result["stderr"],
        })

        if exec_result["success"] and exec_result["stdout"]:
            break

        # Build error message for refinement
        if not exec_result["success"]:
            error_msg = exec_result["stderr"] or "Program returned non-zero exit code"
        else:
            error_msg = "Program produced no output"

        if attempt < max_attempts:
            program = refine_prolog(program, error_msg, context, question)

    # 5. Interpret result
    final_stdout = exec_result["stdout"] if exec_result else ""
    comparison = interpret_result(final_stdout, expected)

    return {
        "id": item.get("id", "unknown"),
        "context": context,
        "question": question,
        "expected": expected,
        "formatted_prompt": formatted_prompt,
        "attempts": attempts,
        "final_answer": comparison["answer"],
        "correct": comparison["correct"],
        "num_attempts": len(attempts),
        "refined": len(attempts) > 1,
    }
