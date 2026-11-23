/* Foto del ECG en vivo.
   Usa getUserMedia con la cámara trasera (facingMode: environment).
   Pensado para un WebView de Android: playsinline, sin audio, y un
   respaldo con input capture si el visor no deja abrir la cámara.
   La foto entra al mismo flujo de vista previa que un archivo.
   No se guarda en el repositorio ni se envía a un servidor. */
(function () {
  "use strict";
  var slot = document.getElementById("slot-camara");
  if (!slot || !window.ChagasImagen) return;

  var estilo = document.createElement("style");
  estilo.textContent = [
    ".camara{position:fixed;inset:0;z-index:40;background:#0e1114;color:#f4efe9;display:flex;flex-direction:column;",
    "padding:12px 12px calc(12px + env(safe-area-inset-bottom))}",
    "#camara-video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000}",
    ".camara-guia{position:absolute;left:8%;right:8%;top:10%;bottom:168px;border:2px solid rgba(255,255,255,.85);border-radius:12px;",
    "box-shadow:0 0 0 999px rgba(0,0,0,.35);pointer-events:none;display:flex;align-items:flex-end;justify-content:center;padding:12px}",
    ".camara-guia p{margin:0;text-align:center;font-size:.92rem;text-shadow:0 1px 2px #000}",
    ".camara-error{position:relative;z-index:2;margin:auto 8px;padding:16px;border-radius:14px;background:#1c2128;border:1px solid #3a414c}",
    ".camara-controles{margin-top:auto;position:relative;z-index:2;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:12px}",
    ".camara-controles .btn{width:auto;min-width:48px;min-height:48px;background:transparent;color:#fff;border-color:rgba(255,255,255,.7)}",
    "#camara-disparo{width:74px;height:74px;min-height:74px;border-radius:50%;border:4px solid #fff;background:#8f1d33;color:#fff;font-size:0;justify-self:center}",
    "#camara-disparo::after{content:'';width:52px;height:52px;border-radius:50%;background:#fff;display:block}",
    ".camara-respaldo{position:relative;z-index:2;display:flex;justify-content:center;margin-top:8px}",
    ".camara-respaldo .btn{width:auto;background:#fffcf9;color:#1c1917}"
  ].join("");
  document.head.appendChild(estilo);

  slot.innerHTML = '<button type="button" class="btn btn-secundario" id="btn-camara">Tomar foto</button>';

  var dlg = document.createElement("div");
  dlg.id = "camara-dialogo";
  dlg.className = "camara";
  dlg.hidden = true;
  dlg.setAttribute("role", "dialog");
  dlg.setAttribute("aria-modal", "true");
  dlg.setAttribute("aria-labelledby", "camara-titulo");
  dlg.innerHTML =
    '<h2 id="camara-titulo" class="solo-sr">Cámara del electrocardiograma</h2>' +
    '<video id="camara-video" autoplay muted playsinline webkit-playsinline></video>' +
    '<div class="camara-guia" id="camara-guia" aria-hidden="true"><p>Encuadre el trazado dentro del marco. Evite sombras y reflejos. La imagen no se invierte.</p></div>' +
    '<p class="camara-error" id="camara-error" role="alert" hidden></p>' +
    '<div class="camara-controles">' +
      '<button type="button" class="btn" id="camara-cerrar">Cerrar</button>' +
      '<button type="button" id="camara-disparo" aria-label="Capturar foto"></button>' +
      '<button type="button" class="btn" id="camara-cambiar" aria-label="Cambiar de cámara">Cambiar</button>' +
    '</div>' +
    '<div class="camara-respaldo">' +
      '<label class="btn btn-secundario" for="camara-sistema">Cámara del sistema</label>' +
    '</div>' +
    '<input id="camara-sistema" class="solo-sr" type="file" accept="image/*" capture="environment">';
  document.body.appendChild(dlg);

  var video = document.getElementById("camara-video");
  var errorEl = document.getElementById("camara-error");
  var guia = document.getElementById("camara-guia");
  var disparo = document.getElementById("camara-disparo");
  var stream = null;
  var frente = false;
  var previo = null;

  video.setAttribute("playsinline", "true");
  video.setAttribute("webkit-playsinline", "true");
  video.muted = true;
  video.autoplay = true;

  function mostrarError(texto) {
    errorEl.hidden = !texto;
    errorEl.textContent = texto || "";
    guia.hidden = !!texto;
    disparo.disabled = !!texto;
  }

  function mensaje(err) {
    var name = err && err.name;
    if (!window.isSecureContext) {
      return "Este visor bloquea la cámara fuera de una conexión segura. Use la cámara del sistema o cierre y elija la foto desde la galería.";
    }
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      return "No hay permiso para la cámara. Puede autorizarla en el sistema, usar la cámara del sistema o cerrar y elegir la foto desde la galería.";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError" || name === "OverconstrainedError") {
      return "No se encontró una cámara utilizable. Use la cámara del sistema o la galería.";
    }
    if (name === "NotReadableError" || name === "TrackStartError") {
      return "La cámara está ocupada por otra aplicación. Ciérrela e inténtelo de nuevo, o use la galería.";
    }
    return "No se pudo abrir la cámara en vivo. Use la cámara del sistema o la galería. La aplicación no se interrumpe.";
  }

  function detener() {
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    if (video) video.srcObject = null;
  }

  function constraints() {
    return {
      audio: false,
      video: { facingMode: { ideal: frente ? "user" : "environment" } }
    };
  }

  function iniciar() {
    detener();
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      mostrarError("Este visor no ofrece cámara en vivo. Use la cámara del sistema o cierre y elija la foto desde la galería.");
      return Promise.resolve();
    }
    return navigator.mediaDevices.getUserMedia(constraints()).catch(function (err) {
      if (err && (err.name === "OverconstrainedError" || err.name === "ConstraintNotSatisfiedError")) {
        return navigator.mediaDevices.getUserMedia({ audio: false, video: true });
      }
      throw err;
    }).then(function (s) {
      if (!s) return;
      stream = s;
      video.srcObject = s;
      mostrarError("");
      var play = video.play();
      if (play && play.catch) play.catch(function () {});
    }).catch(function (err) {
      mostrarError(mensaje(err));
    });
  }

  function abrir() {
    previo = document.activeElement;
    dlg.hidden = false;
    document.body.classList.add("sin-scroll");
    frente = false;
    iniciar().then(function () {
      (disparo.disabled ? document.getElementById("camara-cerrar") : disparo).focus();
    });
  }

  function cerrar() {
    detener();
    dlg.hidden = true;
    document.body.classList.remove("sin-scroll");
    if (previo && previo.focus) previo.focus();
  }

  function capturar() {
    if (!video.videoWidth) {
      mostrarError("La cámara todavía no tiene imagen. Espere un momento y vuelva a capturar.");
      return;
    }
    var c = document.createElement("canvas");
    c.width = video.videoWidth;
    c.height = video.videoHeight;
    c.getContext("2d").drawImage(video, 0, 0);
    window.ChagasImagen.ponerCanvas(c, { origen: "camara", nombre: "Foto de la cámara" });
    cerrar();
  }

  document.getElementById("btn-camara").addEventListener("click", abrir);
  document.getElementById("camara-cerrar").addEventListener("click", cerrar);
  disparo.addEventListener("click", capturar);
  document.getElementById("camara-cambiar").addEventListener("click", function () {
    frente = !frente;
    iniciar();
  });
  document.getElementById("camara-sistema").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    window.ChagasImagen.ponerArchivo(file, { origen: "camara-sistema", nombre: file.name || "Foto de la cámara" });
    cerrar();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !dlg.hidden) cerrar();
  });
})();
