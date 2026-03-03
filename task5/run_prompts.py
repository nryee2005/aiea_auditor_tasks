import argparse
import importlib.util
import os

# Set prompts and output directories
prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
out_dir = os.path.join(os.path.dirname(__file__), "outputs")


def load_module(name):
    # Dynamically load prompts/<name>.py as a module rather than normal import
    path = os.path.join(prompts_dir, f"{name}.py")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not find {path}")

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod # Returns module


def get_prompt_items(mod):
    # Try PROMPTS list first, then get_prompts(), then a placeholder for module
    if hasattr(mod, "PROMPTS") and len(mod.PROMPTS) > 0:
        return mod.PROMPTS

    if hasattr(mod, "get_prompts"):
        prompts = mod.get_prompts()
        if isinstance(prompts, list) and len(prompts) > 0:
            return prompts

    # Fallback placeholder if prompt mod doesn't have above attributes
    name = getattr(mod, "NAME", mod.__name__)
    return [{
        "id": f"{name}_01",
        "context": "Placeholder context (replace with real sample from paper if desired).",
        "question": "Placeholder question (replace with real sample from paper if desired).",
        "expected": None,
    }]


def format_one(mod, item):
    # Try different formatting interfaces that prompt modules can have
    context = item.get("context", "")
    question = item.get("question", "")

    # build_problem + render (used by pro_onto_qa, folio, ar_lsat, logical_deduction)
    if hasattr(mod, "build_problem") and hasattr(mod, "render"):
        prob = mod.build_problem(context, question)
        return mod.render(prob)

    # format_prompt (used by proofwriter)
    if hasattr(mod, "format_prompt"):
        return mod.format_prompt(context, question)

    # build_problem only, just print the dict
    if hasattr(mod, "build_problem"):
        return str(mod.build_problem(context, question))

    raise AttributeError(f"{mod.__name__} has no known formatting interface")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Dataset module name (e.g. proofwriter, pro_onto_qa)")
    parser.add_argument("--all", action="store_true", help="Run all prompts, not just the first")
    args = parser.parse_args()

    os.makedirs(out_dir, exist_ok=True)
    mod = load_module(args.name)
    items = get_prompt_items(mod)

    if not args.all:
        items = items[:1]

    for item in items:
        pid = item.get("id", "unknown")
        text = format_one(mod, item)

        # Print with header
        header = f"\n{args.name.upper()} | {pid}\n"
        expected = item.get("expected")
        if expected is not None:
            header += f"(expected: {expected})\n"

        print(header)
        print(text)

        # Save to file
        out_file = os.path.join(out_dir, f"{args.name}_{pid}.txt")
        with open(out_file, "w") as f:
            f.write(header + text + "\n")
        print(f"\n[saved] {out_file}\n")
