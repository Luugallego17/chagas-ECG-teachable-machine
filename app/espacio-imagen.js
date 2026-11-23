/* Vista previa de la imagen del ECG: rotación y recorte.
   La cámara (camara.js) y la galería (galeria.js) entregan la imagen por
   ChagasImagen.ponerCanvas o ChagasImagen.ponerArchivo.
   La página clasifica en ChagasImagen.alAnalizar(canvas). */
(function () {
  "use strict";
  var previo = window.ChagasImagen || {};
  var trabajo = null;
  var infoActual = { nombre: "", ejemplo: null, origen: "" };
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(id) { return document.getElementById(id); }

  function mostrarAlerta(msg) {
    var el = $("alerta-imagen");
    if (!el) return;
    if (!msg) { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false;
    el.textContent = msg;
  }

  function marcarPaso(n) {
    var items = document.querySelectorAll("#pasos li");
    Array.prototype.forEach.call(items, function (li, i) {
      li.classList.toggle("activo", i === n);
      li.classList.toggle("hecho", i < n);
    });
  }

  function habilitar(hay) {
    ["btn-rotar", "btn-recortar", "btn-descartar", "btn-analizar"].forEach(function (id) {
      var b = $(id);
      if (b) b.disabled = !hay;
    });
    var herr = $("herramientas");
    var barra = $("barra-accion");
    if (herr) herr.hidden = !hay;
    if (barra) barra.hidden = !hay;
  }

  function pintarPreview() {
    var p = $("preview");
    if (!p) return;
    p.innerHTML = "";
    if (!trabajo) {
      p.innerHTML = '<div class="vacio" id="vacio-preview">' +
        '<svg viewBox="0 0 78 30" fill="none" aria-hidden="true"><path d="M2 20h10V8h8v12h12l3-4 4 9 3-14 3 9h16" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>' +
        '<p>Todavía no hay una imagen.</p></div>';
      if ($("fileinfo")) $("fileinfo").textContent = "";
      habilitar(false);
      marcarPaso(0);
      return;
    }
    var view = document.createElement("canvas");
    view.width = trabajo.width;
    view.height = trabajo.height;
    view.getContext("2d").drawImage(trabajo, 0, 0);
    view.setAttribute("role", "img");
    view.setAttribute("aria-label", "Vista previa del electrocardiograma");
    p.appendChild(view);
    if ($("fileinfo")) {
      $("fileinfo").textContent = (infoActual.nombre || "Imagen") + " · " + trabajo.width + " × " + trabajo.height + " px";
    }
    habilitar(true);
    marcarPaso(1);
  }

  function aplicarCanvas(canvas, info) {
    trabajo = canvas;
    infoActual = {
      nombre: (info && info.nombre) || "Imagen",
      ejemplo: info && info.ejemplo ? info.ejemplo : null,
      origen: (info && info.origen) || "archivo"
    };
    window.ChagasImagen.info = infoActual;
    mostrarAlerta("");
    var est = $("estado-analisis");
    if (est) est.hidden = true;
    pintarPreview();
    document.dispatchEvent(new CustomEvent("chagas-imagen-lista", { detail: infoActual }));
  }

  function rasterizarArchivo(file) {
    if (window.createImageBitmap) {
      return createImageBitmap(file, { imageOrientation: "from-image" }).then(function (bmp) {
        var c = document.createElement("canvas");
        c.width = bmp.width;
        c.height = bmp.height;
        c.getContext("2d").drawImage(bmp, 0, 0);
        if (bmp.close) bmp.close();
        return c;
      });
    }
    return new Promise(function (resolve, reject) {
      var img = new Image();
      var url = URL.createObjectURL(file);
      img.onload = function () {
        var c = document.createElement("canvas");
        c.width = img.naturalWidth;
        c.height = img.naturalHeight;
        c.getContext("2d").drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        resolve(c);
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("lectura")); };
      img.src = url;
    });
  }

  function ponerArchivo(file, info) {
    info = info || {};
    if (!file) return Promise.resolve();
    var tipo = file.type || "";
    if (tipo && tipo.indexOf("image/") !== 0) {
      mostrarAlerta("Ese archivo no es una imagen. Elija un archivo JPG o PNG.");
      return Promise.resolve();
    }
    if (!tipo && file.name && !/\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(file.name)) {
      mostrarAlerta("Ese archivo no parece una imagen. Elija un archivo JPG o PNG.");
      return Promise.resolve();
    }
    return rasterizarArchivo(file).then(function (canvas) {
      if (!canvas.width || !canvas.height) throw new Error("vacia");
      aplicarCanvas(canvas, {
        nombre: info.nombre || file.name || "Imagen",
        origen: info.origen || "archivo",
        ejemplo: null
      });
    }).catch(function () {
      mostrarAlerta("No se pudo leer la imagen. Compruebe que sea un archivo JPG o PNG y vuelva a intentarlo.");
    });
  }

  function ponerCanvas(canvas, info) {
    if (!canvas || !canvas.width) {
      mostrarAlerta("La imagen capturada está vacía. Repita la toma.");
      return;
    }
    var copia = document.createElement("canvas");
    copia.width = canvas.width;
    copia.height = canvas.height;
    copia.getContext("2d").drawImage(canvas, 0, 0);
    aplicarCanvas(copia, info || { nombre: "Imagen", origen: "camara" });
  }

  function rotar() {
    if (!trabajo) return;
    var c = document.createElement("canvas");
    c.width = trabajo.height;
    c.height = trabajo.width;
    var ctx = c.getContext("2d");
    ctx.translate(c.width, 0);
    ctx.rotate(Math.PI / 2);
    ctx.drawImage(trabajo, 0, 0);
    trabajo = c;
    pintarPreview();
  }

  function limpiar() {
    trabajo = null;
    infoActual = { nombre: "", ejemplo: null, origen: "" };
    window.ChagasImagen.info = infoActual;
    mostrarAlerta("");
    var est = $("estado-analisis");
    if (est) est.hidden = true;
    pintarPreview();
    document.querySelectorAll(".ex.activo").forEach(function (el) { el.classList.remove("activo"); });
    document.dispatchEvent(new CustomEvent("chagas-imagen-limpia"));
  }

  function analizar() {
    if (!trabajo || !window.ChagasImagen.alAnalizar) return;
    var btn = $("btn-analizar");
    var est = $("estado-analisis");
    if (btn) { btn.disabled = true; btn.setAttribute("aria-busy", "true"); }
    if (est) est.hidden = false;
    mostrarAlerta("");
    var hecho = false;
    function fin() {
      if (hecho) return;
      hecho = true;
      if (btn) { btn.disabled = !trabajo; btn.removeAttribute("aria-busy"); }
      if (est) est.hidden = true;
    }
    try {
      Promise.resolve(window.ChagasImagen.alAnalizar(trabajo, infoActual)).then(function () {
        marcarPaso(2);
        fin();
      }, function (err) {
        mostrarAlerta((err && err.message) || "No se pudo analizar la imagen. Pruebe con otra toma, más nítida.");
        fin();
      });
    } catch (e) {
      mostrarAlerta("No se pudo analizar la imagen. Pruebe con otra toma, más nítida.");
      fin();
    }
  }

  var recorte = { abierto: false };
  function cerrarRecorte() {
    var dlg = $("crop-dialog");
    if (dlg) dlg.hidden = true;
    document.body.classList.remove("sin-scroll");
    recorte.abierto = false;
    if (recorte.previo && recorte.previo.focus) recorte.previo.focus();
  }

  function abrirRecorte() {
    if (!trabajo) return;
    var dlg = $("crop-dialog");
    var stage = $("crop-stage");
    var base = $("crop-base");
    var box = $("crop-box");
    if (!dlg || !stage || !base || !box) return;
    recorte.previo = document.activeElement;
    dlg.hidden = false;
    document.body.classList.add("sin-scroll");
    recorte.abierto = true;
    var panel = dlg.querySelector(".crop-panel");
    var maxW = Math.min((panel ? panel.clientWidth : 320) - 8, 640);
    var maxH = Math.min(window.innerHeight * 0.52, 520);
    var scale = Math.min(maxW / trabajo.width, maxH / trabajo.height);
    var dw = Math.max(1, Math.round(trabajo.width * scale));
    var dh = Math.max(1, Math.round(trabajo.height * scale));
    base.width = trabajo.width;
    base.height = trabajo.height;
    base.style.width = dw + "px";
    base.style.height = dh + "px";
    base.getContext("2d").drawImage(trabajo, 0, 0);
    var st = { x: dw * 0.08, y: dh * 0.08, w: dw * 0.84, h: dh * 0.84 };
    function paint() {
      box.style.left = st.x + "px";
      box.style.top = st.y + "px";
      box.style.width = st.w + "px";
      box.style.height = st.h + "px";
    }
    paint();
    var drag = null;
    function punto(e) {
      var r = base.getBoundingClientRect();
      return {
        x: (e.clientX - r.left) * (dw / r.width),
        y: (e.clientY - r.top) * (dh / r.height)
      };
    }
    box.onpointerdown = function (e) {
      var h = e.target.getAttribute && e.target.getAttribute("data-h");
      var p = punto(e);
      drag = { h: h, x: p.x, y: p.y, st: { x: st.x, y: st.y, w: st.w, h: st.h } };
      if (box.setPointerCapture) box.setPointerCapture(e.pointerId);
      e.preventDefault();
    };
    box.onpointermove = function (e) {
      if (!drag) return;
      var p = punto(e);
      var dx = p.x - drag.x;
      var dy = p.y - drag.y;
      var n = { x: drag.st.x, y: drag.st.y, w: drag.st.w, h: drag.st.h };
      var min = Math.min(48, dw, dh);
      if (!drag.h) {
        n.x = drag.st.x + dx;
        n.y = drag.st.y + dy;
      } else {
        if (drag.h.indexOf("w") >= 0) { n.x = drag.st.x + dx; n.w = drag.st.w - dx; }
        if (drag.h.indexOf("e") >= 0) n.w = drag.st.w + dx;
        if (drag.h.indexOf("n") >= 0) { n.y = drag.st.y + dy; n.h = drag.st.h - dy; }
        if (drag.h.indexOf("s") >= 0) n.h = drag.st.h + dy;
      }
      if (n.w < min) { if (drag.h && drag.h.indexOf("w") >= 0) n.x = n.x + n.w - min; n.w = min; }
      if (n.h < min) { if (drag.h && drag.h.indexOf("n") >= 0) n.y = n.y + n.h - min; n.h = min; }
      if (n.x < 0) { n.w += n.x; n.x = 0; }
      if (n.y < 0) { n.h += n.y; n.y = 0; }
      if (n.x + n.w > dw) n.w = dw - n.x;
      if (n.y + n.h > dh) n.h = dh - n.y;
      if (n.w < min) n.w = min;
      if (n.h < min) n.h = min;
      st.x = n.x; st.y = n.y; st.w = Math.min(n.w, dw - n.x); st.h = Math.min(n.h, dh - n.y);
      paint();
    };
    box.onpointerup = box.onpointercancel = function () { drag = null; };
    $("crop-aplicar").onclick = function () {
      var sx = st.x / dw * trabajo.width;
      var sy = st.y / dh * trabajo.height;
      var sw = st.w / dw * trabajo.width;
      var sh = st.h / dh * trabajo.height;
      var out = document.createElement("canvas");
      out.width = Math.max(1, Math.round(sw));
      out.height = Math.max(1, Math.round(sh));
      out.getContext("2d").drawImage(trabajo, sx, sy, sw, sh, 0, 0, out.width, out.height);
      trabajo = out;
      cerrarRecorte();
      pintarPreview();
    };
    $("crop-cancelar").onclick = cerrarRecorte;
    $("crop-cancelar").focus();
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && recorte.abierto) cerrarRecorte();
  });

  var bRotar = $("btn-rotar");
  var bRec = $("btn-recortar");
  var bDes = $("btn-descartar");
  var bAn = $("btn-analizar");
  if (bRotar) bRotar.addEventListener("click", rotar);
  if (bRec) bRec.addEventListener("click", abrirRecorte);
  if (bDes) bDes.addEventListener("click", limpiar);
  if (bAn) bAn.addEventListener("click", analizar);

  window.ChagasImagen = {
    alAnalizar: previo.alAnalizar || null,
    info: infoActual,
    ponerArchivo: ponerArchivo,
    ponerCanvas: ponerCanvas,
    mostrarAlerta: mostrarAlerta,
    limpiar: limpiar,
    marcarPaso: marcarPaso,
    obtener: function () { return trabajo; }
  };
  habilitar(false);
})();
