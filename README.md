# 🎛️ Botonera — Soundboard REST API para eventos en vivo

**API Flask + pygame que convierte cualquier computadora en una consola de efectos de sonido controlable desde la red local.** Diseñada para animadores, DJs y operadores de audio en fiestas, shows y eventos en vivo.

El operador lanza efectos desde su teléfono, tablet o cualquier dispositivo conectado al mismo Wi-Fi — sin teclado, sin ratón, manos libres.

---

## ✨ Características

- 🎵 **Reproducción de audio** (MP3, WAV, OGG, FLAC) vía pygame, sin latencia perceptible
- 📂 **Categorías configurables** — organiza tus efectos por temática (Halloween, cumpleaños, circo, navidad…)
- 🔍 **Auto-descubrimiento** — cualquier subcarpeta con audio en `music/` se convierte en categoría automáticamente
- 🌐 **Control remoto por HTTP** — cualquier dispositivo en la red puede disparar efectos vía REST
- 🔒 **Seguridad básica** — whitelist de IPs, semáforo de concurrencia (máx. 10 clientes), protección contra path traversal
- ⌨️ **Hotkeys configurables** por categoría
- 📋 **Logs con rotación** diaria (7 días de historial)
- ✅ **Tests** unitarios e integración incluidos (pytest)

---

## 🏗️ Stack técnico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| API | Flask 3.x |
| Audio | pygame 2.5 |
| Monitoreo | psutil |
| Tests | pytest + pytest-cov |

---

## 📁 Estructura del proyecto

```
botonera/
├── src/
│   ├── backend/
│   │   ├── app.py        # Flask API — 8 endpoints
│   │   ├── config.py     # Carga de config y descubrimiento de categorías
│   │   └── player.py     # AudioPlayer (pygame)
│   └── cli/
│       └── interface.py  # Interfaz de línea de comandos
├── tests/
│   ├── test_backend.py      # Tests unitarios (config, rutas, seguridad)
│   ├── test_integration.py  # Tests de API con Flask test client
│   └── stability_test.py    # Tests de estabilidad
├── scripts/
│   └── setup_categorias.py  # Script de configuración inicial
├── music/                   # ← TUS efectos van aquí (ver music/README.md)
│   ├── 1_DIA_DE_MUERTOS/
│   ├── 2_HALLOWEEN_TERROR/
│   ├── 3_CUMPLEANOS/
│   └── ...
├── botonera_config.json     # Configuración de categorías y servidor
├── requirements.txt
└── requirements-dev.txt
```

---

## 🚀 Instalación

```bash
git clone https://github.com/pspedomexmex/botonera.git
cd botonera

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> **Dependencia del sistema:** pygame requiere SDL2.  
> En Debian/Ubuntu: `sudo apt install libsdl2-mixer-2.0-0`

---

## 🎵 Agregar efectos de sonido

Los archivos de audio **no están incluidos** en el repositorio.  
Coloca los tuyos en las subcarpetas de `music/` según la temática:

```
music/
├── 1_DIA_DE_MUERTOS/   ← pon aquí tus mp3/wav de Día de Muertos
├── 2_HALLOWEEN_TERROR/ ← efectos de terror
├── 3_CUMPLEANOS/       ← fanfarrias, manor, etc.
└── ...
```

Consulta [`music/README.md`](music/README.md) para la guía completa, incluyendo fuentes de efectos libres de derechos.

---

## ▶️ Ejecución

```bash
# Arranque básico (puerto 5000, carpeta ./music)
python -m src.backend.app

# Con parámetros
python -m src.backend.app --port 8080 --host 127.0.0.1 --music-dir /ruta/a/mis/efectos

# Ver todas las opciones
python -m src.backend.app --help
```

La API queda disponible en `http://localhost:5000`.

---

## 🔌 Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/health` | Health check — `{"status": "ok"}` |
| `GET` | `/api/categories` | Lista de categorías con conteo de pistas |
| `GET` | `/api/tracks?category=X` | Tracks de una categoría |
| `POST` | `/api/play` | Reproduce un efecto `{"file": "...", "category": "..."}` |
| `POST` | `/api/pause` | Pausa / reanuda |
| `POST` | `/api/stop` | Detiene la reproducción |
| `POST` | `/api/volume` | Ajusta volumen `{"volume": 0-100}` |
| `GET` | `/api/status` | Estado actual del reproductor |

### Ejemplo rápido (curl)

```bash
# Ver categorías disponibles
curl http://localhost:5000/api/categories

# Reproducir un efecto
curl -X POST http://localhost:5000/api/play \
     -H "Content-Type: application/json" \
     -d '{"category": "DJ_EFECTOS", "file": "aplausos.mp3"}'

# Ajustar volumen al 80%
curl -X POST http://localhost:5000/api/volume \
     -H "Content-Type: application/json" \
     -d '{"volume": 80}'
```

---

## ⚙️ Configuración (`botonera_config.json`)

```json
{
  "music_dir": "./music",
  "categories": [
    { "name": "🎃 Halloween", "folder": "2_HALLOWEEN_TERROR", "hotkey": "2", "color": "red" }
  ],
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "allowed_ips": ["127.0.0.1", "192.168.1.*", "192.168.0.*"]
  }
}
```

Las carpetas en `music/` que no estén en `categories` se agregan automáticamente al arrancar.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing   # con cobertura
```

---

## 👤 Autor

**Edgar Climaco Martínez** — Ingeniero en Sistemas Computacionales · Ciberseguridad · Maestría en IA  
[GitHub](https://github.com/pspedomexmex)

## 📄 Licencia

MIT
