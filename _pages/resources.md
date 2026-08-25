---
layout: archive
title: "Quantum Computing Resources"
permalink: /resources/
author_profile: true
---

{% include base_path %}

Welcome! This is a little corner of the site where I keep the quantum
computing tools, papers, and communities I genuinely rely on. Think of it
less as an exhaustive directory and more as a friend handing you the short
list of "things I actually use." It is inspired by the spirit of
[AstroBetter](https://www.astrobetter.com/wiki/Wiki+Home).

I try to keep this lean and current. If something here helped you, or if a
link is stale, please open an issue on the
[site repo]({{ site.repository | prepend: 'https://github.com/' }}) — I
appreciate the nudge.

## Quick Links

| Category | Highlights |
| --- | --- |
| [Software & Libraries](#software-libraries) | Qiskit, Cirq, PennyLane, Q#, Stim, OpenFermion |
| [Hardware & Providers](#hardware-providers) | IBM Quantum, IonQ, Quantinuum, Rigetti, QuEra, Pasqal |
| [Algorithms & Theory](#algorithms-theory) | VQE, QAOA, Shor, Grover, HHL, quantum walks |
| [Conferences & Community](#conferences-community) | QIP, TQC, QCE, Q2B, Unitary Foundation |
| [Papers & Reading Lists](#papers-reading-lists) | arXiv quant-ph, Quantum journal, surveys & textbooks |

---

## Articles

{% assign categories = "software-libraries,hardware-providers,algorithms-theory,conferences-community,papers-reading" | split: "," %}
{% assign labels = "Software & Libraries,Hardware & Providers,Algorithms & Theory,Conferences & Community,Papers & Reading Lists" | split: "," %}
{% assign slugs = "software-libraries,hardware-providers,algorithms-theory,conferences-community,papers-reading-lists" | split: "," %}

{% for cat in categories %}
  {% assign idx = forloop.index0 %}
  {% assign label = labels[idx] %}
  {% assign anchor = slugs[idx] %}
  <h3 id="{{ anchor }}">{{ label }}</h3>
  <ul>
  {% for entry in site.resources %}
    {% if entry.categories contains cat %}
      <li>
        <a href="{{ entry.url | relative_url }}">{{ entry.title }}</a>
        {% if entry.excerpt %} &mdash; {{ entry.excerpt | strip_html | strip_newlines | truncate: 160 }}{% endif %}
      </li>
    {% endif %}
  {% endfor %}
  </ul>
{% endfor %}

## Other Cool Links

- [Physics Pages](https://physicspages.com/) — Technical physics notes and worked explanations across topics including electrodynamics, quantum mechanics, relativity, thermal physics, astrophysics, and related mathematics.
- [The Theoretical Minimum](https://theoreticalminimum.com/courses) — Leonard Susskind's course catalogue for self-study, with a core sequence running from classical mechanics through statistical mechanics and cosmology plus supplemental courses.
- [The Feynman Lectures on Physics](https://www.feynmanlectures.caltech.edu/) — Caltech's online HTML edition of the classic Feynman, Leighton, and Sands lectures, covering mechanics, electromagnetism, matter, and quantum mechanics.
- [Sean Carroll's General Relativity Notes](https://preposterousuniverse.com/grnotes/) — Free graduate-level lecture notes on general relativity, covering special relativity, manifolds, curvature, gravitation, weak fields, black holes, and cosmology.
- [Quantum Algorithm Zoo](https://quantumalgorithmzoo.org/) — A broad catalogue of quantum algorithms organized by problem family, with speedup notes, references, and implementation links where available.
- [Group Tables and Subgroup Diagrams](https://hobbes.la.asu.edu/groups/groups.html) — An interactive finite-group tool for exploring group tables, generated subgroups, centralizers, conjugacy classes, quotient structure, and subgroup diagrams.
- [Palomar Registry](https://palomar-registry.org/about) — A public searchable registry of Lean formalizations, recording machine-checked proofs, immutable repository versions, exact formal statements, dependencies, and review metadata.
