def build_problem(context: str, question: str):
    # Very small toy mapping just to show the format
    predicates = [
        "Quiet(x): x is quiet",
        "Furry(x): x is furry",
        "Young(x): x is young",
        "White(x): x is white",
        "Red(x): x is red",
    ]
    facts = [
        "Quiet(Anne) = True",
        "White(Harry) = True",
    ]
    rules = [
        "Young(x) -> Furry(x)",
        "Red(x) -> Young(x)"
    ]
    query = "White(Anne) = True"
    return {
        "dataset": "ProofWriter",
        "context": context,
        "question": question,
        "predicates": predicates,
        "facts": facts,
        "rules": rules,
        "query": query,
    }


# prompts/proofwriter.py
NAME = "proofwriter"
DESCRIPTION = "Logic-LM prompt formatting for ProofWriter-style entailment tasks."

def format_prompt(context: str, question: str) -> str:
    return f"""Logic-LM

Task Description: Given a context and a question, determine whether the statement is entailed, contradicted, or unknown.

Context:
{context}

Question:
{question}

Answer choices: entailed / contradicted / unknown
"""

# This is what run_prompts.py is complaining it cannot find
PROMPTS = [
    {
        "id": "pw_01",
        "context": "Anne is quiet. Erin is furry. All red people are young.",
        "question": "Anne is white.",
        "expected": "unknown",
    },
    {
        "id": "pw_02",
        "context": "All people who regularly drink coffee are dependent on caffeine.",
        "question": "Someone who drinks coffee is dependent on caffeine.",
        "expected": "entailed",
    },
]

def get_prompts():
    # Optional: some runners accept this too; safe to include.
    return PROMPTS