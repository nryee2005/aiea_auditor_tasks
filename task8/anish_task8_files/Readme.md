# Task 8 — LangChain + Logic-LM Inference Engine

Integrates LangChain into a logical inference engine over a Prolog knowledge base,
following the Logic-LM paper architecture.

---

## Architecture

```
Natural Language Query
        │
        ▼
┌───────────────────┐
│   RAG Retrieval   │  ← ChromaDB vector store built from simpsons_kb.pl
│  (rag_store.py)   │     retrieves the most relevant facts & rules
└────────┬──────────┘
         │ context (top-k KB entries)
         ▼
┌───────────────────┐
│ Translate Chain   │  ← LLM converts NL query → Prolog goal
│   (chains.py)     │     e.g. "Is Marge the mother of Bart?" → mother(marge, bart)
└────────┬──────────┘
         │ prolog goal
         ▼
┌───────────────────┐
│  Prolog Executor  │  ← Runs goal against SWI-Prolog + simpsons_kb.pl
│   (chains.py)     │     returns True/False + any variable bindings
└────────┬──────────┘
         │ result + bindings
         ▼
┌───────────────────┐
│   Trace Chain     │  ← LLM generates step-by-step deduction trace
│   (chains.py)     │     citing specific facts and rules from the KB
└────────┬──────────┘
         │ trace
         ▼
┌───────────────────┐
│   Verify Chain    │  ← LLM produces final TRUE/FALSE verdict + reason
│   (chains.py)     │
└────────┬──────────┘
         │
         ▼
    TRUE / FALSE + Inference Trace
```

This mirrors the Logic-LM paper (Pan et al., 2023): use an LLM to translate
natural language into a formal logic program, execute it with a symbolic solver,
then use the LLM again to explain the result.

---

## Files

| File | Purpose |
|---|---|
| `simpsons_kb.pl` | Prolog knowledge base (20 facts, 8 rules) |
| `rag_store.py` | Parses KB → ChromaDB vector store, exposes retriever |
| `chains.py` | All 4 LangChain chains + Prolog executor |
| `main.py` | Runs example queries end-to-end |

---

## Setup

```cmd
pip install langchain langchain-openai langchain-community chromadb
```

SWI-Prolog must be installed and `swipl` must be on your PATH:
- Download: https://www.swi-prolog.org/Download.html

Set your OpenAI API key:
```cmd
set OPENAI_API_KEY=sk-proj-...
```

---

## Run

```cmd
python main.py
```

---

## Example Output

```
======================================================================
  QUERY : Is Marge the mother of Bart?
======================================================================

[ RAG CONTEXT — KB entries retrieved ]
  [fact] Marge is a parent of Bart.  (Prolog: parent(marge, bart).)
  [fact] Marge is female.  (Prolog: female(marge).)
  [rule] mother(X, Y) is true if X is a parent of Y and X is female.

[ PROLOG GOAL  (LLM translation) ]
  mother(marge, bart)

[ PROLOG EXECUTION ]
  Goal    : mother(marge, bart)
  Result  : True
  Raw SWI : true

[ INFERENCE TRACE ]
  1. From the KB: parent(marge, bart) — Marge is a parent of Bart.
  2. From the KB: female(marge) — Marge is female.
  3. Applying rule: mother(X, Y) :- parent(X, Y), female(X).
     Substituting X=marge, Y=bart: both conditions satisfied.
  4. Therefore, mother(marge, bart) is provable.
  Therefore, Is Marge the mother of Bart? is TRUE.

[ VERDICT ]
  Answer: TRUE
  Reason: Marge is a parent of Bart and is female, satisfying the mother rule.
```

---

## Reference

Pan et al. (2023). *Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning.* https://arxiv.org/abs/2305.12295