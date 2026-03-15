"""
main.py
-------
Task 8: LangChain + Logic-LM inference engine over the Simpsons KB.

Run:
    python main.py

Output for each query:
  - The RAG-retrieved KB context
  - The LLM-generated Prolog goal
  - The SWI-Prolog execution result
  - A step-by-step logical inference trace
  - A final TRUE / FALSE verdict
"""
from __future__ import annotations

from task8.anish_files.rag_store import build_retriever
from task8.anish_files.chains import run_inference

# ── Example queries ────────────────────────────────────────────────────────
QUERIES = [
    "Is Marge the mother of Bart?",
    "Is Abe the grandfather of Lisa?",
    "Who are all the children of Homer?",
    "Is Patty an aunt of Bart?",
    "Is Mona an ancestor of Maggie?",
]

DIVIDER = "=" * 70


def print_result(result: dict) -> None:
    print(f"\n{DIVIDER}")
    print(f"  QUERY : {result['query']}")
    print(DIVIDER)

    print("\n[ RAG CONTEXT — KB entries retrieved ]")
    for line in result["rag_context"].strip().splitlines():
        print(f"  {line}")

    print(f"\n[ PROLOG GOAL  (LLM translation) ]")
    print(f"  {result['prolog_goal']}")

    pr = result["prolog_result"]
    print(f"\n[ PROLOG EXECUTION ]")
    print(f"  Goal    : {pr['goal']}")
    print(f"  Result  : {pr['result']}")
    if pr["bindings"]:
        print(f"  Bindings: {', '.join(pr['bindings'])}")
    if pr["raw_output"]:
        print(f"  Raw SWI : {pr['raw_output']}")

    print(f"\n[ INFERENCE TRACE ]")
    for line in result["trace"].strip().splitlines():
        print(f"  {line}")

    print(f"\n[ VERDICT ]")
    for line in result["verdict"].strip().splitlines():
        print(f"  {line}")

    print()


def main() -> None:
    print("Building RAG retriever from Simpsons KB...")
    retriever = build_retriever(k=5)
    print("Retriever ready.\n")

    for query in QUERIES:
        result = run_inference(query, retriever)
        print_result(result)

    print(f"\n{DIVIDER}")
    print("  Done.")
    print(DIVIDER)


if __name__ == "__main__":
    main()