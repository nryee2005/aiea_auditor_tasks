import subprocess
import os
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.agents.structured_output import ToolStrategy
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

KB_PATH = os.path.join(os.path.dirname(__file__), "family_guy_kb.pl")

# natural language versions of each fact so embeddings are useful
FACT_DESCRIPTIONS = {
    "male(peter)":          "Peter is male.",
    "male(chris)":          "Chris is male.",
    "male(stewie)":         "Stewie is male.",
    "male(brian)":          "Brian is male.",
    "male(carter)":         "Carter is male.",
    "female(lois)":         "Lois is female.",
    "female(meg)":          "Meg is female.",
    "female(babs)":         "Babs is female.",
    "parent(peter, chris)": "Peter is a parent of Chris.",
    "parent(peter, stewie)":"Peter is a parent of Stewie.",
    "parent(peter, meg)":   "Peter is a parent of Meg.",
    "parent(lois, chris)":  "Lois is a parent of Chris.",
    "parent(lois, stewie)": "Lois is a parent of Stewie.",
    "parent(lois, meg)":    "Lois is a parent of Meg.",
    "parent(carter, lois)": "Carter is a parent of Lois.",
    "parent(babs, lois)":   "Babs is a parent of Lois.",
    "married(peter, lois)": "Peter is married to Lois.",
    "married(lois, peter)": "Lois is married to Peter.",
    "married(carter, babs)":"Carter is married to Babs.",
    "married(babs, carter)":"Babs is married to Carter.",
}

# rules described in plain english
RULE_DESCRIPTIONS = {
    "father":      "father(X, Y) is true if X is a parent of Y and X is male.",
    "mother":      "mother(X, Y) is true if X is a parent of Y and X is female.",
    "sibling":     "sibling(X, Y) is true if X and Y share a common parent and are not the same.",
    "brother":     "brother(X, Y) is true if Y is a sibling of X and Y is male.",
    "sister":      "sister(X, Y) is true if Y is a sibling of X and Y is female.",
    "grandparent": "grandparent(X, Z) is true if X is a parent of Y and Y is a parent of Z.",
    "grandfather": "grandfather(X, Z) is true if X is a grandparent of Z and X is male.",
    "grandmother": "grandmother(X, Z) is true if X is a grandparent of Z and X is female.",
    "in_law":      "in_law(X, Y) is true if X is married to Z and Z is a parent of Y.",
}


def build_retriever(k=5):
    docs = []
    for prolog, description in FACT_DESCRIPTIONS.items():
        docs.append(Document(page_content=description, metadata={"type": "fact", "prolog": prolog + "."}))
    for functor, description in RULE_DESCRIPTIONS.items():
        docs.append(Document(page_content=description, metadata={"type": "rule", "functor": functor}))

    vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings(), collection_name="family_guy_kb")
    return vectorstore.as_retriever(search_kwargs={"k": k})


def make_system_prompt(question, retriever):
    # pull the top k most relevant facts/rules for this question
    docs = retriever.invoke(question)
    context = "\n".join(f"- {d.page_content}" for d in docs)

    return f"""\
You are a logic reasoning assistant with access to a Prolog knowledge base about the Family Guy family.

Relevant knowledge base entries for this question:
{context}

Available rules: mother/2, father/2, sibling/2, brother/2, sister/2, grandparent/2, grandfather/2, grandmother/2, in_law/2
Individuals: peter, lois, chris, stewie, meg, brian, carter, babs

Argument order: father(X,Y) means X is father of Y. brother(X,Y) means Y is the brother. sister(X,Y) means Y is the sister.

When answering:
1. Make ONE Prolog query using run_prolog_query
2. Accept the result — if it returns "false", the answer is false. Do not retry unless there is a syntax ERROR.
3. Respond with answer ("true"/"false") and a step-by-step trace referencing the specific facts and rules used."""


@tool
def run_prolog_query(goal: str) -> str:
    """Run a Prolog goal against the Family Guy knowledge base.

    Pass a SWI-Prolog goal string like "father(peter, chris)" or "parent(X, stewie)".
    Returns true, false, or an error message.
    """
    wrapped = f"({goal} -> write(true) ; write(false)), nl, halt"
    try:
        result = subprocess.run(
            ["swipl", "-q", "-l", KB_PATH, "-g", wrapped],
            capture_output=True, text=True, timeout=10,
        )
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()

        if "ERROR:" in stderr:
            return f"Error: {stderr}"
        return stdout if stdout else "false"
    except FileNotFoundError:
        return "Error: swipl not found on PATH"
    except subprocess.TimeoutExpired:
        return "Error: execution timed out"


@dataclass
class QueryResult:
    answer: str  # "true" or "false"
    trace: str   # deduction using the facts and rules from the KB


model = init_chat_model("openai:gpt-4o-mini", temperature=0)


def run_query(question, retriever):
    agent = create_agent(
        model=model,
        tools=[run_prolog_query],
        system_prompt=make_system_prompt(question, retriever),
        response_format=ToolStrategy(QueryResult),
        middleware=[ModelCallLimitMiddleware(run_limit=5, exit_behavior="end")],
    )
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result.get("structured_response")


if __name__ == "__main__":
    print("Building RAG retriever...")
    retriever = build_retriever(k=3)
    print("Ready.\n")

    questions = [
        "Is Peter the father of Chris?",        # should be true
        "Is Carter the grandfather of Stewie?", # multi-hop through grandparent rule
        "Is Meg a brother of Stewie?",          # meg is female, should be false
        "Is Brian a parent of Peter?",          # no fact for this, should be false
    ]

    for q in questions:
        print(f"Q: {q}")
        r = run_query(q, retriever)
        if r:
            print(f"Answer: {r.answer}")
            print(f"Trace:  {r.trace}")
        else:
            print("Answer: (limit reached)")
        print()
