from openai import OpenAI
from pyswip import Prolog
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
prolog = Prolog()
previous_response_id = None

user_input = input("Please input what natural language you'd like translated to prolog: ")

response = client.responses.create(
    model="gpt-4o",
    instructions="""Convert the user's natural language into Prolog facts and rules.
        Rules:
        - Use lowercase for atoms/constants (socrates, not Socrates)
        - Uppercase is ONLY for variables (X, Y, Person)
        - Define base facts BEFORE rules that use them
        - Output ONLY raw Prolog code
        - NO markdown, NO code blocks, NO backticks, NO explanations

        Example output:
        man(socrates).
        man(plato).
        mortal(X) :- man(X).""",
    input=user_input,
    previous_response_id=previous_response_id
)

previous_response_id = response.id
prolog_code = response.output_text

# Strip markdown code blocks if present
if prolog_code.startswith('```'):
    lines = prolog_code.split('\n')
    lines = [l for l in lines if not l.startswith('```')]
    prolog_code = '\n'.join(lines)

print("Translating to Prolog...\n")
print(f"{prolog_code}\n")

# Load facts/rules into Prolog
for line in prolog_code.strip().split('\n'):
    line = line.strip()
    if line and not line.startswith('%') and not line.startswith('```'):
        if line.endswith('.'):
            line = line[:-1]
        try:
            prolog.assertz(line)
        except Exception as e:
            print(f"Error loading: {line} - {e}")

print("Prolog loaded. Ask questions (type 'exit' to quit):\n")

# Query loop
while True:
    query_input = input("Question: ")
    if query_input.lower() in ["exit", "quit"]:
        break

    query_response = client.responses.create(
        model="gpt-4o",
        instructions="""Convert the question into a Prolog query.
            Output ONLY the query predicate. No '?-' prefix, no period, no explanation.
            Example: mortal(socrates)""",
        input=query_input,
        previous_response_id=previous_response_id
    )

    previous_response_id = query_response.id
    query = query_response.output_text.strip()
    print(f"Query: {query}")

    try:
        results = list(prolog.query(query))
        if results:
            if results == [{}]:
                print("Result: true\n")
            else:
                for r in results:
                    print(f"Result: {r}")
                print()
        else:
            print("Result: false\n")
    except Exception as e:
        print(f"Query error: {e}\n")


