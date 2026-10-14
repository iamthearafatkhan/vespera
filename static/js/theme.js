// static/js/theme.js
(function () {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;

  btn.addEventListener("click", () => {
    const isDark = document.documentElement.classList.toggle("dark");
    // remember choice across visits
    localStorage.setItem("theme", isDark ? "dark" : "light");
  });
})();
