NAME = "logical_deduction"


def build_problem(context, question):
    return {
        "dataset": "LogicalDeduction",
        "task_description": (
            "You are given a problem description. The task is to parse the problem "
            "as a constraint satisfaction problem, defining the domain, variables, "
            "and constraints."
        ),
        "context": context,
        "question": question,
        "options": [
            "A) station_wagon is the second-newest",
            "B) convertible is the second-newest",
            "C) minivan is the second-newest",
        ],
        "domain": {
            "1": "oldest",
            "2": "second-newest",
            "3": "newest",
        },
        "variables": [
            "station_wagon in {1,2,3}",
            "convertible in {1,2,3}",
            "minivan in {1,2,3}",
        ],
        "constraints": [
            "station_wagon == 1 ::: The station wagon is the oldest",
            "minivan > convertible ::: The minivan is newer than the convertible",
            "AllDifferent(station_wagon, convertible, minivan) ::: All vehicles have different values",
        ],
        "query": [
            "A) station_wagon == 2",
            "B) convertible == 2",
            "C) minivan == 2",
        ],
    }


def render(problem):
    lines = []
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
    for v in problem["variables"]:
        lines.append(f"  {v}")
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
