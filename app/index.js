/* Versión genérica: el modelo de Teachable Machine lo carga quien usa la página.
   Todo sigue ocurriendo en el navegador. */
(function () {
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var anio = document.getElementById("year");
  if (anio) anio.textContent = "© " + new Date().getFullYear();

  function cvar(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#8f1d33"; }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }
  function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, ""); }

  var CLASES = [
    { key: "normal", label: "Normal", css: "--c-norm", desc: "Ritmo sinusal sin alteraciones de conducción." },
    { key: "rbbb", label: "BRD", css: "--c-brd", desc: "Bloqueo completo de rama derecha. Hallazgo frecuente en Chagas." },
    { key: "lafb", label: "HBAI", css: "--c-hbai", desc: "Hemibloqueo anterior izquierdo. Muy frecuente en Chagas." },
    { key: "rbbb_lafb", label: "BRD + HBAI", css: "--c-brdhbai", desc: "Patrón chagásico clásico, de alta especificidad." },
    { key: "av_block", label: "Bloqueo AV", css: "--c-av", desc: "Bloqueo aurículo-ventricular. Marcador de progresión." },
    { key: "pvc", label: "Extrasístole ventricular", css: "--c-pvc", desc: "Arritmia ventricular; riesgo de muerte súbita." }
  ];
  var MAPA = {
    normal: "--c-norm", rbbb: "--c-brd", lafb: "--c-hbai", rbbb_lafb: "--c-brdhbai", brd_hbai: "--c-brdhbai",
    av_block: "--c-av", bloqueo_av: "--c-av", pvc: "--c-pvc", extrasistole_ventricular: "--c-pvc", brd: "--c-brd", hbai: "--c-hbai"
  };
  function colorFor(key) { return cvar(MAPA[key] || "--c-brd"); }
  function labelFor(key, raw) {
    var c = CLASES.filter(function (x) { return x.key === key; })[0];
    return c ? c.label : raw;
  }
  function descFor(key) {
    var c = CLASES.filter(function (x) { return x.key === key; })[0];
    return c ? c.desc : "";
  }

  (function () {
    var g = document.getElementById("classgrid");
    if (!g) return;
    CLASES.forEach(function (c) {
      var d = document.createElement("article");
      d.className = "clase";
      d.innerHTML = '<i style="background:var(' + c.css + ')"></i><div><div class="fn">' + esc(c.label) + '</div><p class="detalle">' + esc(c.desc) + '</p></div>';
      g.appendChild(d);
    });
  })();

  function gauss(t, c, w, a) { return a * Math.exp(-((t - c) * (t - c)) / (2 * w * w)); }
  function beat(t, kind) {
    var v = gauss(t, .15, .02, .12);
    if (kind === "rbbb" || kind === "rbbb_lafb") {
      v += gauss(t, .35, .012, .85) + gauss(t, .385, .01, -.3) + gauss(t, .435, .016, .55);
      if (kind === "rbbb_lafb") v += gauss(t, .325, .008, -.2);
    } else {
      var q = kind === "av_block" ? .46 : .34;
      v += gauss(t, q - .03, .012, -.1) + gauss(t, q, .012, 1) + gauss(t, q + .03, .012, -.22);
      if (kind === "lafb") v += gauss(t, .322, .008, -.18);
    }
    v += gauss(t, (kind === "av_block" ? .7 : .58), .045, .28);
    return v;
  }
  function drawECG(cv, kind) {
    var ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(198,47,68,.16)"; ctx.lineWidth = 1;
    for (var x = 0; x < W; x += 6) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (var y = 0; y < H; y += 6) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.strokeStyle = "#111"; ctx.lineWidth = 1.4; ctx.beginPath();
    var mid = H * .58, gain = H * .34, fs = 250, rr = (kind === "av_block" ? 1 : .8), sx = W / 4.8, pos = .12, first = true;
    if (kind === "pvc") {
      var seq = ["N", "N", "V", "N", "N"];
      for (var s = 0; s < seq.length; s++) {
        var isV = seq[s] === "V";
        for (var i = 0; i < .8 * fs; i++) {
          var tt = i / fs;
          var vv = isV ? (gauss(tt, .33, .05, -1.1) + gauss(tt, .46, .07, .55)) : beat(tt, "normal");
          var X = (pos + tt) * sx, Y = mid - vv * gain;
          if (first) { ctx.moveTo(X, Y); first = false; } else ctx.lineTo(X, Y);
        }
        pos += isV ? rr * 1.4 : rr;
      }
    } else {
      for (var p = .12; p < 4.6; p += rr) {
        for (var j = 0; j < .8 * fs; j++) {
          var tj = j / fs, vj = beat(tj, kind), Xx = (p + tj) * sx, Yy = mid - vj * gain;
          if (first) { ctx.moveTo(Xx, Yy); first = false; } else ctx.lineTo(Xx, Yy);
        }
      }
    }
    ctx.stroke();
  }

  (function () {
    var row = document.getElementById("exrow");
    if (!row) return;
    CLASES.forEach(function (ex) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "ex";
      b.setAttribute("aria-label", "Usar el ejemplo de " + ex.label);
      var cv = document.createElement("canvas");
      cv.width = 150; cv.height = 42; cv.setAttribute("aria-hidden", "true");
      drawECG(cv, ex.key);
      var lab = document.createElement("span");
      lab.className = "lab"; lab.textContent = ex.label;
      b.appendChild(cv); b.appendChild(lab);
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(row.querySelectorAll(".ex"), function (el) { el.classList.remove("activo"); });
        b.classList.add("activo");
        var grande = document.createElement("canvas");
        grande.width = 520; grande.height = 180;
        drawECG(grande, ex.key);
        if (window.ChagasImagen) {
          ChagasImagen.ponerCanvas(grande, { nombre: "Ejemplo sintético · " + ex.label, origen: "ejemplo", ejemplo: ex.key });
        }
      });
      row.appendChild(b);
    });
  })();

  var model = null;
  var files = { model: null, weights: null, meta: null };
  function wire(id, key, nameId) {
    document.getElementById(id).addEventListener("change", function (e) {
      files[key] = e.target.files[0] || null;
      document.getElementById(nameId).textContent = files[key] ? files[key].name : { model: "model.json", weights: "weights.bin", meta: "metadata.json" }[key];
      document.getElementById("load").disabled = !(files.model && files.weights && files.meta);
    });
  }
  wire("f-model", "model", "n-model");
  wire("f-weights", "weights", "n-weights");
  wire("f-meta", "meta", "n-meta");

  function setChip(cls, txt) {
    var c = document.getElementById("mchip");
    c.className = "led" + (cls ? " " + cls : "");
    c.innerHTML = "<i></i><span>" + esc(txt) + "</span>";
  }
  document.getElementById("load").addEventListener("click", function () {
    if (typeof tmImage === "undefined") { setChip("err", "No se pudo cargar la librería"); return; }
    setChip("ocupado", "Cargando el modelo…");
    document.getElementById("load").disabled = true;
    tmImage.loadFromFiles(files.model, files.weights, files.meta).then(function (m) {
      model = m;
      setChip("ok", "Modelo activo · " + m.getTotalClasses() + " clases");
      document.getElementById("clearModel").hidden = false;
    }).catch(function () {
      setChip("err", "No se pudo cargar. Revise los tres archivos.");
      document.getElementById("load").disabled = false;
    });
  });
  document.getElementById("clearModel").addEventListener("click", function () {
    model = null;
    setChip("", "Sin modelo");
    document.getElementById("clearModel").hidden = true;
    document.getElementById("load").disabled = !(files.model && files.weights && files.meta);
  });

  function pct(x) { return (x * 100).toFixed(1).replace(".", ","); }
  function mostrarEspera(texto) {
    document.getElementById("waiting").hidden = false;
    document.getElementById("waiting").textContent = texto;
    document.getElementById("report").hidden = true;
  }
  function render(items, fuente) {
    document.getElementById("waiting").hidden = true;
    document.getElementById("report").hidden = false;
    var top = items[0];
    document.getElementById("rk").textContent = fuente === "modelo" ? "Predicción del modelo" : "Etiqueta del ejemplo";
    var vn = document.getElementById("vname");
    vn.textContent = top.label;
    vn.style.color = top.color;
    document.getElementById("vmsg").textContent = fuente === "modelo"
      ? "Clase más probable según el modelo cargado. Correlacione el resultado con la clínica."
      : "Sin modelo cargado se muestra la etiqueta conocida de este ejemplo sintético.";
    document.getElementById("vdesc").textContent = descFor(top.key);
    document.getElementById("cn").textContent = fuente === "modelo" ? pct(top.prob) : "100,0";
    var rows = document.getElementById("orows");
    rows.innerHTML = "";
    items.forEach(function (it, idx) {
      var valor = Math.round(it.prob * 1000) / 10;
      var bloque = document.createElement("div");
      bloque.className = "barra" + (idx === 0 ? " principal" : "");
      bloque.innerHTML = '<span class="nombre">' + esc(it.label) + '</span><span class="pct">' + pct(it.prob) + ' %</span>' +
        '<span class="riel" role="meter" aria-label="' + esc(it.label) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + valor + '"><span class="relleno" style="--c:' + it.color + '"></span></span>';
      rows.appendChild(bloque);
      var fill = bloque.querySelector(".relleno");
      if (reduce) fill.style.width = (it.prob * 100) + "%";
      else requestAnimationFrame(function () { fill.style.width = (it.prob * 100) + "%"; });
    });
  }

  function classify(input, ejemplo) {
    return new Promise(function (resolve, reject) {
      if (model) {
        model.predict(input).then(function (preds) {
          var items = preds.map(function (p, i) {
            var k = slug(p.className);
            return { key: k, label: labelFor(k, p.className), prob: p.probability, color: colorFor(k) };
          }).sort(function (a, b) { return b.prob - a.prob; });
          render(items, "modelo");
          resolve(items);
        }).catch(function () {
          reject(new Error("No se pudo analizar esta imagen con el modelo cargado."));
        });
        return;
      }
      if (ejemplo) {
        var i = 0;
        CLASES.forEach(function (c, n) { if (c.key === ejemplo) i = n; });
        render([{ key: ejemplo, label: labelFor(ejemplo), prob: 1, color: colorFor(ejemplo) }], "ejemplo");
        resolve();
        return;
      }
      reject(new Error("Imagen lista. Cargue arriba los tres archivos del modelo para clasificarla. Los ejemplos sí muestran su etiqueta sin modelo."));
    });
  }

  window.ChagasImagen = window.ChagasImagen || {};
  window.ChagasImagen.alAnalizar = function (canvas, info) {
    return classify(canvas, info && info.ejemplo);
  };
  document.addEventListener("chagas-imagen-limpia", function () {
    mostrarEspera("Todavía no hay una lectura. Elija una imagen o un ejemplo.");
  });
  document.addEventListener("chagas-imagen-lista", function () {
    mostrarEspera("Imagen lista. Puede rotarla o recortarla y después pulsar Analizar.");
  });

  var tabEcg = document.getElementById("tab-ecg");
  var tabAudio = document.getElementById("tab-audio");
  function seleccionar(cual, enfocar) {
    var ecg = cual === "ecg";
    tabEcg.setAttribute("aria-selected", ecg ? "true" : "false");
    tabAudio.setAttribute("aria-selected", ecg ? "false" : "true");
    tabEcg.tabIndex = ecg ? 0 : -1;
    tabAudio.tabIndex = ecg ? -1 : 0;
    document.getElementById("panel-ecg").hidden = !ecg;
    document.getElementById("panel-audio").hidden = ecg;
    if (enfocar) (ecg ? tabEcg : tabAudio).focus();
  }
  function alTecla(e, actual) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft" && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    var otro = e.key === "ArrowRight" || e.key === "End" ? (actual === "ecg" ? "audio" : "ecg") : (actual === "audio" ? "ecg" : "audio");
    if (e.key === "Home") otro = "ecg";
    if (e.key === "End") otro = "audio";
    if (e.key === "ArrowRight") otro = actual === "ecg" ? "audio" : "ecg";
    if (e.key === "ArrowLeft") otro = actual === "audio" ? "ecg" : "audio";
    seleccionar(otro, true);
  }
  tabEcg.addEventListener("click", function () { seleccionar("ecg", false); });
  tabAudio.addEventListener("click", function () { seleccionar("audio", false); });
  tabEcg.addEventListener("keydown", function (e) { alTecla(e, "ecg"); });
  tabAudio.addEventListener("keydown", function (e) { alTecla(e, "audio"); });
})();
