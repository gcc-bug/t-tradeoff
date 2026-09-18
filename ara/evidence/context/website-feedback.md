# User-supplied Website Feedback

Source: pasted attachment supplied in the installation/assessment request. The text is external AI advice, not user endorsement or verified research evidence.

**I would keep the tradeoff goal, move the main research effort toward high-level synthesis, and retain gate-level resynthesis as a supporting tool.** The current evidence does not justify making adaptive pass selection our central contribution.

Your three options are not equally supported:

| Direction                                      | My assessment                                                                                                               |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Design our own iterative resynthesis algorithm | Worth pursuing only after identifying a transformation or search decision that existing methods miss                        |
| Develop a high-level construction              | The most promising next direction, provided it captures a general structure rather than a collection of isolated identities |
| Abandon the tradeoff objective                 | Premature; the experiments have tested a narrow transformation space, not the feasibility of the objective                  |

**The main distinction is between finding a better circuit among existing choices and creating better choices.**

Our current search mostly explores compositions of existing optimizers. The latest result shows that a simple fixed sequence finds the same endpoint. That weakens the motivation for a more elaborate controller **on the current action set**. It tells us little about whether a different representation could yield substantially better circuits.

### 1. What would make resynthesis worth continuing?

An algorithm we design would need a concrete advantage beyond deciding which tool to call next. For example, it could search a class of equivalent phase representations that the current backends do not generate, while using their synthesis routines to implement the candidates.

But “joint optimization” and “recover arithmetic dependencies” are already established directions. Matroid-based synthesis already addresses T-count, T-depth, and additional ancillas; relational analysis already exploits nonlinear relationships in arithmetic circuits. We would need a narrower missing capability. [Ancilla-assisted synthesis](https://arxiv.org/abs/1303.2042), [Relational analysis](https://arxiv.org/abs/2410.23493)

**I would pause further work on pass-order search.** Keep the existing integrations to check whether any proposed high-level advantage survives strong downstream optimization.

### 2. The high-level opportunity I would investigate

HWP gives us a useful formulation:

$$
U_F|x\rangle=e^{i\theta F(x)}|x\rangle,
\qquad F(x)=\sum_j p_j(x).
$$

Ordinary HWP computes the weight of the predicates. A broader question is:

> **Can we implement the phase by computing a cheaper representation of \(F\), without explicitly constructing and counting every predicate?**

This changes the object being optimized: the computation of the phase function itself.

For illustration, consider all edges between two disjoint vertex sets of sizes \(a,b\). Let their input Hamming weights be \(u,v\). The number of cut edges is

$$
F(x)=u(b-v)+(a-u)v=bu+av-2uv.
$$

The same phase can therefore be expressed using two population counts and arithmetic on their outputs, rather than explicitly counting \(ab\) edge parities.

**This identity is not a novelty claim, and it does not automatically produce a cheaper circuit.** Multiplication, phasing, workspace, and cleanup all cost resources. Its value here is that it identifies a genuinely different construction whose scaling and tradeoffs can be analyzed.

That is the kind of opportunity I would seek: a recurring workload structure that changes what must be computed. A rule is useful when it recognizes an entire parameterized family and comes with a cost argument. Our earlier triple rule was insufficient because we never established that broader reach.

HWP already has substantial prior work, including resource-optimized simulation constructions. We must compare against those constructions under matching assumptions—not only our current unitary implementation. [Kivlichan et al.](https://arxiv.org/abs/1902.10673), [Kan–Symons](https://arxiv.org/abs/2411.02160)

### 3. Is the tradeoff target unreachable?

**We have no evidence that it is unreachable. We also have no evidence yet that our approach improves the established frontier.**

The achievable target should be:

> For a specified workload family and resource regime, produce better circuits under the same error and execution assumptions.

It need not mean simultaneously minimizing all three resources, or beating every method on every input. A lower T-count at a fixed ancilla budget and depth limit is already a meaningful result.

What should become optional is **dynamic preferences**. They were our proposed mechanism, not the ultimate scientific goal. If a structural synthesis algorithm obtains better tradeoffs without changing preferences during execution, that still answers the important problem.

**My suggested next research step is one parameterized construction study:** identify a workload structure, derive an alternative phase computation, and compare its complete resource scaling with the strongest applicable construction. Establish where it should win before building another search algorithm.

That gives us a decisive checkpoint: either we discover a useful new construction space for synthesis to explore, or we learn that the chosen structure is already handled adequately by prior work.
