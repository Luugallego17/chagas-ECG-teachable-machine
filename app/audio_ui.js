// Controles del fonocardiograma. El estilo lo puede cambiar otro trabajo:
// los ganchos son los id audio-*.
(function () {
  "use strict";
  var seccion = document.getElementById("audio");
  if (!seccion || !window.AudioPreproceso || !window.tf) return;

  var $ = function (id) { return document.getElementById(id); };
  var base = new URL(seccion.getAttribute("data-modelo") || "../modelo/audio/", window.location.href);
  var modelo = null;
  var meta = null;

  function estado(texto) {
    $("audio-estado").textContent = texto;
  }

  function mensajeError(motivo, duracion) {
    if (motivo === "corto") {
      var seg = typeof duracion === "number" ? duracion.toFixed(1).replace(".", ",") : "menos de 5";
      return "La señal dura " + seg + " s. Hacen falta 5 segundos completos, así que no se asigna una clase.";
    }
    if (motivo === "silencio") return "La señal está en silencio. No se asigna una clase.";
    return "No se pudo leer el audio. Use un archivo .wav de al menos 5 segundos.";
  }

  function mostrarIncierto(motivo, duracion) {
    var caja = $("audio-error");
    caja.hidden = false;
    caja.textContent = mensajeError(motivo, duracion);
    $("audio-resultado").hidden = false;
    var nombre = meta && meta.etiquetasApp ? meta.etiquetasApp.incierto : "Incierto";
    $("audio-clase").textContent = nombre || "Incierto";
    $("audio-confianza").textContent = "—";
  }

  function limpiarError() {
    var caja = $("audio-error");
    caja.hidden = true;
    caja.textContent = "";
  }

  function mostrarClase(clave, confianza) {
    limpiarError();
    $("audio-resultado").hidden = false;
    var nombre = meta.etiquetasApp && meta.etiquetasApp[clave] ? meta.etiquetasApp[clave] : clave;
    $("audio-clase").textContent = nombre;
    $("audio-confianza").textContent = (confianza * 100).toFixed(1).replace(".", ",") + " %";
    var umbral = typeof meta.umbralConfianzaBaja === "number" ? meta.umbralConfianzaBaja : 0.6;
    estado(confianza < umbral ? "Confianza baja. Léalo con cautela." : "Listo.");
  }

  function cargar() {
    estado("Cargando el modelo de audio…");
    fetch(new URL("metadata.json", base))
      .then(function (r) {
        if (!r.ok) throw new Error("metadata");
        return r.json();
      })
      .then(function (datos) {
        meta = datos;
        return tf.loadLayersModel(new URL("model.json", base).href);
      })
      .then(function (m) {
        modelo = m;
        estado("Modelo de audio listo.");
      })
      .catch(function (err) {
        console.error(err);
        estado("No se pudo cargar el modelo de audio. Sirva el repositorio con un servidor local; el electrocardiograma sigue en esta página.");
      });
  }

  function aMono(buffer) {
    var n = buffer.length;
    var canales = buffer.numberOfChannels;
    var mono = new Float32Array(n);
    for (var c = 0; c < canales; c++) {
      var datos = buffer.getChannelData(c);
      for (var i = 0; i < n; i++) mono[i] += datos[i];
    }
    if (canales > 1) {
      for (var j = 0; j < n; j++) mono[j] /= canales;
    }
    return mono;
  }

  function clasificar(buffer) {
    if (!modelo || !meta) {
      estado("El modelo de audio aún no está listo.");
      return;
    }
    var prep = window.AudioPreproceso.preparar(aMono(buffer), buffer.sampleRate);
    if (!prep.ok) {
      mostrarIncierto(prep.motivo, prep.duracion);
      return;
    }
    var forma = [1, window.AudioPreproceso.N_MELS, window.AudioPreproceso.N_FRAMES, 1];
    var entrada = tf.tensor4d(prep.spec, forma);
    var salida = modelo.predict(entrada);
    salida.data().then(function (probs) {
      entrada.dispose();
      salida.dispose();
      var etiquetas = meta.labels || ["normal", "soplo"];
      var iSoplo = etiquetas.indexOf("soplo");
      var iNormal = etiquetas.indexOf("normal");
      var umbral = typeof meta.umbralSoplo === "number" ? meta.umbralSoplo : 0.5;
      var esSoplo = probs[iSoplo] >= umbral;
      mostrarClase(esSoplo ? "soplo" : "normal", esSoplo ? probs[iSoplo] : probs[iNormal]);
    }).catch(function (err) {
      entrada.dispose();
      console.error(err);
      mostrarIncierto("ilegible");
    });
  }

  function decodificar(blob) {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    var ctx = new Ctx();
    blob.arrayBuffer().then(function (crudo) {
      return ctx.decodeAudioData(crudo);
    }).then(function (audio) {
      clasificar(audio);
    }).catch(function () {
      mostrarIncierto("ilegible");
    }).finally(function () {
      ctx.close();
    });
  }

  $("audio-archivo").addEventListener("change", function (ev) {
    var archivo = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!archivo) return;
    var nombre = (archivo.name || "").toLowerCase();
    var tipo = archivo.type || "";
    if (tipo.indexOf("image/") === 0 || /\.(png|jpe?g|gif|pdf|txt)$/.test(nombre)) {
      mostrarIncierto("ilegible");
      return;
    }
    decodificar(archivo);
  });

  cargar();
})();
