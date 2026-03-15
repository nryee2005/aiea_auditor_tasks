"""
chains.py
---------
Implements a Logic-LM style inference pipeline using LangChain.

Pipeline (mirrors Logic-LM paper):
  1. TRANSLATE chain  — NL query -> Prolog goal via LLM
  2. EXECUTE          — run the Prolog goal against SWI-Prolog
  3. TRACE chain      — LLM explains the deduction step-by-step
  4. VERIFY chain     — LLM gives a final True/False verdict + one-line reason

RAG context from the KB is injected into steps 1 and 3.
"""
from __future__ import annotations

import subprocess
import re
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

KB_PATH = Path(__file__).parent / "simpsons_kb.pl"

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
parser = StrOutputParser()

# ---------------------------------------------------------------------------
# 1. TRANSLATE CHAIN
#    Input : {"query": str, "context": str}   (context = RAG snippets)
#    Output: a single Prolog goal string, e.g. "grandmother(mona, bart)"
# ---------------------------------------------------------------------------
TRANSLATE_PROMPT = ChatPromptTemplate.from_template("""
You are a Prolog expert working with a Simpsons family knowledge base.

The KB defines these named predicates (always prefer these over writing compound goals):
  mother(X, Y)      - X is the mother of Y
  father(X, Y)      - X is the father of Y
  grandparent(X, Y) - X is a grandparent of Y
  grandmother(X, Y) - X is the grandmother of Y
  grandfather(X, Y) - X is the grandfather of Y
  ancestor(X, Y)    - X is an ancestor of Y (includes grandparents, great-grandparents, etc.)
  aunt(X, Y)        - X is an aunt of Y
  related(X, Y)     - X and Y share a common ancestor
  parent(X, Y)      - X is a direct parent of Y
  male(X)           - X is male
  female(X)         - X is female
  sibling(X, Y)     - X and Y are siblings

Available context retrieved from KB:
{context}

Translate the following natural-language query into a SINGLE Prolog goal.
Rules:
- ALWAYS use the most specific named predicate available. For example:
    "Is Abe the grandfather of Lisa?" -> grandfather(abe, lisa)   NOT parent(abe, X), parent(X, lisa)
    "Is Mona an ancestor of Maggie?" -> ancestor(mona, maggie)    NOT parent(mona, maggie)
    "Is Patty an aunt of Bart?"      -> aunt(patty, bart)         NOT sibling(patty, X), parent(X, bart)
- Use lowercase atom names (homer, marge, bart, lisa, maggie, abe, mona, herb, patty, selma).
- If the query asks whether something is true, write a ground goal, e.g. grandfather(abe, lisa).
- If the query asks for all solutions, use a variable, e.g. parent(homer, X).
- Output ONLY the Prolog goal, nothing else. No explanation, no full stop.

Query: {query}

Prolog goal:""")

translate_chain = TRANSLATE_PROMPT | llm | parser


# ---------------------------------------------------------------------------
# 2. PROLOG EXECUTOR
#    Runs a Prolog goal against the KB using SWI-Prolog.
#    Returns a dict: {"goal": str, "result": bool, "bindings": list[str]}
# ---------------------------------------------------------------------------

def run_prolog(goal: str) -> dict:
    """
    Execute `goal` against simpsons_kb.pl using SWI-Prolog.
    Writes a temp .pl file and runs it — more reliable than stdin on Windows.
    Returns {"goal", "result", "bindings", "raw_output"}.
    """
    import tempfile
    import os

    goal = goal.strip().rstrip(".")

    # Detect if goal contains an unbound variable (capital letter)
    has_variable = bool(re.search(r'\b[A-Z_][A-Za-z_0-9]*\b', goal))

    if has_variable:
        var_match = re.search(r'\b([A-Z][A-Za-z_0-9]*)\b', goal)
        var_name = var_match.group(1) if var_match else "X"
        prolog_script = (
            f":- consult('{KB_PATH.as_posix()}').\n"
            f":- forall({goal}, (write({var_name}), nl)), halt.\n"
        )
    else:
        prolog_script = (
            f":- consult('{KB_PATH.as_posix()}').\n"
            f":- (({goal}) -> write(true) ; write(false)), nl, halt.\n"
        )

    # Write to a temp file so Windows CMD handles it cleanly
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".pl", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(prolog_script)
        tmp.close()

        proc = subprocess.run(
            ["swipl", "-q", tmp.name],
            text=True,
            capture_output=True,
            timeout=10,
        )
        raw = (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return {
            "goal": goal,
            "result": None,
            "bindings": [],
            "raw_output": "ERROR: SWI-Prolog not found. Install it and make sure 'swipl' is on your PATH.",
        }
    except subprocess.TimeoutExpired:
        return {
            "goal": goal,
            "result": None,
            "bindings": [],
            "raw_output": "ERROR: SWI-Prolog timed out.",
        }
    finally:
        os.unlink(tmp.name)

    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    if not has_variable:
        result = "true" in raw.lower()
        bindings = []
    else:
        result = len(lines) > 0
        bindings = lines  # each line is one solution

    return {
        "goal": goal,
        "result": result,
        "bindings": bindings,
        "raw_output": raw,
    }


# ---------------------------------------------------------------------------
# 3. TRACE CHAIN
#    Input : {"query", "goal", "result", "bindings", "context"}
#    Output: step-by-step logical deduction trace (string)
# ---------------------------------------------------------------------------
TRACE_PROMPT = ChatPromptTemplate.from_template("""
You are a logic teacher explaining a Prolog inference step-by-step.

Knowledge base facts and rules used:
{context}

Original question: {query}
Prolog goal executed: {goal}
SWI-Prolog result: {result}
Bindings (solutions found): {bindings}

Write a clear, numbered deduction trace explaining HOW Prolog arrived at this result.
Each step should cite a specific fact or rule from the knowledge base.
End with a one-line conclusion: "Therefore, [query] is TRUE." or "Therefore, [query] is FALSE."

Trace:""")

trace_chain = TRACE_PROMPT | llm | parser


# ---------------------------------------------------------------------------
# 4. VERIFY CHAIN
#    Input : {"query", "trace"}
#    Output: "TRUE" or "FALSE" followed by a one-line reason
# ---------------------------------------------------------------------------
VERIFY_PROMPT = ChatPromptTemplate.from_template("""
Based on the following logical inference trace, answer the original query.

Query: {query}
Trace: {trace}

Respond with exactly:
  Answer: TRUE  or  Answer: FALSE
  Reason: <one sentence>
""")

verify_chain = VERIFY_PROMPT | llm | parser


# ---------------------------------------------------------------------------
# FULL PIPELINE
# ---------------------------------------------------------------------------

def run_inference(query: str, retriever) -> dict:
    """
    Full Logic-LM pipeline:
      query -> RAG -> translate -> prolog -> trace -> verify

    Returns a dict with all intermediate outputs for full transparency.
    """

    # Step 1: Retrieve relevant KB context via RAG
    rag_docs = retriever.invoke(query)
    context = "\n".join(
        f"  [{d.metadata['type']}] {d.page_content}  (Prolog: {d.metadata.get('prolog','')})"
        for d in rag_docs
    )

    # Step 2: Translate NL query to Prolog goal
    prolog_goal = translate_chain.invoke({"query": query, "context": context}).strip()

    # Step 3: Execute Prolog goal
    prolog_result = run_prolog(prolog_goal)

    # Step 4: Generate inference trace
    trace = trace_chain.invoke({
        "query": query,
        "goal": prolog_result["goal"],
        "result": prolog_result["result"],
        "bindings": prolog_result["bindings"] if prolog_result["bindings"] else "none",
        "context": context,
    })

    # Step 5: Verify and produce final verdict
    verdict = verify_chain.invoke({"query": query, "trace": trace})

    return {
        "query": query,
        "rag_context": context,
        "prolog_goal": prolog_goal,
        "prolog_result": prolog_result,
        "trace": trace,
        "verdict": verdict,
    }