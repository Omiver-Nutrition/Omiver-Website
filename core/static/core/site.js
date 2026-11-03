(function () {
  var doc = document.documentElement;

  // Header hairline once the page has scrolled.
  var header = document.querySelector('[data-header]');
  if (header) {
    var onScroll = function () { header.classList.toggle('is-scrolled', window.scrollY > 4); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // Mobile navigation.
  var toggle = document.querySelector('[data-nav-toggle]');
  var nav = document.querySelector('[data-nav]');
  if (toggle && nav) {
    var setOpen = function (open) {
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    toggle.addEventListener('click', function () { setOpen(!nav.classList.contains('is-open')); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) { setOpen(false); toggle.focus(); }
    });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  }

  // Section reveal: content stays visible unless the browser can animate it in.
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduce && 'IntersectionObserver' in window) {
    var targets = document.querySelectorAll('[data-reveal]');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('is-in'); io.unobserve(entry.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.top < window.innerHeight) return; // already on screen: never hide it
      el.dataset.revealArmed = '';
      io.observe(el);
    });
    doc.classList.add('reveal-ready');
    targets.forEach(function (el) { if (!('revealArmed' in el.dataset)) el.classList.add('is-in'); });
  }

  // Contact form: clear on success, fade the status message after a while.
  document.body.addEventListener('htmx:afterSwap', function (e) {
    var status = e.detail.target;
    if (!status || !status.classList.contains('form-status')) return;
    var form = document.getElementById(status.dataset.form);
    var response = status.querySelector('.form-response');
    if (response && response.classList.contains('success') && form) form.reset();
    if (response) {
      setTimeout(function () {
        response.style.opacity = 0;
        setTimeout(function () { status.innerHTML = ''; }, 300);
      }, 6000);
    }
  });
})();
