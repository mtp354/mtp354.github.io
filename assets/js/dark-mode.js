// Dark-mode toggle. Persists preference in localStorage and respects
// prefers-color-scheme on first visit. Sets data-theme on <html>.
(function () {
  'use strict';
  var KEY = 'mtp354-theme';
  var root = document.documentElement;

  function apply(theme) {
    root.setAttribute('data-theme', theme);
    var btn = document.getElementById('theme-toggle');
    if (btn) {
      var dark = theme === 'dark';
      btn.setAttribute('aria-pressed', String(dark));
      btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      btn.innerHTML = dark
        ? '<i class="fa fa-sun" aria-hidden="true"></i>'
        : '<i class="fa fa-moon" aria-hidden="true"></i>';
    }
  }

  function initial() {
    var stored = null;
    try { stored = localStorage.getItem(KEY); } catch (e) {}
    if (stored === 'light' || stored === 'dark') return stored;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  }

  apply(initial());

  document.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target.closest('#theme-toggle') : null;
    if (!t) return;
    ev.preventDefault();
    var current = root.getAttribute('data-theme') || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    apply(next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
  });
})();
