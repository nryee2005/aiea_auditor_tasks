from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass
class FOLIOProblem:
    dataset: str
    task_description: str
    context: str
    question: str
    predicates: List[str]
    premises: List[str]
    conclusion: str


def build_problem(context: str, question: str) -> Dict[str, Any]:
    task_description = (
        "Given a problem description and a question, parse the problem and question "
        "into first-order logic formulas.\n"
        "The grammar of first-order logic is defined as follows:\n"
        "1) conjunction: expr1 ∧ expr2\n"
        "2) disjunction: expr1 ∨ expr2\n"
        "3) exclusive disjunction: expr1 ⊕ expr2\n"
        "4) negation: ¬expr1\n"
        "5) implication: expr1 → expr2\n"
        "6) iff: expr1 ↔ expr2\n"
        "7) universal quantifier: ∀x\n"
        "8) existential quantifier: ∃x\n"
        "Output format: logic form ::: description"
    )

    predicates = [
        "Dependent(x) ::: x is a person dependent on caffeine",
        "Student(x) ::: x is a student",
        "Drinks(x) ::: x regularly drinks coffee",
        "Jokes(x) ::: x jokes about being addicted to caffeine",
        "Unaware(x) ::: x is unaware that caffeine is a drug",
    ]

    # Premises modeled after your screenshot
    premises = [
        "∀x (Drinks(x) → Dependent(x)) ::: All people who regularly drink coffee are dependent on caffeine",
        "∀x (Jokes(x) → ¬Unaware(x)) ::: No one who jokes about being addicted is unaware that caffeine is a drug",
        # You can add the Rina-specific premise as another line:
        "(¬Student(rina) → (Dependent(rina) ⊕ Student(rina))) ::: If Rina is not a student, then Rina is either dependent or a student, or neither",
    ]

    conclusion = (
        "Jokes(rina) ⊕ Unaware(rina) ::: "
        "Rina either jokes about being addicted to caffeine or is unaware that caffeine is a drug"
    )

    obj = FOLIOProblem(
        dataset="FOLIO",
        task_description=task_description,
        context=context,
        question=question,
        predicates=predicates,
        premises=premises,
        conclusion=conclusion,
    )
    return asdict(obj)


def render(problem: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Logic-LM\n")
    lines.append("Task Description: " + problem["task_description"] + "\n")
    lines.append("Context: " + problem["context"] + "\n")
    lines.append("Question: " + problem["question"] + "\n")

    lines.append("Predicates:")
    for p in problem["predicates"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append("Premises:")
    for pr in problem["premises"]:
        lines.append(f"  {pr}")
    lines.append("")

    lines.append("Conclusion:")
    lines.append(f"  {problem['conclusion']}")
    lines.append("")
    return "\n".join(lines)