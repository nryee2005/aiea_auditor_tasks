# Task 5 — Logic-LM Prompt Formatting & Pipeline

## What This Does

1. Tests a Prolog knowledge base (from task 4) with SWI-Prolog queries.
2. Formats logic problems into the 5 Logic-LM prompt styles: ProofWriter, PrOntoQA, FOLIO, LogicalDeduction, AR-LSAT.
3. (Optional) Runs an end-to-end pipeline: GPT translates problems to Prolog, swipl executes them, self-refines on errors, and compares answers.

## How to Run

```bash
# Run KB tests + prompt formatting demo
cd task5
python run_task5.py

# Run a single dataset's prompts
python run_prompts.py proofwriter --all

# Run the GPT → Prolog pipeline (requires OPENAI_API_KEY)
pip install openai python-dotenv
export OPENAI_API_KEY=your_key
python run_pipeline.py
```

## Requirements

- Python 3.10+
- `swipl` on PATH (SWI-Prolog)
- `openai` + `python-dotenv` (only for `run_pipeline.py`)

## Outputs

All results are saved to `outputs/`.
