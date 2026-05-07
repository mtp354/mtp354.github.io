---
layout: archive
title: "Quantum Computing Resources"
permalink: /resources/
author_profile: true
---

{% include base_path %}

A small, curated wiki of tools, papers, communities, and references I find
useful in quantum computing research. Inspired by
[AstroBetter](https://www.astrobetter.com/wiki/Wiki+Home), but focused on QC
and intentionally lean.

Suggestions or corrections? Open an issue on the
[site repo]({{ site.repository | prepend: 'https://github.com/' }}).

## Quick Links

| Category | Highlights |
| --- | --- |
| [Software & Libraries](#software--libraries) | Qiskit, Cirq, PennyLane, Q#, Stim, OpenFermion |
| [Hardware & Providers](#hardware--providers) | IBM Quantum, IonQ, Quantinuum, Rigetti, QuEra, Pasqal |
| [Algorithms & Theory](#algorithms--theory) | VQE, QAOA, Shor, Grover, HHL, quantum walks |
| [Conferences & Community](#conferences--community) | QIP, TQC, QCE, Q2B, Unitary Foundation |
| [Papers & Reading Lists](#papers--reading-lists) | arXiv quant-ph, Quantum journal, surveys & textbooks |

---

## Articles

{% assign categories = "software-libraries,hardware-providers,algorithms-theory,conferences-community,papers-reading" | split: "," %}
{% assign labels = "Software & Libraries,Hardware & Providers,Algorithms & Theory,Conferences & Community,Papers & Reading Lists" | split: "," %}

{% for cat in categories %}
  {% assign idx = forloop.index0 %}
  {% assign label = labels[idx] %}
  {% assign anchor = label | downcase | replace: ' & ', '--' | replace: ' ', '-' %}
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
