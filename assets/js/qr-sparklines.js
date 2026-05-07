// Sparkline renderer for Quantum Radar publicly-traded reports.
// Reads JSON from <script type="application/json" id="qr-spark-data"> and
// draws inline SVG sparklines into elements with data-spark="TICKER".
(function () {
  'use strict';
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function spark(values, opts) {
    opts = opts || {};
    var w = opts.width || 110;
    var h = opts.height || 28;
    var pad = 2;
    if (!values || values.length < 2) return '';
    var min = Math.min.apply(null, values);
    var max = Math.max.apply(null, values);
    var range = max - min || 1;
    var step = (w - pad * 2) / (values.length - 1);
    var pts = values.map(function (v, i) {
      var x = pad + i * step;
      var y = h - pad - ((v - min) / range) * (h - pad * 2);
      return x.toFixed(1) + ',' + y.toFixed(1);
    });
    var up = values[values.length - 1] >= values[0];
    var color = up ? '#1a8a3a' : '#b8252f';
    return '<svg class="qr-spark" viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '" aria-hidden="true">' +
      '<polyline fill="none" stroke="' + color + '" stroke-width="1.4" points="' + pts.join(' ') + '" />' +
      '</svg>';
  }

  ready(function () {
    var node = document.getElementById('qr-spark-data');
    if (!node) return;
    var data;
    try { data = JSON.parse(node.textContent); } catch (e) { return; }
    if (!data || typeof data !== 'object') return;
    Object.keys(data).forEach(function (ticker) {
      var targets = document.querySelectorAll('[data-spark="' + ticker + '"]');
      if (!targets.length) return;
      var svg = spark(data[ticker]);
      for (var i = 0; i < targets.length; i++) targets[i].innerHTML = svg;
    });
  });
})();
