# Chagas ECG para Android

Envoltorio [Capacitor](https://capacitorjs.com/) de la app web (`app/` y `modelo/`).
Identificador: `bo.ucb.chagas.ecg`. Nombre visible: **Chagas ECG**.

La aplicación abre el asistente dentro de un WebView. TensorFlow.js, Teachable Machine
y los dos modelos van dentro del paquete: no hace falta red para clasificar.
El electrocardiograma sigue embebido en `app/asistente.html`. El fonocardiograma
se lee de `modelo/audio/`.

No se usa el micrófono. La galería y los archivos los abre el selector del sistema.

## Permisos

El manifiesto declara solo `android.permission.CAMERA`. No hay `RECORD_AUDIO`,
ni permiso de lectura de fotos o de almacenamiento.

- **Cámara.** Se pide en el momento de pulsar «Tomar foto». El WebView avisa
  a Capacitor (`onPermissionRequest` con `VIDEO_CAPTURE`) y ahí aparece el
  diálogo del sistema. Si la persona lo niega, la página lo explica y sigue
  con la galería.
- **Galería y archivo de audio.** Los abre el selector del sistema
  (`input type="file"`). En Android reciente ese selector no exige
  `READ_MEDIA_IMAGES` ni `READ_MEDIA_AUDIO`.
- **Red.** No se declara `INTERNET`. Los modelos y las librerías van dentro
  del APK. La recarga en vivo de Capacitor, que sí usa red, no forma parte
  de este paquete.

La cámara no es obligatoria (`android:required="false"`): un aparato sin
cámara puede instalar la app y usar la galería.

## Qué hace falta

- Node.js 20 o superior
- JDK 21
- Android SDK (platform 36 y build-tools 36) y Android Studio, o solo las
  herramientas de línea de comandos

`ANDROID_HOME` debe apuntar al SDK. Ejemplo:

```bash
export ANDROID_HOME="$HOME/android-sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"
```

## Generar el APK de depuración

Desde la raíz del repositorio:

```bash
cd mobile
npm install
npm run apk
```

`npm run apk` copia `app/` y `modelo/` a `mobile/www`, sincroniza Capacitor y
ejecuta `./gradlew assembleDebug`. Gradle firma ese APK con la clave de
depuración de Android (`~/.android/debug.keystore`), que se crea sola la
primera vez.

El archivo queda en:

```text
mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

Ese binario no se sube a git. Para publicarlo como borrador:

```bash
gh release create v1.0.0-beta mobile/android/app/build/outputs/apk/debug/app-debug.apk \
  --title "v1.0.0-beta" \
  --notes "APK de depuración, firmado con la clave debug. No es un dispositivo médico."
```

Para instalarlo en un emulador o un teléfono con depuración USB:

```bash
adb install -r mobile/android/app/build/outputs/apk/debug/app-debug.apk
```

## Carpetas que no se versionan

`node_modules/`, `www/` (se regenera), `android/app/build/`, `.gradle/` y los `.apk`.
Sí se versionan `package.json`, `capacitor.config.json`, este archivo y el
proyecto `android/` sin los productos de compilación.
