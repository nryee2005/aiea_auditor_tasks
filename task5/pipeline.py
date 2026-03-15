import re
import subprocess
import tempfile
import os

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage

model = init_chat_model("openai:gpt-3.5-turbo", temperature=0)


def call_llm(system_prompt, user_prompt):
    response = model.invoke([SystemMessage(system_prompt), HumanMessage(user_prompt)])
    return response.content.strip()


def strip_fences(raw):
    # Remove markdown code fences that GPT sometimes adds
    raw = re.sub(r"^```(?:prolog)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*$", "", raw, flags=re.MULTILINE)
    return raw.strip()


# System prompt for translating natural language to Prolog
TRANSLATE_PROMPT = """\
You are an expert logic programmer. Given a natural-language logic problem \
(context + question + answer format), produce a complete, self-contained \
SWI-Prolog program.

STRICT RULES for SWI-Prolog:
- Declare facts and rules as normal clauses.
- The query MUST be a :- directive (e.g., :- (goal -> ... ; ...), halt.).
- Do NOT write bare goals or ?- queries. Only use :- directives.
- The LAST line must be :- halt.
- The program must print EXACTLY ONE WORD as the answer using write/1 and nl/0.
- No other output. No sentences. Just the single answer word.

Output ONLY the Prolog code. No explanation."""

# What answer format to tell GPT about for each dataset
ANSWER_FORMATS = {
    "proofwriter": "Print exactly one of: entailed, contradicted, or unknown",
    "pro_onto_qa": "Print exactly one of: true or false",
}


def translate_to_prolog(context, question, dataset=""):
    # Ask GPT to turn a logic problem into a Prolog program
    answer_hint = ANSWER_FORMATS.get(dataset, "Print exactly one of: true or false")
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Answer format: {answer_hint}"
    )
    raw = call_llm(TRANSLATE_PROMPT, user_prompt)
    return strip_fences(raw)


# Prolog execution

def run_prolog(program):
    # Write program to a temp file and run it with swipl
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".pl", delete=False)
    tmp.write(program)
    tmp.close()

    try:
        result = subprocess.run(
            ["swipl", "-q", tmp.name],
            capture_output=True, text=True, timeout=10,
        )
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()

        # swipl can return 0 even when directives fail -> check for ERROR in stderr
        has_error = "ERROR:" in stderr
        success = result.returncode == 0 and not has_error

        return {"success": success, "stdout": stdout, "stderr": stderr}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "swipl not found on PATH"}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Execution timed out (10s)"}
    finally:
        os.unlink(tmp.name) # cleanup tmp


# Self-refinement

REFINE_PROMPT = """\
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


def refine_prolog(program, error, context, question):
    # Send the failing program + error back to GPT to get a fix
    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        f"Failing program:\n```prolog\n{program}\n```\n\n"
        f"Error:\n{error}"
    )
    raw = call_llm(REFINE_PROMPT, user_prompt)
    return strip_fences(raw)


# Answer comparison

def interpret_result(stdout, expected):
    # Compare prolog output against expected answer
    raw_answer = stdout.strip().lower()
    if expected is None:
        return {"answer": raw_answer, "expected": None, "correct": None}

    norm_expected = expected.strip().lower()

    def canonicalize(val):
        val = val.strip().rstrip(".")

        # Exact match against known answer words
        if val in ("true", "yes", "entailed"):
            return "true"
        if val in ("false", "no", "contradicted"):
            return "false"
        if val in ("unknown", "neither"):
            return "unknown"

        # Search for keywords in longer output
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

    return {
        "answer": raw_answer,
        "expected": expected,
        "correct": canonicalize(raw_answer) == canonicalize(norm_expected),
    }


# Main pipeline for one problem

def run_pipeline_item(item, mod, dataset=""):
    # Import here to avoid circular import
    from run_prompts import format_one

    context = item.get("context", "")
    question = item.get("question", "")
    expected = item.get("expected")

    # Format prompt for display
    formatted_prompt = format_one(mod, item)

    # Translate to Prolog
    program = translate_to_prolog(context, question, dataset=dataset)

    # Execute with up to 3 refinement attempts
    max_attempts = 3
    attempts = []

    for attempt in range(1, max_attempts + 1):
        exec_result = run_prolog(program)
        attempts.append({
            "attempt": attempt,
            "program": program,
            "success": exec_result["success"],
            "stdout": exec_result["stdout"],
            "stderr": exec_result["stderr"],
        })

        # If it worked and produced output, we're done
        if exec_result["success"] and exec_result["stdout"]:
            break

        # Figure out what went wrong for the refinement prompt
        if not exec_result["success"]:
            error_msg = exec_result["stderr"] or "Program returned non-zero exit code"
        else:
            error_msg = "Program produced no output"

        # Try to fix it
        if attempt < max_attempts:
            program = refine_prolog(program, error_msg, context, question)

    # Compare final output to expected answer
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
