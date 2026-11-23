// Compara matriz mel y log-mel de JS contra el JSON que escribe el test de Python.
// Uso: node tests/comparar_preproceso.js <caso.json>
const fs = require("fs");
const pre = require("../app/audio_preprocess.js");

const caso = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const banco = pre.matrizMel();
let maxMel = 0;
for (let i = 0; i < banco.length; i++) maxMel = Math.max(maxMel, Math.abs(banco[i] - caso.mel[i]));
const spec = pre.logMel(Float32Array.from(caso.onda));
let maxSpec = 0;
for (let i = 0; i < spec.length; i++) maxSpec = Math.max(maxSpec, Math.abs(spec[i] - caso.logmel[i]));
const rs = pre.remuestrearLineal(Float32Array.from(caso.ondaCorta), caso.srCorta, pre.SR);
let maxRs = 0;
for (let i = 0; i < rs.length; i++) maxRs = Math.max(maxRs, Math.abs(rs[i] - caso.remuestreo[i]));
console.log(JSON.stringify({ maxMel, maxSpec, maxRs, nMel: banco.length, nSpec: spec.length }));
if (maxMel > 1e-6 || maxSpec > 1e-4 || maxRs > 1e-5) process.exit(2);
