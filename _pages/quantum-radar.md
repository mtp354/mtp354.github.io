---
title: "Quantum Radar"
permalink: /quantum-radar/
author_profile: true
---

**Quantum Radar** is a small in-repo automation that I use to keep tabs on
the quantum computing world while I work on other things. It runs as a set
of GitHub Actions inside this website's repository and quietly publishes
fresh pages here for me to skim later. I share it openly in case any of it
is useful to you too.

Here is what it currently tracks:

- **Opportunities** — grants with an identifiable open call/application, plus
  internships, summer schools, hackathons, fellowships, and a collapsible jobs
  section sourced from approved public job feeds. Grant award news is excluded.
  Refreshed every three days, with job listings refreshed daily once configured.
- **Conferences** — upcoming quantum-adjacent academic conferences plus quantum
  industry conferences and summits. Refreshed every three days.
- **Publications & news** — a quantum publications and news digest, every
  two days.
- **Movers & Shakers** — a hand-curated list of leading quantum companies,
  influential university labs, and people doing notable work in the field.
- **Quantum Industry** — publicly listed quantum companies, broad quantum ETFs,
  catalogued grant awards with captured values, and directional investment/workforce
  estimates refreshed with the daily market snapshot.

The orchestrator code lives at
[`projects/quantum-radar/`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/projects/quantum-radar)
and the workflows at
[`.github/workflows/quantum-radar-*.yml`]({{ site.repository | prepend: 'https://github.com/' }}/tree/main/.github/workflows)
in this same repo.

{% include base_path %}

{% assign report_types = "opportunities,conferences,publications-news,movers-shakers,quantum-industry" | split: "," %}
{% assign type_labels = "Opportunities,Conferences,Publications & news,Movers & Shakers,Quantum Industry" | split: "," %}

{% for rt in report_types %}
  {% assign idx = forloop.index0 %}
  {% assign label = type_labels[idx] %}
  {% assign entries = site.quantum_radar | where: "report_type", rt %}
  {% if rt == "quantum-industry" %}
    {% assign legacy_entries = site.quantum_radar | where: "report_type", "publicly-traded" %}
    {% assign entries = entries | concat: legacy_entries %}
  {% endif %}
  {% assign entries = entries | sort: "date" | reverse %}

  <h2 id="{{ rt }}">{{ label }}</h2>

  {% if entries.size == 0 %}
  _No entries yet._
  {% else %}
  {% assign latest = entries | first %}
  {% assign latest_title = latest.title %}
  {% if rt == "quantum-industry" and latest.report_type == "publicly-traded" %}
    {% assign latest_title = latest_title | replace: "Publicly Traded Quantum", "Quantum Industry" %}
  {% endif %}

  **Latest:** [{{ latest_title }}]({{ latest.url | relative_url }}) &mdash; {{ latest.date | date: "%B %-d, %Y" }}

  {% if entries.size > 1 %}
  <details>
    <summary>Archive ({{ entries.size }} entries)</summary>
    <ul>
    {% for e in entries %}
      {% assign entry_title = e.title %}
      {% if rt == "quantum-industry" and e.report_type == "publicly-traded" %}
        {% assign entry_title = entry_title | replace: "Publicly Traded Quantum", "Quantum Industry" %}
      {% endif %}
      <li>
        <a href="{{ e.url | relative_url }}">{{ e.date | date: "%Y-%m-%d" }}</a> &mdash; {{ entry_title }}
      </li>
    {% endfor %}
    </ul>
  </details>
  {% endif %}
  {% endif %}

{% endfor %}
