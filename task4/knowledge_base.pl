male(peter).
male(chris).
male(stewie).
male(brian).

female(lois).
female(meg).

parent(peter, chris).
parent(peter, stewie).
parent(peter, meg).
parent(lois, chris).
parent(lois, stewie).
parent(lois, meg).
owner(stewie, brian).

mother(X, Y) :- parent(X, Y), female(X).
father(X, Y) :- parent(X, Y), male(X).
brother(X, Y) :- parent(Z, X), parent(Z, Y), male(Y), X \= Y.
