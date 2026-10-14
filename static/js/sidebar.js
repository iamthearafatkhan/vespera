// static/js/sidebar.js
(function () {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!toggle || !sidebar || !backdrop) return;

  function open() {
    sidebar.classList.remove("-translate-x-full");
    backdrop.classList.remove("hidden");
  }
  function close() {
    sidebar.classList.add("-translate-x-full");
    backdrop.classList.add("hidden");
  }

  toggle.addEventListener("click", open);
  backdrop.addEventListener("click", close);
})();
