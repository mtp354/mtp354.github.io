---
title: "Software & Libraries"
excerpt: "Open-source frameworks for building, simulating, and running quantum programs."
categories:
  - software-libraries
tags:
  - qiskit
  - cirq
  - pennylane
  - simulators
date: 2026-05-06
---

A starter index of the quantum software ecosystem. Each entry below is a
jumping-off point — vendor docs are usually the most current source of truth.

## General-purpose SDKs

- [**Qiskit**](https://www.ibm.com/quantum/qiskit) — IBM's Python SDK; circuits,
  transpiler, primitives, and access to IBM Quantum hardware.
- [**Cirq**](https://quantumai.google/cirq) — Google's Python framework, geared
  toward NISQ experiments and gate-level control.
- [**PennyLane**](https://pennylane.ai/) — Xanadu's hybrid quantum/ML framework
  with autodiff across many backends.
- [**Q#**](https://learn.microsoft.com/azure/quantum/) — Microsoft's quantum
  programming language with Azure Quantum integration.

## Simulators

- [**Stim**](https://github.com/quantumlib/Stim) — Extremely fast Clifford and
  stabilizer simulator; the standard for QEC research.
- [**QuEST**](https://quest.qtechtheory.org/) — High-performance multi-threaded
  / GPU statevector and density-matrix simulator (C / Python).
- [**Qulacs**](https://github.com/qulacs/qulacs) — Fast C++ statevector
  simulator with Python bindings.

## Domain-specific

- [**OpenFermion**](https://quantumai.google/openfermion) — Fermionic operators
  and electronic-structure tooling.
- [**Mitiq**](https://mitiq.readthedocs.io/) — Error mitigation toolkit (ZNE,
  PEC, CDR, …) from the Unitary Foundation.
- [**TensorNetwork**](https://github.com/google/TensorNetwork) — Tensor network
  contractions for classical simulation of quantum circuits.

> _Stub — expand with personal notes, gotchas, and version pins as you use these._
