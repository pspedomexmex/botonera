# Carpeta de música y efectos de sonido

Los archivos de audio **no se incluyen en el repositorio** (derechos de autor y tamaño).  
Debes colocar tus propios efectos aquí antes de ejecutar la app.

## Formatos soportados

`.mp3` · `.wav` · `.ogg` · `.flac`

## Estructura de carpetas

Cada subcarpeta corresponde a una categoría del soundboard.  
La app la detecta automáticamente si contiene al menos un archivo de audio.

```
music/
├── 1_DIA_DE_MUERTOS/      # Efectos y música de Día de Muertos
├── 2_HALLOWEEN_TERROR/    # Terror, suspenso, Halloween
├── 3_CUMPLEANOS/          # Cumpleaños: manor, fanfarrias, efectos
├── 4_INFANTIL_DISNEY/     # Música infantil temática (Disney, películas)
├── 5_INFANTIL_CLASICOS/   # Canciones infantiles clásicas
├── 6_NAVIDAD/             # Villancicos y ambiente navideño
├── 7_CIRCO_SHOW/          # Música de circo, entradas, show
├── 8_PAYASOS/             # Efectos y música de payasos
├── 9_BRINCO_DIERAS/       # Samplers / efectos de show en vivo
├── DJ_EFECTOS/            # Efectos para DJ: risas, aplausos, transiciones
└── LOOPS_FIESTA/          # Loops y bases para animar fiestas
```

## Agregar una categoría nueva

Crea una subcarpeta con el nombre que quieras y coloca audio dentro.  
La app la descubrirá sola al arrancar:

```
music/
└── MI_CATEGORIA/
    ├── efecto1.mp3
    └── efecto2.wav
```

O bien, registra la categoría en `botonera_config.json` para asignarle
hotkey, color e ícono:

```json
{
  "name": "🎸 Rock",
  "folder": "MI_CATEGORIA",
  "hotkey": "0",
  "color": "red"
}
```

## Dónde conseguir efectos libres de derechos

- [Freesound.org](https://freesound.org) — licencias CC0 y CC-BY
- [Pixabay Sound Effects](https://pixabay.com/sound-effects/) — uso libre
- [Mixkit](https://mixkit.co/free-sound-effects/) — uso libre
- [BBC Sound Effects](https://sound-effects.bbcrewind.co.uk) — uso no comercial

> **Nota:** Los archivos de audio que uses son responsabilidad tuya.  
> Verifica que tengas los derechos para usarlos en tu contexto (privado, comercial, etc.).
