# Probabilistic Soft Logic Tutorial
## Installation / Prerequisites
You will need to have Java installed. PSL requires Java 8 or higher.
- On Mac, you can install Java with Homebrew using `brew install Java`

Next:
1. You can look at the source code by cloning the following repository: https://github.com/linqs/psl.
2. You can also see and run working examples by cloning this repository: https://github.com/linqs/psl-examples
	- These examples will automatically fetch any dependencies required to execute
	- If you want the PSL CLI jar, it is available from Maven Central
## Writing Rules
```
# model.psl
1.0: Knows(A, B) & Likes(A, X) -> Likes(B, X) ^2
0.5: ~Likes(A, B) -> ~Likes(B, A) ^2
Knows(A, B) = Knows(B, A) .
```
Each rule starts with a weight where higher means the rule is more strongly enforced. The body appears before `->` and the head after it. `&` connects multiple conditions in the body. `^2` squares the hinge-loss for smoother optimization. Rules ending in `.` with no weight are hard constraints that must always hold.
## Setting Up Data
```yaml
predicates:
  Knows/2: closed
  Likes/2: open

observations:
  Knows: knows_obs.txt
  Likes: likes_obs.txt

targets:
  Likes: likes_targets.txt

truth:
  Likes: likes_truth.txt
```
`closed` predicates are fully observed and fixed during inference. `open` predicates are what PSL infers. Observation files are tab-separated `.txt` files where each line is a ground atom with an optional truth value, for example `Alice Pizza 0.9`. The `targets` section tells PSL which atoms to infer, and `truth` provides ground truth labels for weight learning or evaluation.
## Running Inference
```bash
java -jar psl-cli.jar --infer --model model.psl --data model.data --output results/
```
This reads your rules and data, runs MPE inference, and writes inferred truth values to the output directory as tab-separated files. Each line in the output is a ground atom and its inferred value between 0.0 and 1.0.
## PSL Inference Example
Using the `model.psl` and `model.data` files above, we can run inference using:
```txt
# knows_obs.txt
Alice Bob 
Bob Carol
```
```txt
### likes_obs.txt
Alice Pizza 1.0 
Alice Sushi 0.8
```
After running the command in the Running Inference section, we get an output result that looks like:
```txt
Bob Pizza 0.91 
Bob Sushi 0.74 
Carol Pizza 0.63
```
Because Alice likes pizza and sushi and knows Bob, PSL infers Bob probably likes them too. Bob knows Carol, so Carol gets weaker but nonzero inferred values through the transitive chain.