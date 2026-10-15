// static/js/theme.js
// Single global handler for every theme toggle on the page.
// Uses event delegation so it works on any page, for any number of toggles,
// without needing per-page scripts.
(function () {
  // read / write theme
  function isDark() { return document.documentElement.classList.contains('dark'); }
  function setDark(v) {
    document.documentElement.classList.toggle('dark', v);
    localStorage.setItem('theme', v ? 'dark' : 'light');
  }

  // one listener for the entire document
  document.addEventListener('click', function (e) {
    // closest() walks up from the click target — so clicking an SVG inside the button still matches
    var btn = e.target.closest('#theme-toggle, [data-theme-toggle]');
    if (!btn) return;
    e.preventDefault();
    setDark(!isDark());
  });

  // cross-tab sync — if you toggle in one tab, other tabs update too
  window.addEventListener('storage', function (e) {
    if (e.key === 'theme') setDark(e.newValue === 'dark');
  });
})();