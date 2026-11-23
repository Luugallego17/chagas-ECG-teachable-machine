/* Elegir la foto del ECG desde la galería.
   El input no lleva capture, para que en el teléfono abra las fotos
   y no la cámara. La imagen entra al mismo flujo que la foto en vivo. */
(function () {
  "use strict";
  var slot = document.getElementById("slot-galeria");
  if (!slot || !window.ChagasImagen) return;

  slot.innerHTML =
    '<label class="btn btn-secundario" for="f-galeria">Galería</label>' +
    '<input id="f-galeria" class="solo-sr" type="file" accept="image/*" aria-label="Elegir una imagen de la galería">';

  document.getElementById("f-galeria").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    var tipo = file.type || "";
    var nombre = file.name || "";
    var parece = tipo.indexOf("image/") === 0 || (!tipo && /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(nombre));
    if (tipo && tipo.indexOf("image/") !== 0) {
      window.ChagasImagen.mostrarAlerta("Ese archivo no es una imagen. Elija un JPG o un PNG de la galería.");
      return;
    }
    if (!parece && nombre && !/\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(nombre)) {
      window.ChagasImagen.mostrarAlerta("Ese archivo no es una imagen. Elija un JPG o un PNG de la galería.");
      return;
    }
    window.ChagasImagen.ponerArchivo(file, { origen: "galeria", nombre: nombre || "Imagen de la galería" });
  });
})();
