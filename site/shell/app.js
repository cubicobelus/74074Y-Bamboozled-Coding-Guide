(function () {
  'use strict';

  var DATA = JSON.parse(document.getElementById('site-data').textContent);
  var SITE = DATA.siteTitle;
  var TERMS = DATA.terms;
  var START = DATA.start;
  var PREVIEW_BLOCKS = 6;
  var STORE_KEY = 'bamboozled-start';

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
  var layout = document.querySelector('.layout');
  var topbar = document.querySelector('.topbar');
  var backButton = document.getElementById('back-button');
  var backCount = document.getElementById('back-count');

  var currentSlug = null;
  var pendingScroll = null;
  var backStack = [];

  function has(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }

  function plainClick(ev) {
    return ev.button === 0 && !ev.ctrlKey && !ev.metaKey && !ev.shiftKey && !ev.altKey;
  }

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
    var page = has(pages, r.slug) ? pages[r.slug] : null;
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
    if (pendingScroll !== null) {
      // Coming back from a jump: restore the exact scroll position.
      window.scrollTo(0, pendingScroll);
      pendingScroll = null;
    } else if (r.heading) {
      var target = document.getElementById(r.heading);
      if (target && lesson.contains(target)) {
        target.scrollIntoView();
        target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    }
  }

  window.addEventListener('hashchange', route);

  // ---- back to where you were ----
  function updateBack() {
    backButton.hidden = backStack.length === 0;
    backCount.textContent = backStack.length > 1 ? ' (' + backStack.length + ')' : '';
  }
  function pushHere() {
    if (currentSlug) { backStack.push({ slug: currentSlug, y: window.scrollY }); }
    updateBack();
  }
  // A jump: remember where we are, then go to href.
  function jumpTo(href) {
    pushHere();
    if (href === location.hash) { route(); } else { location.hash = href; }
  }
  backButton.addEventListener('click', function () {
    var entry = backStack.pop();
    updateBack();
    if (!entry) { return; }
    pendingScroll = entry.y;
    var h = '#/' + entry.slug;
    if (location.hash === h) { route(); } else { location.hash = h; }
  });

  // ---- modal helpers ----
  var modalOpen = null; // 'preview' or 'welcome'
  function setInert(on) {
    [layout, topbar, backButton].forEach(function (el) {
      if (!el) { return; }
      if (on) { el.setAttribute('inert', ''); } else { el.removeAttribute('inert'); }
    });
    document.body.classList.toggle('modal-open', on);
  }
  function trapTab(ev, box) {
    if (ev.key !== 'Tab') { return; }
    var items = Array.prototype.filter.call(
      box.querySelectorAll('button, a[href], [tabindex]:not([tabindex="-1"])'),
      function (el) { return !el.hidden && el.offsetParent !== null; });
    if (!items.length) { return; }
    var first = items[0], last = items[items.length - 1];
    if (ev.shiftKey && (document.activeElement === first || document.activeElement === box)) {
      ev.preventDefault(); last.focus();
    } else if (!ev.shiftKey && document.activeElement === last) {
      ev.preventDefault(); first.focus();
    }
  }

  // ---- vocabulary preview panel ----
  var previewBackdrop = document.getElementById('preview-backdrop');
  var preview = document.getElementById('preview');
  var previewTitle = document.getElementById('preview-title');
  var previewWhere = document.getElementById('preview-where');
  var previewBody = document.getElementById('preview-body');
  var previewGo = document.getElementById('preview-go');
  var previewClose = document.getElementById('preview-close');
  var previewTerm = null;
  var previewOpener = null;

  function showTerm(key) {
    var t = has(TERMS, key) ? TERMS[key] : null;
    if (!t) { return false; }
    previewBody.innerHTML = t.html;
    // Only the first few blocks: the opening lines have to work as a definition.
    var kids = previewBody.children;
    if (kids.length > PREVIEW_BLOCKS) {
      while (previewBody.children.length > PREVIEW_BLOCKS) {
        previewBody.removeChild(previewBody.lastChild);
      }
      var more = document.createElement('p');
      more.className = 'preview-more';
      more.textContent = 'The explanation continues in the lesson.';
      previewBody.appendChild(more);
    }
    previewTitle.textContent = t.term;
    previewWhere.textContent = 'in "' + t.page + '"';
    previewTerm = t;
    previewBody.scrollTop = 0;
    return true;
  }

  function openTerm(key, opener) {
    try {
      if (!showTerm(key)) { return false; }
      if (modalOpen !== 'preview') {
        previewOpener = opener || document.activeElement;
        previewBackdrop.hidden = false;
        modalOpen = 'preview';
        setInert(true);
      }
      preview.focus();
      return true;
    } catch (e) {
      closePreview(false);
      return false;
    }
  }

  function closePreview(restoreFocus) {
    previewBackdrop.hidden = true;
    if (modalOpen === 'preview') { modalOpen = null; }
    setInert(false);
    previewTerm = null;
    if (restoreFocus && previewOpener && document.body.contains(previewOpener)) {
      previewOpener.focus();
    }
    previewOpener = null;
  }

  function jumpFromPreview() {
    if (!previewTerm) { return; }
    var href = '#/' + previewTerm.slug + '/' + encodeURIComponent(previewTerm.id);
    closePreview(false);
    jumpTo(href);
  }

  previewClose.addEventListener('click', function (ev) { ev.stopPropagation(); closePreview(true); });
  previewGo.addEventListener('click', function (ev) { ev.stopPropagation(); jumpFromPreview(); });
  previewBackdrop.addEventListener('click', function (ev) {
    if (ev.target === previewBackdrop) { closePreview(true); }
  });
  preview.addEventListener('click', function (ev) {
    var a = ev.target.closest ? ev.target.closest('a') : null;
    if (a && previewBody.contains(a)) {
      var href = a.getAttribute('href') || '';
      if (href.indexOf('#/') !== 0 || !plainClick(ev)) { return; }
      ev.preventDefault();
      if (a.classList.contains('term') && openTerm(a.getAttribute('data-term'))) { return; }
      closePreview(false);
      jumpTo(href);
      return;
    }
    if (previewBody.contains(ev.target) || ev.target === preview) { jumpFromPreview(); }
  });
  preview.addEventListener('keydown', function (ev) { trapTab(ev, preview); });

  // ---- lesson clicks: copy buttons, terms, lesson links ----
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
    if (btn) {
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
      return;
    }

    var a = ev.target.closest ? ev.target.closest('a') : null;
    if (!a) { return; }
    var href = a.getAttribute('href') || '';
    if (href.indexOf('#/') !== 0 || !plainClick(ev)) { return; }

    if (a.classList.contains('term')) {
      // If anything goes wrong the link is left alone and works as a normal link.
      if (openTerm(a.getAttribute('data-term'), a)) { ev.preventDefault(); }
      return;
    }
    // An ordinary link to another lesson or section is a jump too.
    if (currentSlug) {
      ev.preventDefault();
      jumpTo(href);
    }
  });

  // ---- mobile menu ----
  menuButton.addEventListener('click', function () {
    var open = sidebar.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
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

  // ---- first-visit question ----
  var welcomeBackdrop = document.getElementById('welcome-backdrop');
  var welcome = document.getElementById('welcome');
  var welcomeChoices = document.getElementById('welcome-choices');
  var welcomeSkip = document.getElementById('welcome-skip');
  var changeStart = document.getElementById('change-start');
  var welcomeOpener = null;
  var sessionChoice = null;

  function readChoice() {
    try { return window.localStorage.getItem(STORE_KEY); } catch (e) { return null; }
  }
  function saveChoice(value) {
    sessionChoice = value;
    try { window.localStorage.setItem(STORE_KEY, value); } catch (e) { /* storage blocked: keep going */ }
  }
  function currentChoice() { return readChoice() || sessionChoice; }

  function buildWelcome() {
    var chosen = currentChoice();
    welcomeChoices.textContent = '';
    START.forEach(function (s) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'choice';
      b.setAttribute('aria-pressed', chosen === s.id ? 'true' : 'false');
      var l = document.createElement('span');
      l.className = 'c-label';
      l.textContent = s.label;
      var w = document.createElement('span');
      w.className = 'c-where';
      w.textContent = 'Starts at: ' + s.title;
      b.appendChild(l);
      b.appendChild(w);
      b.addEventListener('click', function () {
        saveChoice(s.id);
        closeWelcome(false);
        var target = '#/' + s.slug;
        if (location.hash === target) { route(); } else { location.hash = target; }
      });
      welcomeChoices.appendChild(b);
    });
    welcomeSkip.textContent = chosen && chosen !== 'skip' ? 'Cancel' : 'Skip for now';
  }

  function openWelcome(opener) {
    buildWelcome();
    welcomeOpener = opener || null;
    welcomeBackdrop.hidden = false;
    modalOpen = 'welcome';
    setInert(true);
    welcome.focus();
  }
  function closeWelcome(restoreFocus) {
    welcomeBackdrop.hidden = true;
    if (modalOpen === 'welcome') { modalOpen = null; }
    setInert(false);
    if (restoreFocus && welcomeOpener && document.body.contains(welcomeOpener)) {
      welcomeOpener.focus();
    }
    welcomeOpener = null;
  }
  function skipWelcome() {
    var chosen = currentChoice();
    if (!chosen) { saveChoice('skip'); }
    closeWelcome(true);
  }
  welcomeSkip.addEventListener('click', skipWelcome);
  welcome.addEventListener('keydown', function (ev) { trapTab(ev, welcome); });
  changeStart.addEventListener('click', function () { openWelcome(changeStart); });

  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') { return; }
    if (modalOpen === 'preview') { closePreview(true); }
    else if (modalOpen === 'welcome') { skipWelcome(); }
  });

  // ---- start ----
  var openedWithoutLesson = parseHash().slug === '';
  route();
  if (openedWithoutLesson && !currentChoice()) { openWelcome(null); }
})();
