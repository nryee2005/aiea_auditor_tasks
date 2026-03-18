% Facts - Characters
male(peter).
male(chris).
male(stewie).
male(brian).
male(carter).

female(lois).
female(meg).
female(babs).

% Facts - Relationships
parent(peter, chris).
parent(peter, stewie).
parent(peter, meg).
parent(lois, chris).
parent(lois, stewie).
parent(lois, meg).
parent(carter, lois).
parent(babs, lois).

married(peter, lois).
married(lois, peter).
married(carter, babs).
married(babs, carter).

% Rules
mother(X, Y) :- parent(X, Y), female(X).
father(X, Y) :- parent(X, Y), male(X).
sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \= Y.
brother(X, Y) :- sibling(X, Y), male(Y).
sister(X, Y) :- sibling(X, Y), female(Y).
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
grandfather(X, Z) :- grandparent(X, Z), male(X).
grandmother(X, Z) :- grandparent(X, Z), female(X).
in_law(X, Y) :- married(X, Z), parent(Z, Y).