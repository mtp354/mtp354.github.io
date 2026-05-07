---
title: "Quantum Radar"
permalink: /quantum-radar/
author_profile: true
toc: true
toc_sticky: true
---

**Quantum Radar** is a small in-repo automation that I use to keep tabs on
the quantum computing world while I work on other things. It runs as a set
of GitHub Actions inside this website's repository and quietly publishes
fresh pages here for me to skim later. I share it openly in case any of it
is useful to you too.

Here is what it currently tracks:

- **Opportunities** — a curated list of grants, internships, summer schools,
  hackathons, and fellowships I am watching, with deadlines pulled from each
  program's page where possible. Refreshed every three days.
- **Publications & news** — a quantum publications and news digest, every
  two days.
- **Movers & Shakers** — a hand-curated list of leading quantum companies,
  influential university labs, and people doing notable work in the field.
- **Publicly Traded Quantum** — primary publicly listed quantum companies
  and a couple of broad quantum ETFs, with stock prices refreshed daily.

The orchestrator code lives at
[`projects/quantum-radar/`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/projects/quantum-radar)
and the workflows at
[`.github/workflows/quantum-radar-*.yml`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/.github/workflows)
in this same repo.

{% include base_path %}

{% assign report_types = "opportunities,publications-news,movers-shakers,publicly-traded" | split: "," %}
{% assign type_labels = "Opportunities,Publications & news,Movers & Shakers,Publicly Traded Quantum" | split: "," %}

{% for rt in report_types %}
  {% assign idx = forloop.index0 %}
  {% assign label = type_labels[idx] %}
  {% assign entries = site.quantum_radar | where: "report_type", rt | sort: "date" | reverse %}

  <h2 id="{{ rt }}">{{ label }}</h2>

  {% if entries.size == 0 %}
  _No entries yet._
  {% else %}
  {% assign latest = entries | first %}

  **Latest:** [{{ latest.title }}]({{ latest.url | relative_url }}) &mdash; {{ latest.date | date: "%B %-d, %Y" }}

  {% if entries.size > 1 %}
  <details>
    <summary>Archive ({{ entries.size }} entries)</summary>
    <ul>
    {% for e in entries %}
      <li>
        <a href="{{ e.url | relative_url }}">{{ e.date | date: "%Y-%m-%d" }}</a> &mdash; {{ e.title }}
      </li>
    {% endfor %}
    </ul>
  </details>
  {% endif %}
  {% endif %}

{% endfor %}
