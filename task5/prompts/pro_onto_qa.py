NAME = "pro_onto_qa"


def build_problem(context, question):
    return {
        "dataset": "PrOntoQA",
        "task_description": (
            "You are given a problem description and a question. The task is to:\n"
            "1) define all the predicates in the problem\n"
            "2) parse the problem into logic rules based on the defined predicates\n"
            "3) write all the facts mentioned in the problem\n"
            "4) parse the question into the logic form"
        ),
        "context": context,
        "question": question,
        "predicates": [
            "Jompus(x, bool) ::: Does x belong to Jompus?",
            "Zumpus(x, bool) ::: Does x belong to Zumpus?",
            "Frutiy(x, bool) ::: Is x fruity?",
            "Shy(x, bool) ::: Is x shy?",
            "Dumpus(x, bool) ::: Is x a dumpus?",
            "Rompus(x, bool) ::: Is x a rompous?",
        ],
        "facts": [
            "Zumpus(Alex, True)",
            "Tumpus(Alex, True)",
        ],
        "rules": [
            "Jompus(x, True) -> Frutiy(x, True)",
            "Dumpus(x, True) -> Rompus(x, True)",
        ],
        "query": "Shy(Alex, False)",
    }


def render(problem):
    lines = []
    lines.append("Logic-LM\n")
    lines.append("Task Description: " + problem["task_description"] + "\n")
    lines.append("Context: " + problem["context"] + "\n")
    lines.append("Question: " + problem["question"] + "\n")

    lines.append("Predicates:")
    for p in problem["predicates"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append("Facts:")
    for f in problem["facts"]:
        lines.append(f"  {f}")
    lines.append("")

    lines.append("Rules:")
    for r in problem["rules"]:
        lines.append(f"  {r}")
    lines.append("")

    lines.append("Query:")
    lines.append(f"  {problem['query']}")
    lines.append("")
    return "\n".join(lines)


# Sample problems for PrOntoQA
PROMPTS = [
    {
        "id": "pro_onto_qa_01",
        "context": (
            "Every jompus is fruity. Every fruity thing is bright. "
            "Alex is a jompus."
        ),
        "question": "Is Alex bright?",
        "expected": "true",
    },
    {
        "id": "pro_onto_qa_02",
        "context": (
            "Every zumpus is shy. Every shy thing is a dumpus. "
            "Every dumpus is cold. Rex is a zumpus."
        ),
        "question": "Is Rex cold?",
        "expected": "true",
    },
]
