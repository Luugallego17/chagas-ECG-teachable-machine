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

## Firma de la versión que se instala

El APK para el teléfono es de **release**, no el de depuración. El de depuración
solo llevaba la firma v2 y `minSdk` 24; varios teléfonos lo rechazan al
instalarlo a mano.

`minSdk` queda en 24 (Android 7.0). Capacitor 8 arrastra
`org.apache.cordova:framework:14.0.1`, y ese manifiesto no acepta un mínimo
menor: el empaquetado falla si se pone 23. Un teléfono con Android 6 no puede
instalar la app. La firma de release activa los esquemas v1, v2 y v3, y el
paquete no lleva `android:testOnly` ni `android:debuggable`.

La clave no está en git. Se crea una vez y se guarda fuera del repositorio.
Alias: `chagas-ecg`. Algoritmo: RSA 2048. Validez: 10000 días.
El archivo de contraseñas tampoco se escribe aquí.

```bash
keytool -genkeypair -v \
  -keystore chagas-ecg-release.keystore \
  -alias chagas-ecg -keyalg RSA -keysize 2048 -validity 10000
```

En `mobile/android/keystore.properties` (también ignorado por git):

```properties
storeFile=/ruta/absoluta/chagas-ecg-release.keystore
storePassword=...
keyAlias=chagas-ecg
keyPassword=...
```

## Generar el APK

Desde la raíz del repositorio:

```bash
cd mobile
npm install
sh empaquetar.sh
npx cap sync android
cd android && ./gradlew assembleRelease
```

El archivo queda en:

```text
mobile/android/app/build/outputs/apk/release/app-release.apk
```

Ese binario no se sube a git. Si hay que reinstalar encima de un APK de
depuración, primero se desinstala la copia anterior: la firma no coincide.

`npm run apk` sigue generando el APK de depuración, firmado solo con la clave
debug de Android. No es el que conviene pasar a un teléfono.

Para instalarlo en un teléfono con depuración USB:

```bash
adb install -r mobile/android/app/build/outputs/apk/release/app-release.apk
```

## Carpetas que no se versionan

`node_modules/`, `www/` (se regenera), `android/app/build/`, `.gradle/`,
`android/keystore.properties`, los `.keystore` y los `.apk`.
Sí se versionan `package.json`, `capacitor.config.json`, este archivo y el
proyecto `android/` sin los productos de compilación.
