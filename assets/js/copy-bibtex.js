// Cite-button toggle and copy-BibTeX-to-clipboard helper.
// Vanilla JS, no deps.
(function () {
  'use strict';

  function toggleBlock(btn) {
    var id = btn.getAttribute('aria-controls');
    if (!id) return;
    var block = document.getElementById(id);
    if (!block) return;
    var open = block.hasAttribute('hidden') === false;
    if (open) {
      block.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
    } else {
      block.removeAttribute('hidden');
      btn.setAttribute('aria-expanded', 'true');
    }
  }

  function copyText(text, btn) {
    var done = function () {
      var orig = btn.innerHTML;
      btn.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i> Copied';
      btn.disabled = true;
      setTimeout(function () {
        btn.innerHTML = orig;
        btn.disabled = false;
      }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {
        // fallback below
        legacyCopy(text, done);
      });
    } else {
      legacyCopy(text, done);
    }
  }

  function legacyCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'absolute';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    document.body.removeChild(ta);
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target.closest ? ev.target.closest('[data-cite-toggle]') : null;
    if (t) { ev.preventDefault(); toggleBlock(t); return; }
    var c = ev.target.closest ? ev.target.closest('[data-cite-copy]') : null;
    if (c) {
      ev.preventDefault();
      var block = c.closest('.cite-block');
      var pre = block ? block.querySelector('[data-cite-text]') : null;
      if (pre) copyText(pre.textContent.trim(), c);
    }
  });
})();
