from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
from typing import Any, Dict, List

PROMPTS_DIR = Path(__file__).parent / "prompts"
OUT_DIR = Path(__file__).parent / "outputs"


def load_module(module_name: str):
    # Load prompts/<module_name>.py as a Python module, even if prompts is not a package.
    module_path = PROMPTS_DIR / f"{module_name}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Could not find {module_path}")

    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to create import spec for {module_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_prompt_items(mod) -> List[Dict[str, Any]]:
    """
    Priority:
      1) PROMPTS (list of dicts) if present
      2) get_prompts() if present and returns list
      3) else make ONE default prompt using build_problem/render with placeholder context/question
    """
    if hasattr(mod, "PROMPTS"):
        prompts = getattr(mod, "PROMPTS")
        if isinstance(prompts, list) and len(prompts) > 0:
            return prompts

    if hasattr(mod, "get_prompts"):
        prompts = mod.get_prompts()
        if isinstance(prompts, list) and len(prompts) > 0:
            return prompts

    # Fallback: create a single item for build_problem/render modules
    return [{
        "id": f"{getattr(mod, 'NAME', mod.__name__)}_01",
        "context": "Placeholder context (replace with real sample from paper if desired).",
        "question": "Placeholder question (replace with real sample from paper if desired).",
        "expected": None,
    }]


def format_one(mod, item: Dict[str, Any]) -> str:
    """
    Try common interfaces:
      - render(build_problem(context, question))
      - format_prompt(context, question)
      - build_problem(context, question) (as dict) then pretty print
    """
    context = item.get("context", "")
    question = item.get("question", "")

    # Preferred: build_problem + render (what your folio/ar_lsat/etc. have)
    if hasattr(mod, "build_problem") and hasattr(mod, "render"):
        prob = mod.build_problem(context, question)
        return mod.render(prob)

    # Next: format_prompt (your proofwriter has this)
    if hasattr(mod, "format_prompt"):
        return mod.format_prompt(context, question)

    # Last resort: build_problem only
    if hasattr(mod, "build_problem"):
        prob = mod.build_problem(context, question)
        return str(prob)

    raise AttributeError(
        f"{mod.__name__} has no known formatting interface. "
        f"Expected build_problem+render OR format_prompt OR build_problem."
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Prompt module name (e.g., proofwriter, folio, logical_deduction, pro_onto_qa, al_lsat)")
    parser.add_argument("--all", action="store_true", help="Run all prompts found in PROMPTS/get_prompts() instead of just the first.")
    args = parser.parse_args()

    ensure_out_dir()
    mod = load_module(args.name)

    items = get_prompt_items(mod)
    if not args.all:
        items = items[:1]

    for item in items:
        pid = item.get("id", "unknown")
        out_text = format_one(mod, item)

        header = f"\n========== {args.name.upper()} | {pid} ==========\n"
        expected = item.get("expected")
        if expected is not None:
            header += f"(expected: {expected})\n"

        print(header)
        print(out_text)

        out_file = OUT_DIR / f"{args.name}_{pid}.txt"
        out_file.write_text(header + out_text + "\n", encoding="utf-8")
        print(f"\n[saved] {out_file}\n")


if __name__ == "__main__":
    main()