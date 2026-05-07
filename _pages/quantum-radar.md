---
title: "Quantum Radar"
permalink: /quantum-radar/
author_profile: true
toc: true
toc_sticky: true
---

**Quantum Radar** is an in-repo automation that scans the quantum computing
landscape on a schedule. It runs as a set of GitHub Actions inside this
website's repository and publishes its output below.

It produces four feeds:

- **Opportunities** — grants, hackathons, summer schools, internships, and
  fellowships, every three days. Curated seed list plus freshly scraped items,
  rendered as tables with deadlines.
- **Publications & news** — quantum publications and news digest, every two
  days.
- **Repo health** — daily checks across my own monitored quantum repos.
- **Quantum 100** — hand-curated list of leading quantum companies and
  people, refreshed manually.

The orchestrator code lives at
[`projects/quantum-radar/`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/projects/quantum-radar)
and the workflows at
[`.github/workflows/quantum-radar-*.yml`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/.github/workflows)
in this same repo.

{% include base_path %}

{% assign report_types = "opportunities,publications-news,repo-health,quantum-100" | split: "," %}
{% assign type_labels = "Opportunities,Publications & news,Repo health,Quantum 100" | split: "," %}

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
