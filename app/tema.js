/* Tema claro u oscuro. Si no hay una elección guardada, sigue al sistema. */
(function () {
  "use strict";
  var btn = document.getElementById("theme");
  if (!btn) return;

  function oscuro() {
    var cur = document.documentElement.getAttribute("data-theme");
    if (cur) return cur === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function pintar() {
    var d = oscuro();
    btn.setAttribute("aria-pressed", d ? "true" : "false");
    btn.textContent = d ? "Tema claro" : "Tema oscuro";
  }

  btn.addEventListener("click", function () {
    var next = oscuro() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("ecg-tema", next); } catch (e) {}
    pintar();
    document.dispatchEvent(new CustomEvent("chagas-tema"));
  });

  pintar();
  if (window.matchMedia("(prefers-color-scheme: dark)").addEventListener) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      var guardado = null;
      try { guardado = localStorage.getItem("ecg-tema"); } catch (e) {}
      if (!guardado) {
        document.documentElement.removeAttribute("data-theme");
        pintar();
        document.dispatchEvent(new CustomEvent("chagas-tema"));
      }
    });
  }
})();
