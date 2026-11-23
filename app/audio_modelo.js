/* Conecta el modelo real de modelo/audio/ al panel de archivo.
   Usa el mismo preproceso y las mismas reglas que la rama de audio:
   5 s, silencio, umbral de soplo y confianza baja. No pide el micrófono. */
(function () {
  "use strict";
  if (!window.AudioPreproceso || !window.tf || !window.ChagasAudio || !document.currentScript) return;

  var api = window.ChagasAudio;
  var base = new URL("../modelo/audio/", document.currentScript.src);
  var modelo = null;
  var meta = null;
  var AVISO = "Resultado orientativo. No es un diagnóstico de Chagas ni sustituye la auscultación de un médico.";

  function etiqueta(clave) {
    if (meta && meta.etiquetasApp && meta.etiquetasApp[clave]) return meta.etiquetasApp[clave];
    return clave;
  }

  function motivoTexto(motivo, duracion) {
    if (motivo === "corto") {
      var seg = typeof duracion === "number" ? duracion.toFixed(1).replace(".", ",") : "menos de 5";
      return "La señal dura " + seg + " s. Hacen falta 5 segundos completos, así que no se asigna una clase.";
    }
    if (motivo === "silencio") return "La señal está en silencio. No se asigna una clase.";
    return "No se pudo leer el audio. Use un archivo .wav de al menos 5 segundos.";
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

  function cargar() {
    api.fijarEstado("Cargando el modelo de audio…");
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
        api.fijarEstado("Modelo de audio listo. Suba un archivo .wav de al menos 5 segundos.");
      })
      .catch(function () {
        api.fijarEstado("No se pudo cargar el modelo de audio. El electrocardiograma sigue disponible.");
      });
  }

  api.clasificarArchivo = function (file) {
    return new Promise(function (resolve, reject) {
      if (!modelo || !meta) {
        reject(new Error("El modelo de audio aún no está listo."));
        return;
      }
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) {
        reject(new Error("Este visor no puede leer el audio."));
        return;
      }
      var ctx = new Ctx();
      file.arrayBuffer().then(function (crudo) {
        return ctx.decodeAudioData(crudo.slice(0));
      }).then(function (buffer) {
        var prep = window.AudioPreproceso.preparar(aMono(buffer), buffer.sampleRate);
        if (!prep.ok) {
          var texto = motivoTexto(prep.motivo, prep.duracion);
          api.mostrarResultado(etiqueta("incierto"), null, texto + " " + AVISO);
          api.fijarEstado(texto);
          return;
        }
        var forma = [1, window.AudioPreproceso.N_MELS, window.AudioPreproceso.N_FRAMES, 1];
        var entrada = tf.tensor4d(prep.spec, forma);
        var salida = modelo.predict(entrada);
        return salida.data().then(function (probs) {
          entrada.dispose();
          salida.dispose();
          var etiquetas = meta.labels || ["normal", "soplo"];
          var iSoplo = etiquetas.indexOf("soplo");
          var iNormal = etiquetas.indexOf("normal");
          var umbral = typeof meta.umbralSoplo === "number" ? meta.umbralSoplo : 0.5;
          var esSoplo = probs[iSoplo] >= umbral;
          var clave = esSoplo ? "soplo" : "normal";
          var confianza = esSoplo ? probs[iSoplo] : probs[iNormal];
          var baja = typeof meta.umbralConfianzaBaja === "number" ? meta.umbralConfianzaBaja : 0.6;
          var nota = AVISO;
          if (confianza < baja) nota = "Confianza baja. Léalo con cautela. " + nota;
          api.mostrarResultado(etiqueta(clave), confianza, nota);
          if (confianza < baja) api.fijarEstado("Confianza baja. Léalo con cautela.");
        });
      }).catch(function () {
        api.mostrarResultado(etiqueta("incierto"), null, motivoTexto("ilegible") + " " + AVISO);
        api.fijarEstado(motivoTexto("ilegible"));
      }).then(function () {
        if (ctx.close) ctx.close();
        resolve();
      }, function (err) {
        if (ctx.close) ctx.close();
        reject(err instanceof Error ? err : new Error("No se pudo analizar ese archivo."));
      });
    });
  };

  cargar();
})();
