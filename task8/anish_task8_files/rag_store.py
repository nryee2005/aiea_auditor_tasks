"""
rag_store.py
------------
Parses simpsons_kb.pl into individual fact/rule strings, embeds them
into a ChromaDB vector store, and exposes a retriever you can plug
into a LangChain chain.
"""
from __future__ import annotations

import re
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


KB_PATH = Path(__file__).parent / "simpsons_kb.pl"

# Human-readable descriptions for every fact/rule so embeddings are meaningful
FACT_DESCRIPTIONS = {
    "male(homer)":    "Homer is male.",
    "male(bart)":     "Bart is male.",
    "male(abe)":      "Abe is male.",
    "male(herb)":     "Herb is male.",
    "female(marge)":  "Marge is female.",
    "female(lisa)":   "Lisa is female.",
    "female(maggie)": "Maggie is female.",
    "female(mona)":   "Mona is female.",
    "female(patty)":  "Patty is female.",
    "female(selma)":  "Selma is female.",
    "parent(homer, bart)":   "Homer is a parent of Bart.",
    "parent(homer, lisa)":   "Homer is a parent of Lisa.",
    "parent(homer, maggie)": "Homer is a parent of Maggie.",
    "parent(marge, bart)":   "Marge is a parent of Bart.",
    "parent(marge, lisa)":   "Marge is a parent of Lisa.",
    "parent(marge, maggie)": "Marge is a parent of Maggie.",
    "parent(abe, homer)":    "Abe is a parent of Homer.",
    "parent(abe, herb)":     "Abe is a parent of Herb.",
    "parent(mona, homer)":   "Mona is a parent of Homer.",
    "sibling(patty, marge)": "Patty is a sibling of Marge.",
    "sibling(marge, patty)": "Marge is a sibling of Patty.",
    "sibling(selma, marge)": "Selma is a sibling of Marge.",
    "sibling(marge, selma)": "Marge is a sibling of Selma.",
}

RULE_DESCRIPTIONS = {
    "mother": "mother(X, Y) is true if X is a parent of Y and X is female.",
    "father": "father(X, Y) is true if X is a parent of Y and X is male.",
    "grandparent": "grandparent(X, Y) is true if X is a parent of Z and Z is a parent of Y.",
    "grandmother": "grandmother(X, Y) is true if X is a grandparent of Y and X is female.",
    "grandfather": "grandfather(X, Y) is true if X is a grandparent of Y and X is male.",
    "ancestor": "ancestor(X, Y) is true if X is a parent of Y, or X is a parent of Z and Z is an ancestor of Y (recursive).",
    "aunt": "aunt(X, Y) is true if X is a sibling of P, P is a parent of Y, and X is female.",
    "related": "related(X, Y) is true if X and Y share a common ancestor and X is not Y.",
}


def _parse_kb() -> list[Document]:
    """Convert every fact and rule in the KB into a LangChain Document."""
    docs: list[Document] = []

    # Facts
    for prolog_fact, description in FACT_DESCRIPTIONS.items():
        docs.append(Document(
            page_content=description,
            metadata={"type": "fact", "prolog": prolog_fact + "."},
        ))

    # Rules
    raw = KB_PATH.read_text(encoding="utf-8")
    for functor, description in RULE_DESCRIPTIONS.items():
        # Pull the raw Prolog rule text out of the file
        pattern = rf"^{functor}\(.*?(?=\n\n|\n%|\Z)"
        match = re.search(pattern, raw, re.MULTILINE | re.DOTALL)
        prolog_text = match.group(0).strip() if match else f"{functor}(...)."
        docs.append(Document(
            page_content=description,
            metadata={"type": "rule", "functor": functor, "prolog": prolog_text},
        ))

    return docs


def build_retriever(k: int = 4):
    """
    Build (or load from cache) a Chroma vector store from the KB,
    and return a retriever that fetches the top-k most relevant entries.
    """
    docs = _parse_kb()
    embeddings = OpenAIEmbeddings()

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="simpsons_kb",
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


if __name__ == "__main__":
    # Quick smoke-test
    retriever = build_retriever()
    results = retriever.invoke("Who is the grandmother of Bart?")
    print("RAG retrieval results for 'Who is the grandmother of Bart?':")
    for doc in results:
        print(f"  [{doc.metadata['type']}] {doc.page_content}")
        print(f"    Prolog: {doc.metadata.get('prolog', '')}")