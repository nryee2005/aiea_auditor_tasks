from pyswip import Prolog

prolog = Prolog()

# Load in the knowledge base
prolog.consult("knowledge_base.pl")

# Should return [chris, stewie, meg]
results = list(prolog.query("mother(lois, X)"))
print(results)

# Should return true
results = list(prolog.query("father(peter, meg)"))
print(bool(results))

# Returns all parent relationships using two variables
results = list(prolog.query("parent(X, Y)"))
for r in results:
    print(f"{r['X']} is parent of {r['Y']}")