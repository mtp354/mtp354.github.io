---
title: "Algorithms & Theory"
excerpt: "Canonical quantum algorithms and the references that explain them well."
categories:
  - algorithms-theory
tags:
  - vqe
  - qaoa
  - shor
  - grover
  - hhl
date: 2026-05-06
---

A friendly tour of the quantum algorithms I keep coming back to, organized
the same way Stephen Jordan organizes his
[Quantum Algorithm Zoo](https://quantumalgorithmzoo.org/) — which is the
single best catalog out there. Click any group below to expand the table.
Speedups and short descriptions are summarized from the Zoo (cite as: Stephen
P. Jordan, *Quantum Algorithm Zoo*).

## Personal short list

A handful of "if you only learn five, learn these":

- **Shor's algorithm** — Shor (1994). [arXiv:quant-ph/9508027](https://arxiv.org/abs/quant-ph/9508027).
- **Grover's algorithm** — Grover (1996). [arXiv:quant-ph/9605043](https://arxiv.org/abs/quant-ph/9605043).
- **HHL (linear systems)** — Harrow, Hassidim, Lloyd (2009). [arXiv:0811.3171](https://arxiv.org/abs/0811.3171).
- **VQE** — Peruzzo et al. (2014). [arXiv:1304.3061](https://arxiv.org/abs/1304.3061).
- **QAOA** — Farhi, Goldstone, Gutmann (2014). [arXiv:1411.4028](https://arxiv.org/abs/1411.4028).

For broader review reading: Cerezo et al. on
[variational algorithms](https://arxiv.org/abs/2012.09265), Georgescu et al.
on [quantum simulation](https://arxiv.org/abs/1308.6253), McArdle et al. on
[quantum chemistry](https://arxiv.org/abs/1808.10402), and Childs on
[quantum walks](https://arxiv.org/abs/0806.1972).

## Full Algorithm Zoo (collapsible)

<details markdown="1">
<summary><strong>Algebraic & Number Theoretic Algorithms</strong></summary>

| Algorithm | Speedup | One-line description |
| --- | --- | --- |
| Factoring (Shor) | Superpolynomial | Factor an n-bit integer in $\tilde O(n^3)$; breaks RSA. |
| Discrete Logarithms | Superpolynomial | Solves DLP over groups; breaks DSA, ECDSA, Diffie–Hellman. |
| Pell's Equation | Superpolynomial | Find the fundamental solution to $x^2-dy^2=1$ in poly time. |
| Principal Ideal | Superpolynomial | Decide whether an ideal of $\mathbb{Z}[\sqrt d]$ is principal. |
| Unit Group | Superpolynomial | Compute generators of the unit group of a number field. |
| Class Group | Superpolynomial | Compute the class group of a number field. |
| Gauss Sums | Superpolynomial | Estimate Gauss sums over finite fields/rings to poly precision. |
| Primality Proving | Polynomial | Donis-Vela–Garcia-Escartin: $O(n^2 (\log n)^3 \log\log n)$. |
| Solving Exponential Congruences | Polynomial | $\tilde O(q^{3/8})$ vs. classical $\tilde O(q^{9/8})$. |
| Matrix Elements & Multiplicities of Group Reps | Superpolynomial | Approximate Clebsch–Gordan transforms / multiplicities. |
| Verifying Matrix Products | Polynomial | $O(n^{5/3})$ check that $AB=C$ via quantum walks. |
| Subset-sum | Polynomial | $2^{0.241 n}$ vs. classical $2^{0.291 n}$ for hard instances. |
| Decoding | Varies | Speedups for convolutional and simplex codes. |
| Quantum Cryptanalysis | Various | Isogeny attacks, Grover-accelerated key search, Simon-style attacks on block ciphers. |

</details>

<details markdown="1">
<summary><strong>Oracular Algorithms</strong></summary>

| Algorithm | Speedup | One-line description |
| --- | --- | --- |
| Searching (Grover) | Polynomial | Find a marked item in an unsorted list with $O(\sqrt N)$ queries. |
| Abelian Hidden Subgroup | Superpolynomial | Common ancestor of Shor, Simon, period-finding. |
| Bernstein–Vazirani | Polynomial / Exp. recursive | Recover a hidden inner-product string in 1 query. |
| Deutsch–Jozsa | Exp. over P | Distinguish constant vs. balanced functions in 1 query. |
| Hidden Subgroup (non-Abelian) | Varies | Includes graph isomorphism as a special case. |
| Hidden Shift | Varies | Kuperberg's subexponential dihedral HSP, Boolean hidden shift, etc. |
| Pattern Matching | Superpolynomial / Polynomial | Average-case poly-log speedup; $\tilde O(\sqrt n)$ string matching. |
| Ordered Search | Constant factor | $0.433\log_2 N$ queries vs. classical $\log_2 N$. |
| Graph Properties (adjacency) | Polynomial | $\Theta(n^{3/2})$ for connectivity, MST, shortest paths. |
| Graph Properties (array model) | Polynomial | st-connectivity, bipartiteness, cycle detection in $\tilde O(\sqrt{Nd})$. |
| Welded Tree | Superpolynomial | Exponential separation for traversal of a glued binary tree. |
| Collision & Element Distinctness | Polynomial | $O(N^{1/3})$ collisions; $O(N^{2/3})$ element distinctness. |
| Hidden Nonlinear Structures | Superpolynomial | Identify hidden polynomial subsets of an Abelian group. |
| Group Order & Membership | Superpolynomial | Polylog queries to learn $\lvert G\rvert$ for Abelian black-box groups. |
| Counterfeit Coins | Polynomial | Identify $k$ fakes in $O(k^{1/4})$ queries. |
| Matrix Rank | Polynomial | Span-program-based query speedups. |
| Matrix Multiplication over Semirings | Polynomial | Sub-cubic Boolean matrix multiplication. |
| Subset Finding (k-subset-sum) | Polynomial | $O(\lvert D\rvert^{k/(k+1)})$ queries; tight. |
| Search with Wildcards | Polynomial | $\Theta(\sqrt n)$ via Pretty Good Measurement. |
| Network Flows / Matching | Polynomial | Quantum walk speedups for bipartite matching and max flow. |
| Electrical Resistance | Superpolynomial | $\mathrm{poly}(\log n)$ time for well-connected graphs. |
| Junta & Group Testing | Polynomial | Test whether $f$ depends on at most $k$ inputs. |
| NAND Trees / Formula Evaluation | Polynomial | Span-program / quantum-walk evaluation of Boolean formulas. |
| Statistical Difference | Polynomial | $O(\sqrt N)$ to estimate $L_1$ distance of two distributions. |
| Finite Rings & Ideals | Superpolynomial | Polylog query algorithms for ideal membership. |
| Constraint Satisfaction (k-SAT) | Polynomial | Quantum 2-SAT, Schöning-style speedups. |

</details>

<details markdown="1">
<summary><strong>Approximation & Simulation Algorithms</strong></summary>

| Algorithm | Speedup | One-line description |
| --- | --- | --- |
| Hamiltonian Dynamics | Superpolynomial | Simulate $e^{-iHt}$ in $\mathrm{poly}(n,t)$; the original Feynman motivation. |
| Eigenstates & Thermal States | Superpolynomial | Prepare ground / Gibbs states for many Hamiltonian classes. |
| Open Quantum Systems | Superpolynomial | Lindbladian simulation, Markovian and non-Markovian dynamics. |
| Quantum Field Theory | Superpolynomial | Scattering in scalar / fermionic / gauge theories. |
| Knot Invariants | Superpolynomial | Approximate the Jones / HOMFLY polynomial; BQP-complete. |
| Three-manifold Invariants | Superpolynomial | Turaev–Viro invariants are universal for quantum computation. |
| Partition Functions | Superpolynomial | Tutte / Potts / Ising via quantum walks and thermalization. |
| Zeta Functions | Superpolynomial | Counting points on curves over finite fields (Kedlaya). |
| Weight Enumerators | Superpolynomial | Sign of QWGT is BQP-complete (Knill–Laflamme). |
| Simulated Annealing | Polynomial | Quantum Markov-chain mixing with $1/\sqrt\delta$ scaling. |
| String Rewriting | Superpolynomial | Certain grammar-rewriting decision problems are PromiseBQP-complete. |
| Matrix Powers | Superpolynomial | Estimate entries of $A^t$ for sparse $A$. |
| Probabilistic Sampling | Superpolynomial | BosonSampling, IQP, random-circuit sampling — basis of "quantum supremacy." |

</details>

<details markdown="1">
<summary><strong>Optimization, Numerics, and Machine Learning</strong></summary>

| Algorithm | Speedup | One-line description |
| --- | --- | --- |
| Adiabatic Algorithms | Varies | Slow Hamiltonian interpolation; PageRank, training, graph problems. |
| Quantum Approximate Optimization (QAOA) | Superpolynomial (some cases) | Variational ansatz for combinatorial optimization. |
| Optimization by Decoded Quantum Interferometry (DQI) | Superpolynomial | Reduces optimization to classical decoding via QFT. |
| Gradient Estimation | Polynomial | Estimate $\nabla f$ in $O(d)$ queries vs. $\Omega(d^2)$ classical. |
| Convex Optimization | Polynomial | Speedups for membership / separation oracles. |
| Semidefinite Programming | Polynomial (with exceptions) | Brandao–Svore and follow-ups. |
| Linear Programming | Polynomial | Quantum interior-point methods. |
| Linear Systems (HHL) | Superpolynomial | $O(\log n)$ solution sampling for sparse, well-conditioned $Ax=b$. |
| Estimating Determinants & Spectral Sums | Superpolynomial | Phase-estimation Monte Carlo on the maximally mixed state. |
| Differential Equations | Superpolynomial / Polynomial | Linear ODEs, PDEs, finite-element method, Poisson, Black–Scholes. |
| Coupled Classical Oscillators | Superpolynomial | Babbush et al. exponential simulation speedup. |
| Machine Learning | Varies | Linear-systems-based ML, kernels, perceptrons; many "dequantized" results. |
| Tensor Principal Component Analysis | Polynomial (quartic) | Recover planted signal in spiked tensor model. |
| Topological Data Analysis | Superpolynomial | Persistent Betti numbers and Khovanov homology. |
| Approximating Nash Equilibria | Polynomial | $\epsilon$-Nash for zero-sum payoff matrices. |
| Quantum Dynamic Programming | Polynomial | Path-in-the-hypercube; vertex-coloring style speedups. |
| Top Eigenvectors | Polynomial | $\tilde O(d^{3/2})$ vs. classical $\tilde O(d^2)$. |
| Lattice Problems | Polynomial | Chen–Liu–Zhandry, Eldar–Hallgren — partial advantage in special parameter regimes. |
| Double-bracket Quantum Algorithms | Unknown | Group-commutator discretization of double-bracket flows. |
| Monte Carlo Methods | Polynomial (quadratic) | Mean estimation with $O(1/\epsilon)$ vs. $O(1/\epsilon^2)$ samples. |

</details>

> Source and full descriptions / references: Stephen P. Jordan,
> [Quantum Algorithm Zoo](https://quantumalgorithmzoo.org/). The tables above
> are a condensed snapshot — visit the Zoo for the full per-algorithm
> bibliography (currently 500+ references) and code links.

