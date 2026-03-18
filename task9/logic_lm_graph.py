import os
import subprocess

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

KB_PATH = os.path.join(os.path.dirname(__file__), "family_guy_kb.pl")

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

def build_retriever(k=5):
    docs = []
    for prolog, description in FACT_DESCRIPTIONS.items():
        docs.append(Document(page_content=description, metadata={"type": "fact", "prolog": prolog + "."}))
    for functor, description in RULE_DESCRIPTIONS.items():
        docs.append(Document(page_content=description, metadata={"type": "rule", "functor": functor}))
    vectorstore = Chroma.from_documents(docs, OpenAIEmbeddings(), collection_name="family_guy_kb")
    return vectorstore.as_retriever(search_kwargs={"k": k})

@tool
def run_prolog_query(goal: str) -> str:
    """Run a Prolog goal against the Family Guy knowledge base. Returns 'true' or 'false'."""
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

class State(TypedDict):
    messages: Annotated[list, add_messages]
    context: str
    question: str
    prolog_result: str
    answer: str
    trace: str
    retries: int
    context_relevant: str
    refined_query: str

retriever = build_retriever()
model = init_chat_model("openai:gpt-3.5-turbo", temperature=0)

def retrieve_node(state: State) -> dict:
    query = state["refined_query"] or state["question"]
    docs = retriever.invoke(query)
    context = "".join(doc.page_content + "\n" for doc in docs)
    return {"context": context}

def llm_node(state: State) -> dict:
    system_prompt = f"""You are a logic reasoning agent with access to a Prolog knowledge base about Family Guy characters.
Use the run_prolog_query tool to answer questions.

Relevant facts and rules:
{state["context"]}"""
    messages = [SystemMessage(system_prompt)] + state["messages"]
    response = model.bind_tools([run_prolog_query]).invoke(messages)
    return {"messages": [response]}

def judge_node(state: State) -> dict:
    prolog_result = state["messages"][-1].content
    prompt = f"Given this question: {state['question']} and these retrieved facts: {state['context']}, was the context sufficient to answer the question? Reply with just yes or no."
    relevancy = model.invoke([HumanMessage(prompt)]).content.strip().lower()
    refined_query = ""
    if relevancy == "no":
        refine_prompt = f"""The question was: {state["question"]}
The retrieved facts were not sufficient: {state["context"]}
Generate a better search query to find more relevant facts. Reply with just the query."""
        refined_query = model.invoke([HumanMessage(refine_prompt)]).content.strip()

    return {"context_relevant": relevancy, "refined_query": refined_query, "prolog_result": prolog_result, "retries": state["retries"] + 1}

def router(state: State) -> str:
    if state["prolog_result"] in ("true", "false") or state["retries"] >= 3:
        return "respond"
    if state["context_relevant"] == "no":
        return "retrieve"  # re-fetch better context
    return "llm"

def respond_node(state: State) -> dict:
    answer = state["prolog_result"]
    trace = [m for m in state["messages"] if isinstance(m, AIMessage)][-1].content
    return {"answer": answer, "trace": trace}

tool_node = ToolNode([run_prolog_query])

graph = StateGraph(State)
graph.add_node("retrieve", retrieve_node)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)
graph.add_node("judge", judge_node)
graph.add_node("respond", respond_node)

graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "llm")
graph.add_conditional_edges("llm", tools_condition, {"tools": "tools", END: "respond"})
graph.add_edge("tools", "judge")
graph.add_conditional_edges("judge", router, {"respond": "respond", "llm": "llm", "retrieve": "retrieve"})
graph.add_edge("respond", END)

app = graph.compile()

if __name__ == "__main__":
    result = app.invoke({
        "question": "Is Peter the father of Chris?",
        "messages": [HumanMessage("Is Peter the father of Chris?")],
        "retries": 0,
        "context": "",
        "prolog_result": "",
        "answer": "",
        "trace": "",
        "context_relevant": "",
        "refined_query": "",
    })
    print("Answer:", result["answer"])
    print("Trace:", result["trace"])
