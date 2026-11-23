// Preproceso del fonocardiograma. Tiene que coincidir con scripts/audio_comun.py:
// 4 kHz, 5 s, STFT Hann periódica, mel HTK 20–800 Hz, log y z-score del recorte.
// Sirve en el navegador (AudioPreproceso) y en Node (module.exports).
(function (raiz, fabrica) {
  var api = fabrica();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (raiz) raiz.AudioPreproceso = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SR = 4000;
  var N_SAMPLES = 20000;
  var FRAME_LENGTH = 256;
  var FRAME_STEP = 128;
  var FFT_LENGTH = 256;
  var N_BINS = FFT_LENGTH / 2 + 1;
  var N_FRAMES = 1 + Math.floor((N_SAMPLES - FRAME_LENGTH) / FRAME_STEP);
  var N_MELS = 64;
  var FMIN = 20;
  var FMAX = 800;
  var LOG_EPS = 1e-6;
  var UMBRAL_SILENCIO = 1e-4;

  function hannPeriodica(n) {
    var w = new Float64Array(n);
    for (var k = 0; k < n; k++) w[k] = 0.5 - 0.5 * Math.cos((2 * Math.PI * k) / n);
    return w;
  }

  var HANN = hannPeriodica(FRAME_LENGTH);

  function hzAMel(hz) {
    return 2595 * Math.log10(1 + hz / 700);
  }
  function melAHz(mel) {
    return 700 * (Math.pow(10, mel / 2595) - 1);
  }

  // Filtros triangulares, forma plana por filas: nMels * nBins.
  function matrizMel() {
    var nMels = N_MELS;
    var nBins = N_BINS;
    var puntos = new Float64Array(nMels + 2);
    var mel0 = hzAMel(FMIN);
    var mel1 = hzAMel(FMAX);
    for (var i = 0; i < puntos.length; i++) {
      puntos[i] = mel0 + ((mel1 - mel0) * i) / (nMels + 1);
    }
    var bins = new Int32Array(puntos.length);
    for (var p = 0; p < puntos.length; p++) {
      bins[p] = Math.floor(((FFT_LENGTH + 1) * melAHz(puntos[p])) / SR);
    }
    var banco = new Float64Array(nMels * nBins);
    for (var m = 0; m < nMels; m++) {
      var izquierda = bins[m];
      var centro = bins[m + 1];
      var derecha = bins[m + 2];
      if (centro <= izquierda) centro = izquierda + 1;
      if (derecha <= centro) derecha = centro + 1;
      for (var j = izquierda; j < centro; j++) {
        if (j >= 0 && j < nBins) banco[m * nBins + j] = (j - izquierda) / (centro - izquierda);
      }
      for (var j2 = centro; j2 < derecha; j2++) {
        if (j2 >= 0 && j2 < nBins) banco[m * nBins + j2] = (derecha - j2) / (derecha - centro);
      }
    }
    return banco;
  }

  var MEL = null;
  function mel() {
    if (!MEL) MEL = matrizMel();
    return MEL;
  }

  // FFT radix-2 en el sitio. El signo es e^{-2πi}, como numpy.fft.
  function fft(re, im) {
    var n = re.length;
    for (var i = 1, j = 0; i < n; i++) {
      var bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        var tr = re[i]; re[i] = re[j]; re[j] = tr;
        var ti = im[i]; im[i] = im[j]; im[j] = ti;
      }
    }
    for (var len = 2; len <= n; len <<= 1) {
      var ang = (-2 * Math.PI) / len;
      var wlenRe = Math.cos(ang);
      var wlenIm = Math.sin(ang);
      for (var ini = 0; ini < n; ini += len) {
        var wRe = 1;
        var wIm = 0;
        var half = len >> 1;
        for (var k = 0; k < half; k++) {
          var uRe = re[ini + k];
          var uIm = im[ini + k];
          var xRe = re[ini + k + half];
          var xIm = im[ini + k + half];
          var vRe = xRe * wRe - xIm * wIm;
          var vIm = xRe * wIm + xIm * wRe;
          re[ini + k] = uRe + vRe;
          im[ini + k] = uIm + vIm;
          re[ini + k + half] = uRe - vRe;
          im[ini + k + half] = uIm - vIm;
          var nRe = wRe * wlenRe - wIm * wlenIm;
          var nIm = wRe * wlenIm + wIm * wlenRe;
          wRe = nRe;
          wIm = nIm;
        }
      }
    }
  }

  function magnitudCuadro(cuadro) {
    var re = new Float64Array(FFT_LENGTH);
    var im = new Float64Array(FFT_LENGTH);
    for (var i = 0; i < FRAME_LENGTH; i++) re[i] = cuadro[i];
    fft(re, im);
    var mag = new Float64Array(N_BINS);
    for (var k = 0; k < N_BINS; k++) mag[k] = Math.hypot(re[k], im[k]);
    return mag;
  }

  function remuestrearLineal(onda, srDesde, srHasta) {
    if (srDesde === srHasta) return onda;
    var nIn = onda.length;
    if (nIn < 2 || srDesde <= 0 || srHasta <= 0) return new Float32Array(0);
    var nOut = Math.round((nIn * srHasta) / srDesde);
    if (nOut < 2) return new Float32Array(nOut);
    var out = new Float32Array(nOut);
    var ultimo = nIn - 1;
    for (var i = 0; i < nOut; i++) {
      var x = (i * ultimo) / (nOut - 1);
      var i0 = Math.floor(x);
      var i1 = Math.min(i0 + 1, ultimo);
      var f = x - i0;
      out[i] = onda[i0] * (1 - f) + onda[i1] * f;
    }
    return out;
  }

  // Devuelve Float32Array de N_MELS * N_FRAMES, fila = mel, columna = tiempo.
  function logMel(onda) {
    if (onda.length !== N_SAMPLES) {
      throw new Error("se esperaban " + N_SAMPLES + " muestras y llegaron " + onda.length);
    }
    var banco = mel();
    var spec = new Float64Array(N_MELS * N_FRAMES);
    var cuadro = new Float64Array(FRAME_LENGTH);
    for (var t = 0; t < N_FRAMES; t++) {
      var ini = t * FRAME_STEP;
      for (var i = 0; i < FRAME_LENGTH; i++) cuadro[i] = onda[ini + i] * HANN[i];
      var mag = magnitudCuadro(cuadro);
      for (var m = 0; m < N_MELS; m++) {
        var acc = 0;
        var base = m * N_BINS;
        for (var b = 0; b < N_BINS; b++) acc += mag[b] * banco[base + b];
        spec[m * N_FRAMES + t] = Math.log(acc + LOG_EPS);
      }
    }
    var media = 0;
    for (var s = 0; s < spec.length; s++) media += spec[s];
    media /= spec.length;
    var varianza = 0;
    for (var s2 = 0; s2 < spec.length; s2++) {
      var d = spec[s2] - media;
      varianza += d * d;
    }
    var desv = Math.sqrt(varianza / spec.length);
    if (desv < 1e-8) desv = 1;
    var out = new Float32Array(spec.length);
    for (var s3 = 0; s3 < spec.length; s3++) out[s3] = (spec[s3] - media) / desv;
    return out;
  }

  function rms(onda) {
    var e = 0;
    for (var i = 0; i < onda.length; i++) e += onda[i] * onda[i];
    return Math.sqrt(e / onda.length);
  }

  // samples: Float32Array mono en [-1, 1], a sampleRate Hz.
  // Si cabe, se usan los primeros 5 s (igual que la primera ventana del entrenamiento).
  function preparar(samples, sampleRate) {
    var rs = remuestrearLineal(samples, sampleRate, SR);
    var duracion = rs.length / SR;
    if (rs.length < N_SAMPLES) {
      return { ok: false, motivo: "corto", duracion: duracion };
    }
    var clip = rs.subarray(0, N_SAMPLES);
    var energia = rms(clip);
    if (energia < UMBRAL_SILENCIO) {
      return { ok: false, motivo: "silencio", duracion: duracion, clip: clip };
    }
    return { ok: true, spec: logMel(clip), clip: clip, duracion: duracion, rms: energia };
  }

  return {
    SR: SR,
    N_SAMPLES: N_SAMPLES,
    N_MELS: N_MELS,
    N_FRAMES: N_FRAMES,
    N_BINS: N_BINS,
    FRAME_LENGTH: FRAME_LENGTH,
    FRAME_STEP: FRAME_STEP,
    FFT_LENGTH: FFT_LENGTH,
    FMIN: FMIN,
    FMAX: FMAX,
    LOG_EPS: LOG_EPS,
    UMBRAL_SILENCIO: UMBRAL_SILENCIO,
    remuestrearLineal: remuestrearLineal,
    matrizMel: matrizMel,
    logMel: logMel,
    preparar: preparar,
  };
});
