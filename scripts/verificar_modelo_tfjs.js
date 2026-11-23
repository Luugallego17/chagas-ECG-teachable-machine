// Compara una predicción de TensorFlow.js con la de Keras.
// Uso: node scripts/verificar_modelo_tfjs.js <carpeta del modelo> <caso.json>
// caso.json: { "entrada": [[[[...]]]], "esperado": [p0, p1, ...] }
// Código de salida 2 si la diferencia absoluta máxima pasa de 1e-4.
const fs = require("fs");
const path = require("path");

const tfjsDir =
  process.env.TFJS_NODE_MODULES ||
  "/tmp/tfjs-test/node_modules/@tensorflow/tfjs";
const tf = require(tfjsDir);

class Disco {
  constructor(dir) {
    this.dir = dir;
  }
  async load() {
    const documento = JSON.parse(fs.readFileSync(path.join(this.dir, "model.json"), "utf8"));
    const bin = fs.readFileSync(path.join(this.dir, "weights.bin"));
    return {
      modelTopology: documento.modelTopology,
      weightSpecs: documento.weightsManifest[0].weights,
      weightData: bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.byteLength),
    };
  }
}

(async () => {
  const dir = process.argv[2];
  const caso = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const modelo = await tf.loadLayersModel(new Disco(dir));
  const pred = await modelo.predict(tf.tensor(caso.entrada)).data();
  const esp = caso.esperado;
  let maxAbs = 0;
  for (let i = 0; i < pred.length; i++) maxAbs = Math.max(maxAbs, Math.abs(pred[i] - esp[i]));
  console.log(JSON.stringify({ maxAbs, pred: Array.from(pred), esperado: esp }));
  if (maxAbs > 1e-4) process.exit(2);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
