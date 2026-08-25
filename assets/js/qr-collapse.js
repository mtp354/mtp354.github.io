(function () {
  var report = document.querySelector('[data-qr-report]');
  if (!report) return;

  var headings = Array.prototype.slice.call(report.querySelectorAll(':scope > h2'));
  if (!headings.length) return;

  var controls = document.createElement('div');
  controls.className = 'qr-collapse-controls';

  var expand = document.createElement('button');
  expand.type = 'button';
  expand.textContent = 'Expand all';

  var collapse = document.createElement('button');
  collapse.type = 'button';
  collapse.textContent = 'Collapse all';

  controls.appendChild(expand);
  controls.appendChild(collapse);
  report.insertBefore(controls, headings[0]);

  headings.forEach(function (heading) {
    var details = document.createElement('details');
    details.className = 'qr-section';
    details.open = true;

    var summary = document.createElement('summary');
    summary.className = 'qr-section__summary';
    summary.textContent = heading.textContent;
    summary.id = heading.id;

    var body = document.createElement('div');
    body.className = 'qr-section__body';

    heading.removeAttribute('id');
    heading.parentNode.insertBefore(details, heading);
    details.appendChild(summary);
    details.appendChild(body);

    var next = heading.nextSibling;
    heading.remove();

    while (next) {
      var current = next;
      next = next.nextSibling;

      if (current.nodeType === 1 && current.tagName && current.tagName.toLowerCase() === 'h2') {
        details.parentNode.insertBefore(current, details.nextSibling);
        break;
      }

      body.appendChild(current);
    }
  });

  expand.addEventListener('click', function () {
    report.querySelectorAll('.qr-section').forEach(function (section) {
      section.open = true;
    });
  });

  collapse.addEventListener('click', function () {
    report.querySelectorAll('.qr-section').forEach(function (section) {
      section.open = false;
    });
  });
})();
