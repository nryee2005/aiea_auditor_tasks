from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass
class ARLSATProblem:
    dataset: str
    task_description: str
    context: str
    question: str
    options: List[str]
    declarations: List[str]
    constraints: List[str]
    checks: List[str]


def build_problem(context: str, question: str) -> Dict[str, Any]:
    task_description = (
        "You are given a problem description. The task is to parse the problem "
        "as a constraint satisfaction problem, defining the domain, variables, "
        "and constraints, then evaluate answer options."
    )

    # Screenshot vibe: interns & assignments
    options = [
        "(A) Farber",
        "(B) Gombarick",
        "(C) Hall",
        "(D) Kanze",
        "(E) Lha",
    ]

    declarations = [
        "stories = EnumSort([Romania, Spain, Tuscany])",
        "assistants = EnumSort([photographer, writer])",
        "assigned = Function([interns] -> [stories])",
        "trained = Function([interns] -> [assistants])",
    ]

    constraints = [
        "trained(Gombarick) == trained(Lha) ::: Gombarick and Lha trained in the same field",
        "trained(Farber) != trained(Kanze) ::: Farber and Kanze trained in different fields",
        "assigned(Jackson) == Tuscany ::: Jackson is assigned to Tuscany",
        "assigned(Kanze) != Spain ::: Kanze is not assigned to Spain",
    ]

    # Screenshot shows checks like:
    # is_unsat(assigned(Farber) == Tuscany) ::: (A)
    checks = [
        "is_unsat(assigned(Farber) == Tuscany) ::: (A)",
        "is_unsat(assigned(Gombarick) == Tuscany) ::: (B)",
        "is_unsat(assigned(Hall) == Tuscany) ::: (C)",
        "is_unsat(assigned(Kanze) == Tuscany) ::: (D)",
        "is_unsat(assigned(Lha) == Tuscany) ::: (E)",
    ]

    obj = ARLSATProblem(
        dataset="AR-LSAT",
        task_description=task_description,
        context=context,
        question=question,
        options=options,
        declarations=declarations,
        constraints=constraints,
        checks=checks,
    )
    return asdict(obj)


def render(problem: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("Logic-LM\n")
    lines.append("Task Description: " + problem["task_description"] + "\n")
    lines.append("Context: " + problem["context"] + "\n")
    lines.append("Question: " + problem["question"] + "\n")

    lines.append("Options:")
    for o in problem["options"]:
        lines.append(f"  {o}")
    lines.append("")

    lines.append("Declarations:")
    for d in problem["declarations"]:
        lines.append(f"  {d}")
    lines.append("")

    lines.append("Constraints:")
    for c in problem["constraints"]:
        lines.append(f"  {c}")
    lines.append("")

    lines.append("Options (Checks):")
    for chk in problem["checks"]:
        lines.append(f"  {chk}")
    lines.append("")
    return "\n".join(lines)