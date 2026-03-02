from dataclasses import dataclass, asdict
from typing import Dict, List, Any


@dataclass
class LogicalDeductionProblem:
    dataset: str
    task_description: str
    context: str
    question: str
    options: List[str]
    domain: Dict[str, str]
    variables: List[str]
    constraints: List[str]
    query: List[str]


def build_problem(context: str, question: str) -> Dict[str, Any]:
    task_description = (
        "You are given a problem description. The task is to parse the problem "
        "as a constraint satisfaction problem, defining the domain, variables, "
        "and constraints."
    )

    # Matches screenshot: 1 oldest ... 3 newest
    domain = {
        "1": "oldest",
        "2": "second-newest",
        "3": "newest",
    }

    variables = [
        "station_wagon in {1,2,3}",
        "convertible in {1,2,3}",
        "minivan in {1,2,3}",
    ]

    constraints = [
        "station_wagon == 1 ::: The station wagon is the oldest",
        "minivan > convertible ::: The minivan is newer than the convertible",
        "AllDifferent(station_wagon, convertible, minivan) ::: All vehicles have different values",
    ]

    options = [
        "A) station_wagon is the second-newest",
        "B) convertible is the second-newest",
        "C) minivan is the second-newest",
    ]

    query = [
        "A) station_wagon == 2",
        "B) convertible == 2",
        "C) minivan == 2",
    ]

    obj = LogicalDeductionProblem(
        dataset="LogicalDeduction",
        task_description=task_description,
        context=context,
        question=question,
        options=options,
        domain=domain,
        variables=variables,
        constraints=constraints,
        query=query,
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

    lines.append("Domain:")
    for k, v in problem["domain"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")

    lines.append("Variables:")
    for var in problem["variables"]:
        lines.append(f"  {var}")
    lines.append("")

    lines.append("Constraints:")
    for c in problem["constraints"]:
        lines.append(f"  {c}")
    lines.append("")

    lines.append("Query:")
    for q in problem["query"]:
        lines.append(f"  {q}")
    lines.append("")
    return "\n".join(lines)