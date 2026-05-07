---
title: "Quantum 101"
permalink: /quantum-101/
author_profile: true
toc: true
toc_sticky: true
---

A short, opinionated glossary of terms that come up constantly in quantum
computing. The goal is one or two sentences in plain English — enough to
follow a conversation or a paper abstract, not a textbook treatment.

If a definition here is wrong or unclear, please email me — I would
rather fix it than leave it confusing.

## Foundations

**Qubit.** The quantum analogue of a classical bit. Unlike a bit, which is
either 0 or 1, a qubit can be in a superposition of both until measured.

**Superposition.** A quantum state that is a weighted combination of
multiple basis states. Measurement collapses the superposition to one of
those basis states with a probability set by the weights.

**Entanglement.** A correlation between two or more qubits that cannot be
explained by any local description of each qubit individually. Measuring
one instantly constrains the outcomes of the others.

**Bloch sphere.** A geometric picture of a single qubit's state as a point
on the surface of a unit sphere. Useful for visualizing single-qubit
gates as rotations.

**Decoherence.** The process by which a qubit loses its quantum
information to the environment. The main reason near-term quantum
computers are noisy.

## Hardware regimes

**NISQ.** "Noisy intermediate-scale quantum" — Preskill's term for the
current era of quantum computers: tens to hundreds of physical qubits,
significant noise, no full error correction.

**Gate model.** The mainstream model of quantum computing: discrete
unitary gates applied to qubits, then measurement. What IBM, Google,
IonQ, and most others build.

**Adiabatic quantum computing / quantum annealing.** A different model
where the answer is encoded in the ground state of a slowly-changing
Hamiltonian. D-Wave is the best-known example.

## Algorithms

**Shor's algorithm.** A quantum algorithm that factors integers in
polynomial time. The reason post-quantum cryptography exists.

**Grover's algorithm.** A quantum algorithm that searches an unsorted
database of $N$ items in roughly $\sqrt{N}$ steps — a quadratic speedup
over classical.

**HHL.** The Harrow–Hassidim–Lloyd algorithm for solving linear systems.
Often invoked as a quantum primitive for machine learning, but with many
caveats about input/output access.

**QFT.** The quantum Fourier transform — the workhorse subroutine inside
Shor and many phase-estimation algorithms.

**Quantum walk.** Quantum analogue of a random walk; a building block for
search and graph algorithms.

**Hamiltonian simulation.** Using a quantum computer to simulate the time
evolution of another quantum system. The original motivating use case.

## Variational and hybrid

**VQE.** Variational quantum eigensolver — a hybrid algorithm that uses a
classical optimizer to tune a parameterized quantum circuit to find a
Hamiltonian's ground-state energy.

**QAOA.** Quantum approximate optimization algorithm — a related hybrid
approach for combinatorial optimization problems like Max-Cut.

## Error correction

**QEC.** Quantum error correction — encoding one logical qubit across
many physical qubits so that errors can be detected and reversed without
collapsing the state.

**Surface code.** The leading practical QEC scheme, well-suited to
nearest-neighbor 2D qubit layouts.

**Magic state.** A specific resource state that, combined with Clifford
gates, enables universal fault-tolerant computation. Producing them is
expensive, which is why "magic-state distillation" is a major topic.

## Milestones

**Quantum advantage / supremacy.** A demonstration that a quantum
computer solves a particular task faster than any known classical
algorithm running on the best available hardware. The benchmark task
matters as much as the result.
