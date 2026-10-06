(function () {
  'use strict';

  var DATA = JSON.parse(document.getElementById('site-data').textContent);
  var SITE = DATA.siteTitle;
  var pages = {};
  var ordered = [];
  DATA.sections.forEach(function (s) {
    s.pages.forEach(function (p) {
      p.sectionTitle = s.title;
      pages[p.slug] = p;
      ordered.push(p);
    });
  });

  var nav = document.getElementById('nav');
  var lesson = document.getElementById('lesson');
  var content = document.getElementById('content');
  var tocWrap = document.getElementById('toc-wrap');
  var tocList = document.getElementById('toc');
  var sidebar = document.getElementById('sidebar');
  var menuButton = document.getElementById('menu-button');
  var searchInput = document.getElementById('search-input');
  var resultsList = document.getElementById('search-results');

  var currentSlug = null;

  // ---- sidebar ----
  var navLinks = {};
  var navSections = {};
  DATA.sections.forEach(function (s) {
    var details = document.createElement('details');
    var summary = document.createElement('summary');
    summary.textContent = s.title;
    details.appendChild(summary);
    var ul = document.createElement('ul');
    s.pages.forEach(function (p) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#/' + p.slug;
      a.textContent = p.title;
      navLinks[p.slug] = a;
      li.appendChild(a);
      ul.appendChild(li);
    });
    details.appendChild(ul);
    nav.appendChild(details);
    navSections[s.slug] = details;
  });

  // ---- routing ----
  function parseHash() {
    var h = location.hash;
    if (h.indexOf('#/') !== 0) { return { slug: '', heading: '' }; }
    var parts = h.slice(2).split('/');
    var slug = '', heading = '';
    try {
      slug = decodeURIComponent(parts[0] || '');
      heading = decodeURIComponent(parts.slice(1).join('/'));
    } catch (e) { /* malformed escape: treat as unknown */ slug = parts[0] || ''; }
    return { slug: slug, heading: heading };
  }

  function showNotFound(slug) {
    currentSlug = null;
    document.title = 'Page not found | ' + SITE;
    lesson.textContent = '';
    var box = document.createElement('div');
    box.className = 'notfound';
    var h = document.createElement('h1');
    h.textContent = 'We could not find that page';
    var p = document.createElement('p');
    p.textContent = slug
      ? 'There is no lesson called "' + slug + '". The link may be old or mistyped.'
      : 'That link does not point to a lesson.';
    var back = document.createElement('a');
    back.href = '#/' + ordered[0].slug;
    back.textContent = 'Go to the first lesson';
    var p2 = document.createElement('p');
    p2.appendChild(back);
    p2.appendChild(document.createTextNode(', or pick a lesson from the menu.'));
    box.appendChild(h);
    box.appendChild(p);
    box.appendChild(p2);
    lesson.appendChild(box);
    tocWrap.hidden = true;
    setActiveNav(null);
    window.scrollTo(0, 0);
  }

  function setActiveNav(slug) {
    Object.keys(navLinks).forEach(function (k) {
      if (k === slug) { navLinks[k].setAttribute('aria-current', 'page'); }
      else { navLinks[k].removeAttribute('aria-current'); }
    });
    if (slug) {
      navSections[pages[slug].section].open = true;
    }
  }

  function buildToc(page) {
    tocList.textContent = '';
    if (!page.toc.length) { tocWrap.hidden = true; return; }
    page.toc.forEach(function (t) {
      var li = document.createElement('li');
      li.className = 'l' + t.level;
      var a = document.createElement('a');
      a.href = '#/' + page.slug + '/' + encodeURIComponent(t.id);
      a.textContent = t.text;
      li.appendChild(a);
      tocList.appendChild(li);
    });
    tocWrap.hidden = false;
  }

  function route() {
    var r = parseHash();
    if (r.slug === '') {
      // No lesson in the link: open the first one and make the address match.
      history.replaceState(null, '', '#/' + ordered[0].slug);
      r = { slug: ordered[0].slug, heading: '' };
    }
    var page = Object.prototype.hasOwnProperty.call(pages, r.slug) ? pages[r.slug] : null;
    if (!page) { showNotFound(r.slug); return; }

    if (page.slug !== currentSlug) {
      currentSlug = page.slug;
      lesson.innerHTML = page.html;
      document.title = page.title + ' | ' + SITE;
      buildToc(page);
      setActiveNav(page.slug);
      sidebar.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
      window.scrollTo(0, 0);
      content.focus({ preventScroll: true });
    }
    if (r.heading) {
      var target = document.getElementById(r.heading);
      if (target && lesson.contains(target)) { target.scrollIntoView(); }
    }
  }

  window.addEventListener('hashchange', route);

  // ---- mobile menu ----
  menuButton.addEventListener('click', function () {
    var open = sidebar.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // ---- copy buttons ----
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
    }
    return legacyCopy(text);
  }
  function legacyCopy(text) {
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      if (ok) { resolve(); } else { reject(new Error('copy failed')); }
    });
  }
  lesson.addEventListener('click', function (ev) {
    var btn = ev.target.closest ? ev.target.closest('.copy') : null;
    if (!btn) { return; }
    var code = btn.parentNode.querySelector('pre code');
    var original = btn.getAttribute('data-label') || btn.textContent;
    btn.setAttribute('data-label', original);
    copyText(code ? code.textContent : '').then(function () {
      btn.textContent = 'Copied';
    }, function () {
      btn.textContent = 'Press Ctrl+C';
      var sel = window.getSelection();
      var range = document.createRange();
      range.selectNodeContents(code);
      sel.removeAllRanges();
      sel.addRange(range);
    }).then(function () {
      setTimeout(function () { btn.textContent = original; }, 1800);
    });
  });

  // ---- search ----
  var mini = new MiniSearch({
    fields: ['title', 'text'],
    storeFields: ['title'],
    idField: 'slug',
    searchOptions: { prefix: true, fuzzy: 0.2, boost: { title: 3 } }
  });
  mini.addAll(ordered.map(function (p) {
    return { slug: p.slug, title: p.title, text: p.text };
  }));

  function snippet(page, query) {
    var text = page.text;
    var words = query.toLowerCase().split(/\s+/).filter(Boolean);
    var lower = text.toLowerCase();
    var at = -1;
    for (var i = 0; i < words.length && at < 0; i++) { at = lower.indexOf(words[i]); }
    if (at < 0) { return text.slice(0, 90); }
    var start = Math.max(0, at - 40);
    return (start > 0 ? '...' : '') + text.slice(start, at + 70) + '...';
  }

  function renderResults(query) {
    resultsList.textContent = '';
    var hits = mini.search(query).slice(0, 12);
    if (!hits.length) {
      var none = document.createElement('li');
      none.className = 'none';
      none.textContent = 'No lessons match "' + query + '".';
      resultsList.appendChild(none);
      return;
    }
    hits.forEach(function (h) {
      var p = pages[h.id];
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#/' + p.slug;
      var t = document.createElement('div');
      t.className = 'r-title';
      t.textContent = p.title;
      var w = document.createElement('div');
      w.className = 'r-where';
      w.textContent = p.sectionTitle;
      var s = document.createElement('div');
      s.className = 'r-snippet';
      s.textContent = snippet(p, query);
      a.appendChild(t);
      a.appendChild(w);
      a.appendChild(s);
      li.appendChild(a);
      resultsList.appendChild(li);
    });
  }

  function clearSearch() {
    searchInput.value = '';
    resultsList.hidden = true;
    resultsList.textContent = '';
    nav.hidden = false;
  }

  searchInput.addEventListener('input', function () {
    var q = searchInput.value.trim();
    if (q.length < 2) {
      resultsList.hidden = true;
      nav.hidden = false;
      return;
    }
    nav.hidden = true;
    resultsList.hidden = false;
    renderResults(q);
  });
  searchInput.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') { clearSearch(); }
    if (ev.key === 'Enter') {
      var first = resultsList.querySelector('a');
      if (first) { location.hash = first.getAttribute('href'); clearSearch(); }
    }
  });
  resultsList.addEventListener('click', function () {
    // The hash change opens the lesson; close the result list afterwards.
    setTimeout(clearSearch, 0);
  });

  route();
})();
