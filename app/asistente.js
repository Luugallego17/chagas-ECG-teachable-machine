/* Asistente con el modelo de Teachable Machine incorporado en la página.
   La imagen no se envía a ningún servidor. */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var anio = document.getElementById("year");
  if (anio) anio.textContent = "© " + new Date().getFullYear();
  var hora = new Date().getHours();
  var saludo = document.getElementById("saludo");
  if (saludo) saludo.textContent = hora < 12 ? "Buenos días" : (hora < 19 ? "Buenas tardes" : "Buenas noches");
  var fecha = document.getElementById("fecha");
  if (fecha) fecha.textContent = new Date().toLocaleDateString("es-BO", { day: "2-digit", month: "2-digit", year: "numeric" });

  function cvar(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#8f1d33";
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  var META = {
    "ECG NORMAL": { css: "--c-norm", kind: "normal", ab: "Normal", full: "ECG normal", desc: "Ritmo sinusal sin alteraciones de la conducción.", msg: "En esta imagen no se ve un patrón de bloqueo de los que estudia el modelo." },
    "BRD": { css: "--c-brd", kind: "rbbb", ab: "BRD", full: "Bloqueo de rama derecha", desc: "QRS ancho con segunda R tardía. Hallazgo frecuente en la cardiopatía chagásica.", msg: "El trazado se parece al bloqueo de rama derecha. Hay que correlacionarlo con la clínica." },
    "HBAI": { css: "--c-hbai", kind: "lafb", ab: "HBAI", full: "Hemibloqueo anterior izquierdo", desc: "Eje del QRS desviado a la izquierda. Muy frecuente en Chagas, casi siempre junto al BRD.", msg: "El trazado se parece al hemibloqueo anterior izquierdo. Hay que correlacionarlo con la clínica." },
    "BRD + HBAI": { css: "--c-brdhbai", kind: "rbbb_lafb", ab: "BRD + HBAI", full: "Bloqueo bifascicular", desc: "Combinación de ambos bloqueos: patrón chagásico clásico, de alta sugestividad.", msg: "El trazado se parece al bloqueo bifascicular, el patrón clásico que se estudia en Chagas." },
    "Bloqueo AV": { css: "--c-av", kind: "av_block", ab: "BAV", full: "Bloqueo aurículo-ventricular", desc: "Retraso o interrupción entre aurículas y ventrículos. Marca la progresión de la enfermedad.", msg: "El trazado se parece a un bloqueo aurículo-ventricular. Hay que correlacionarlo con la clínica." },
    "Extrasistole ventricular": { css: "--c-pvc", kind: "pvc", ab: "EV", full: "Extrasístole ventricular", desc: "Latido prematuro de origen ventricular, con QRS ancho y pausa posterior.", msg: "El trazado se parece a una extrasístole ventricular. Hay que correlacionarlo con la clínica." }
  };
  var NORMAL = "ECG NORMAL";
  var BAJA = 0.70;
  function metaOf(l) { return META[l] || { css: "--accent", kind: "normal", ab: l, full: l, desc: "", msg: "El modelo asignó esta etiqueta." }; }

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
  function trace(ctx, W, H, kind, color, lw) {
    var fs = 250, T = 2.8, rr = kind === "av_block" ? 1 : .8, mid = H * .62, gain = H * .46, sx = W / T, first = true;
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineJoin = "round"; ctx.beginPath();
    function pt(tt, v) {
      var X = tt * sx, Y = mid - v * gain;
      if (first) { ctx.moveTo(X, Y); first = false; } else ctx.lineTo(X, Y);
    }
    if (kind === "pvc") {
      var seq = ["N", "N", "V"], pos = .05;
      for (var s = 0; s < seq.length; s++) {
        var isV = seq[s] === "V";
        for (var i = 0; i < .8 * fs; i++) {
          var tt = i / fs;
          var vv = isV ? (gauss(tt, .33, .05, -1.1) + gauss(tt, .46, .07, .55)) : beat(tt, "normal");
          pt(pos + tt, vv);
        }
        pos += isV ? rr * 1.4 : rr;
      }
    } else {
      for (var p = .05; p < T; p += rr) {
        for (var j = 0; j < .8 * fs; j++) {
          var tj = j / fs;
          if (p + tj > T) break;
          pt(p + tj, beat(tj, kind));
        }
      }
    }
    ctx.stroke();
  }
  function paper(ctx, W, H, minC, majC) {
    ctx.lineWidth = 1;
    for (var x = 0; x < W; x += 8) {
      ctx.strokeStyle = (x % 40 === 0) ? majC : minC;
      ctx.beginPath(); ctx.moveTo(x + .5, 0); ctx.lineTo(x + .5, H); ctx.stroke();
    }
    for (var y = 0; y < H; y += 8) {
      ctx.strokeStyle = (y % 40 === 0) ? majC : minC;
      ctx.beginPath(); ctx.moveTo(0, y + .5); ctx.lineTo(W, y + .5); ctx.stroke();
    }
  }
  function drawExample(cv, kind) {
    var ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
    paper(ctx, W, H, "rgba(201,74,60,.16)", "rgba(201,74,60,.30)");
    trace(ctx, W, H, kind, "#15110f", 1.6);
  }

  function paintAtlas() {
    document.querySelectorAll("#agrid canvas").forEach(function (cv) {
      var ctx = cv.getContext("2d");
      ctx.clearRect(0, 0, cv.width, cv.height);
      paper(ctx, cv.width, cv.height, cvar("--line"), cvar("--line-fuerte"));
      trace(ctx, cv.width, cv.height, cv.getAttribute("data-kind"), cvar(cv.getAttribute("data-css")), 2.4);
    });
  }
  (function () {
    var g = document.getElementById("agrid");
    if (!g) return;
    Object.keys(META).forEach(function (l) {
      var m = META[l];
      var d = document.createElement("article");
      d.className = "acard";
      d.innerHTML = '<canvas width="360" height="112" data-kind="' + m.kind + '" data-css="' + m.css + '" role="img" aria-label="Trazado de ejemplo: ' + esc(m.full) + '"></canvas>' +
        '<div class="ab">' + esc(m.ab) + '</div><div class="fn">' + esc(m.full) + '</div><div class="d">' + esc(m.desc) + '</div>';
      g.appendChild(d);
    });
    paintAtlas();
  })();
  document.addEventListener("chagas-tema", paintAtlas);

  (function () {
    var row = document.getElementById("exrow");
    if (!row) return;
    Object.keys(META).forEach(function (l) {
      var m = META[l];
      var b = document.createElement("button");
      b.className = "ex";
      b.type = "button";
      b.setAttribute("aria-label", "Usar el ejemplo de " + m.full);
      var cv = document.createElement("canvas");
      cv.width = 150; cv.height = 36; cv.setAttribute("aria-hidden", "true");
      drawExample(cv, m.kind);
      var lab = document.createElement("span");
      lab.className = "lab";
      lab.textContent = m.ab;
      b.appendChild(cv); b.appendChild(lab);
      b.addEventListener("click", function () {
        Array.prototype.forEach.call(row.querySelectorAll(".ex"), function (el) { el.classList.remove("activo"); });
        b.classList.add("activo");
        var grande = document.createElement("canvas");
        grande.width = 520; grande.height = 180;
        drawExample(grande, m.kind);
        if (window.ChagasImagen) {
          ChagasImagen.ponerCanvas(grande, { nombre: "Ejemplo sintético · " + m.full, origen: "ejemplo", ejemplo: l });
        }
      });
      row.appendChild(b);
    });
  })();

  (function () {
    var cv = document.getElementById("pen");
    if (!cv) return;
    var ctx = cv.getContext("2d"), box = cv.parentElement, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W = 0, H = 0, buf = [], phase = 0, off = 0, glow = 0, armed = true, SP = 2, PENX = 0, col = {};
    function colors() {
      col = { min: "rgba(143,29,51,.12)", maj: "rgba(143,29,51,.28)", pen: cvar("--ink"), acc: "#8f1d33" };
      if (document.documentElement.getAttribute("data-theme") === "dark" ||
          (!document.documentElement.getAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches)) {
        col.min = "rgba(255,179,192,.12)"; col.maj = "rgba(255,179,192,.28)"; col.acc = "#ffb3c0";
      }
    }
    function b2(t) { return gauss(t, .15, .02, .1) + gauss(t, .31, .012, -.1) + gauss(t, .34, .012, 1) + gauss(t, .37, .012, -.22) + gauss(t, .56, .045, .26); }
    function resize() {
      W = box.clientWidth || 320; H = box.clientHeight || 64;
      cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      PENX = W - 24; var n = Math.max(40, PENX - 48); colors();
      buf = []; for (var i = 0; i < n; i++) buf.push(sample()); glow = 0;
    }
    function sample() {
      phase += .0058; if (phase >= 1) phase -= 1;
      var v = b2(phase);
      if (v > .6 && armed) { glow = 1; armed = false; }
      if (v < .2) armed = true;
      return H * .62 - v * H * .5;
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.lineWidth = 1;
      for (var x = -off % 40; x < W; x += 8) {
        var isMaj = (Math.round((x + off) / 8) % 5 === 0);
        ctx.strokeStyle = isMaj ? col.maj : col.min;
        ctx.beginPath(); ctx.moveTo(Math.round(x) + .5, 0); ctx.lineTo(Math.round(x) + .5, H); ctx.stroke();
      }
      for (var y = 0; y < H; y += 8) {
        ctx.strokeStyle = (y % 40 === 0) ? col.maj : col.min;
        ctx.beginPath(); ctx.moveTo(0, y + .5); ctx.lineTo(W, y + .5); ctx.stroke();
      }
      var base = H * .62, top = base - H * .42;
      ctx.strokeStyle = col.pen; ctx.lineWidth = 1.6; ctx.beginPath();
      ctx.moveTo(8, base); ctx.lineTo(14, base); ctx.lineTo(14, top); ctx.lineTo(32, top); ctx.lineTo(32, base); ctx.lineTo(38, base); ctx.stroke();
      var x0 = PENX - buf.length;
      ctx.strokeStyle = col.pen; ctx.lineWidth = 1.7; ctx.lineJoin = "round"; ctx.beginPath();
      for (var i = 0; i < buf.length; i++) { if (i === 0) ctx.moveTo(x0 + i, buf[i]); else ctx.lineTo(x0 + i, buf[i]); }
      ctx.stroke();
      var py = buf[buf.length - 1];
      ctx.fillStyle = col.acc; ctx.beginPath(); ctx.arc(PENX, py, 3, 0, 6.2832); ctx.fill();
      glow *= .9;
    }
    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("chagas-tema", function () { colors(); });
    if (reduce) { draw(); }
    else {
      (function loop() {
        for (var s = 0; s < SP; s++) { buf.push(sample()); buf.shift(); off = (off + 1) % 40; }
        draw();
        requestAnimationFrame(loop);
      })();
    }
  })();

  var model = null;
  function setStatus(cls, txt) {
    var s = document.getElementById("status");
    if (!s) return;
    s.className = "led" + (cls ? " " + cls : "");
    s.innerHTML = "<i></i><span>" + esc(txt) + "</span>";
  }
  function b64ToBytes(b64) {
    var bin = atob(b64.trim()), n = bin.length, u = new Uint8Array(n);
    for (var i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
    return u;
  }
  function loadModel() {
    if (typeof tmImage === "undefined") {
      setStatus("err", "No se pudo cargar la librería. Revise la conexión.");
      return;
    }
    try {
      var mj = document.getElementById("model-json").textContent;
      var md = document.getElementById("metadata-json").textContent;
      var b64 = document.getElementById("weights-b64").textContent;
      var mf = new File([mj], "model.json", { type: "application/json" });
      var mdf = new File([md], "metadata.json", { type: "application/json" });
      var wf = new File([b64ToBytes(b64)], "weights.bin", { type: "application/octet-stream" });
      tmImage.loadFromFiles(mf, wf, mdf).then(function (m) {
        model = m;
        setStatus("ok", "Modelo listo · " + m.getTotalClasses() + " patrones");
      }).catch(function () {
        setStatus("err", "No se pudo cargar el modelo incorporado");
      });
    } catch (e) {
      setStatus("err", "No se pudo preparar el modelo incorporado");
    }
  }

  function pct(x) { return (x * 100).toFixed(1).replace(".", ","); }
  var esperaInicial = "Todavía no hay una lectura. Elija una imagen, ajústela si hace falta y pulse Analizar.";

  function mostrarEspera(texto) {
    var w = document.getElementById("waiting");
    var r = document.getElementById("report");
    if (w) { w.hidden = false; w.textContent = texto || esperaInicial; }
    if (r) r.hidden = true;
  }
  function render(items, info) {
    var top = items[0], m = metaOf(top.label), color = cvar(m.css);
    var w = document.getElementById("waiting");
    var r = document.getElementById("report");
    if (w) w.hidden = true;
    if (r) r.hidden = false;
    var rk = document.getElementById("rk");
    if (rk) rk.textContent = "Lectura · " + new Date().toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit" });
    var vn = document.getElementById("vname");
    vn.textContent = m.full;
    vn.style.color = color;
    document.getElementById("vmsg").textContent = m.msg;
    var aclaracion = "";
    if (info && info.ejemplo && META[info.ejemplo] && info.ejemplo !== top.label) {
      aclaracion = " Este dibujo es solo un ejemplo de " + META[info.ejemplo].full + ". El modelo se entrenó con otras imágenes y aquí muestra lo que realmente responde.";
    }
    document.getElementById("vdesc").textContent = m.desc + aclaracion;
    document.getElementById("cn").textContent = pct(top.prob);
    var ln = document.getElementById("lownote");
    if (ln) ln.hidden = !(top.prob < BAJA);
    var rows = document.getElementById("orows");
    rows.innerHTML = "";
    items.forEach(function (it, idx) {
      var mm = metaOf(it.label);
      var col = cvar(mm.css);
      var valor = Math.round(it.prob * 1000) / 10;
      var bloque = document.createElement("div");
      bloque.className = "barra" + (idx === 0 ? " principal" : "");
      bloque.innerHTML = '<span class="nombre">' + esc(mm.full) + '</span>' +
        '<span class="pct">' + pct(it.prob) + ' %</span>' +
        '<span class="riel" role="meter" aria-label="' + esc(mm.full) + '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + valor + '"><span class="relleno" style="--c:' + col + '"></span></span>';
      rows.appendChild(bloque);
      var fill = bloque.querySelector(".relleno");
      if (reduce) fill.style.width = (it.prob * 100) + "%";
      else requestAnimationFrame(function () { fill.style.width = (it.prob * 100) + "%"; });
    });
    if (window.matchMedia("(max-width: 799px)").matches && r && !reduce) {
      r.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function classify(input, info) {
    return new Promise(function (resolve, reject) {
      if (!model) {
        reject(new Error("El modelo todavía se está preparando. Espere a que diga «Modelo listo» y pulse Analizar otra vez."));
        return;
      }
      model.predict(input).then(function (preds) {
        var items = preds.map(function (p) { return { label: p.className, prob: p.probability }; })
          .sort(function (a, b) { return b.prob - a.prob; });
        render(items, info);
        resolve(items);
      }).catch(function () {
        reject(new Error("No se pudo analizar esta imagen. Pruebe a rotarla o a repetir la toma con más luz."));
      });
    });
  }

  window.ChagasImagen = window.ChagasImagen || {};
  window.ChagasImagen.alAnalizar = function (canvas, info) { return classify(canvas, info); };

  document.addEventListener("chagas-imagen-limpia", function () { mostrarEspera(esperaInicial); });
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
    var otro = actual === "ecg" ? "audio" : "ecg";
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

  if (window.tf && window.tmImage) loadModel();
  else window.addEventListener("load", loadModel);
})();
