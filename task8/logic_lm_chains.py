import subprocess
import os
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
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


def build_retriever(k=3):
    docs = []
    for prolog, desc in FACT_DESCRIPTIONS.items():
        docs.append(Document(page_content=desc, metadata={"type": "fact", "prolog": prolog + "."}))
    for functor, desc in RULE_DESCRIPTIONS.items():
        docs.append(Document(page_content=desc, metadata={"type": "rule", "functor": functor}))

    vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings(), collection_name="family_guy_kb_chains")
    return vectorstore.as_retriever(search_kwargs={"k": k})


def run_prolog(goal):
    wrapped = f"({goal} -> write(true) ; write(false)), nl, halt"
    try:
        result = subprocess.run(
            ["swipl", "-q", "-l", KB_PATH, "-g", wrapped],
            capture_output=True, text=True, timeout=10,
        )
        if "ERROR:" in result.stderr:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip() if result.stdout.strip() else "false"
    except FileNotFoundError:
        return "Error: swipl not found"
    except subprocess.TimeoutExpired:
        return "Error: timed out"


model = init_chat_model("openai:gpt-4o-mini", temperature=0)
parser = StrOutputParser()

# step 1: translate NL question into a prolog goal
translate_chain = ChatPromptTemplate.from_template("""
You are a Prolog expert working with a Family Guy knowledge base.

Available predicates: father/2, mother/2, sibling/2, brother/2, sister/2,
grandparent/2, grandfather/2, grandmother/2, in_law/2, parent/2, male/1, female/1, married/2

Individuals: peter, lois, chris, stewie, meg, brian, carter, babs

Argument order — the SECOND argument has the property being checked:
- father(X,Y): X is the father of Y
- brother(X,Y): Y is the brother, NOT X — "Is Meg a brother of Stewie?" → brother(stewie, meg)
- sister(X,Y): Y is the sister, NOT X — "Is Meg a sister of Stewie?" → sister(stewie, meg)
- grandfather(X,Y): X is the grandfather of Y

Relevant KB context:
{context}

Translate this question into a single Prolog goal.
Output ONLY the raw goal — no backticks, no punctuation, no explanation. Example: father(peter, chris)

Question: {question}

Prolog goal:""") | model | parser

# step 2: generate a trace explaining the result
trace_chain = ChatPromptTemplate.from_template("""
Explain in 2-3 sentences how Prolog arrived at this result, citing specific facts and rules used.

Question: {question}
Prolog goal: {goal}
Result: {result}

Relevant KB context:
{context}

Trace:""") | model | parser


def run_query(question, retriever):
    docs = retriever.invoke(question)
    context = "\n".join(f"- {d.page_content}" for d in docs)

    # translate -> execute -> trace
    raw_goal = translate_chain.invoke({"question": question, "context": context}).strip()
    # strip any backticks or trailing punctuation the LLM might add
    goal = raw_goal.strip("`").rstrip(".").lower()
    result = run_prolog(goal)
    trace = trace_chain.invoke({"question": question, "goal": goal, "result": result, "context": context})

    return goal, result, trace


if __name__ == "__main__":
    print("Building RAG retriever...")
    retriever = build_retriever()
    print("Ready.\n")

    questions = [
        "Is Peter the father of Chris?",        # should be true
        "Is Carter the grandfather of Stewie?", # multi-hop through grandparent rule
        "Is Meg a brother of Stewie?",          # meg is female, should be false
        "Is Brian a parent of Peter?",          # no fact for this, should be false
    ]

    for q in questions:
        print(f"Q: {q}")
        goal, result, trace = run_query(q, retriever)
        print(f"Goal:   {goal}")
        print(f"Answer: {result}")
        print(f"Trace:  {trace}")
        print()
