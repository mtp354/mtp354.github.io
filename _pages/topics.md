---
title: "Topics"
permalink: /topics/
author_profile: true
---

A weighted index of every topic tag used across the posts, publications,
talks, and resources on this site. Larger text means the tag appears more
often.

{% assign collected = "" | split: "" %}
{% for post in site.posts %}{% for t in post.tags %}{% assign collected = collected | push: t %}{% endfor %}{% endfor %}
{% for pub in site.publications %}{% for t in pub.tags %}{% assign collected = collected | push: t %}{% endfor %}{% endfor %}
{% for talk in site.talks %}{% for t in talk.tags %}{% assign collected = collected | push: t %}{% endfor %}{% endfor %}
{% for r in site.resources %}{% for t in r.tags %}{% assign collected = collected | push: t %}{% endfor %}{% endfor %}

{% assign uniq = collected | uniq | sort %}

<div class="tag-cloud">
{% for tag in uniq %}
  {% assign occurrences = collected | where_exp: "x", "x == tag" %}
  {% assign n = occurrences.size %}
  {% if n >= 6 %}{% assign cls = "tag-cloud__item tag-cloud__item--xl" %}
  {% elsif n >= 4 %}{% assign cls = "tag-cloud__item tag-cloud__item--lg" %}
  {% elsif n >= 2 %}{% assign cls = "tag-cloud__item tag-cloud__item--md" %}
  {% else %}{% assign cls = "tag-cloud__item tag-cloud__item--sm" %}{% endif %}
  <a class="{{ cls }}" href="{{ site.baseurl }}/tags/#{{ tag | slugify }}">{{ tag }}<sup>{{ n }}</sup></a>
{% endfor %}
</div>

<p style="margin-top:2em;"><em>Tip: each tag links to its dedicated archive page.</em></p>
