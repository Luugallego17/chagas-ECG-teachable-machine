/* Sonido cardíaco: solo archivo, sin micrófono.
   No se llama a getUserMedia ni se pide permiso de grabación.
   Cuando exista modelo/audio/, la integración asigna:
     ChagasAudio.clasificarArchivo = function (file) { ... }  // devuelve una promesa si es async
     ChagasAudio.mostrarResultado(etiqueta, probabilidad, nota)
     ChagasAudio.mostrarError(mensaje)
     ChagasAudio.fijarEstado(texto)
   El aviso #audio-aviso (no diagnostica Chagas) no se quita.
   Sin modelo, Analizar no inventa una clasificación. */
(function () {
  "use strict";
  var entrada = document.getElementById("audio-archivo");
  var estado = document.getElementById("audio-estado");
  var caja = document.getElementById("audio-resultado");
  var ficha = document.getElementById("audio-ficha");
  var nombre = document.getElementById("audio-nombre");
  var duracion = document.getElementById("audio-duracion");
  var alerta = document.getElementById("audio-alerta");
  var analizar = document.getElementById("audio-analizar");
  if (!entrada || !analizar) return;

  var actual = null;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function fijarEstado(texto) {
    if (estado) estado.textContent = texto;
  }

  function mostrarAlerta(mensaje) {
    if (!alerta) return;
    if (!mensaje) { alerta.hidden = true; alerta.textContent = ""; return; }
    alerta.hidden = false;
    alerta.textContent = mensaje;
  }

  function mostrarError(mensaje) {
    mostrarAlerta(mensaje);
    fijarEstado(mensaje);
    if (caja) { caja.hidden = true; caja.innerHTML = ""; }
  }

  function mostrarResultado(etiqueta, probabilidad, nota) {
    if (!caja) return;
    mostrarAlerta("");
    var pct = typeof probabilidad === "number" ? (probabilidad * 100).toFixed(1).replace(".", ",") + " %" : "";
    caja.hidden = false;
    caja.innerHTML = '<p class="kicker">Lectura de sonido</p>' +
      '<p class="nombre">' + esc(etiqueta) + '</p>' +
      (pct ? '<p class="confianza"><span class="numero">' + esc(pct) + '</span></p>' : "") +
      (nota ? '<p>' + esc(nota) + '</p>' : "");
    fijarEstado("Lectura lista. Revise el aviso: esto no diagnostica Chagas.");
  }

  function formato(seg) {
    if (seg == null || !isFinite(seg) || seg <= 0) return "No se pudo leer";
    if (seg >= 60) {
      var total = Math.round(seg);
      var m = Math.floor(total / 60);
      var s = total % 60;
      return m + ":" + (s < 10 ? "0" : "") + s;
    }
    return seg.toFixed(1).replace(".", ",") + " s";
  }

  function esAudio(file) {
    var tipo = file.type || "";
    if (tipo.indexOf("audio/") === 0) return true;
    return /\.wav$/i.test(file.name || "");
  }

  function leerDuracion(file) {
    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file);
      var audio = document.createElement("audio");
      var listo = false;
      function fin(valor) {
        if (listo) return;
        listo = true;
        URL.revokeObjectURL(url);
        resolve(valor);
      }
      audio.preload = "metadata";
      audio.onloadedmetadata = function () {
        if (isFinite(audio.duration) && audio.duration > 0) fin(audio.duration);
        else fin(null);
      };
      audio.onerror = function () { fin(null); };
      audio.src = url;
      setTimeout(function () { fin(null); }, 4000);
    }).then(function (seg) {
      if (seg) return seg;
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC || !file.arrayBuffer) return null;
      return file.arrayBuffer().then(function (buf) {
        var ctx = new AC();
        return new Promise(function (resolve) {
          ctx.decodeAudioData(buf.slice(0), function (audioBuf) {
            if (ctx.close) ctx.close();
            resolve(audioBuf.duration);
          }, function () {
            if (ctx.close) ctx.close();
            resolve(null);
          });
        });
      }).catch(function () { return null; });
    });
  }

  function recibir(file) {
    if (!file) return;
    if (caja) { caja.hidden = true; caja.innerHTML = ""; }
    if (!esAudio(file)) {
      actual = null;
      if (ficha) ficha.hidden = true;
      if (analizar) analizar.disabled = true;
      mostrarError("Ese archivo no es un audio WAV. Elija un archivo .wav.");
      return;
    }
    actual = file;
    mostrarAlerta("");
    if (nombre) nombre.textContent = file.name;
    if (duracion) duracion.textContent = "Leyendo…";
    if (ficha) ficha.hidden = false;
    if (analizar) analizar.disabled = false;
    fijarEstado("Archivo listo. Revise el nombre y la duración y pulse Analizar.");
    leerDuracion(file).then(function (seg) {
      if (actual !== file) return;
      if (duracion) duracion.textContent = formato(seg);
    });
  }

  var api = window.ChagasAudio || {};
  api.fijarEstado = fijarEstado;
  api.mostrarError = mostrarError;
  api.mostrarResultado = mostrarResultado;
  api.archivoActual = function () { return actual; };
  window.ChagasAudio = api;

  entrada.addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (file) recibir(file);
  });

  analizar.addEventListener("click", function () {
    if (!actual) return;
    if (caja) { caja.hidden = true; caja.innerHTML = ""; }
    if (typeof api.clasificarArchivo !== "function") {
      fijarEstado("Archivo listo (" + actual.name + "). El modelo de audio todavía no está conectado, así que no hay clasificación.");
      return;
    }
    analizar.disabled = true;
    analizar.setAttribute("aria-busy", "true");
    fijarEstado("Analizando el sonido…");
    Promise.resolve(api.clasificarArchivo(actual)).then(function () {
      analizar.disabled = !actual;
      analizar.removeAttribute("aria-busy");
    }, function (err) {
      mostrarError((err && err.message) || "No se pudo analizar ese archivo.");
      analizar.disabled = !actual;
      analizar.removeAttribute("aria-busy");
    });
  });
})();
