#!/usr/bin/env python3
"""
Organiza las carpetas de audio en categorías temáticas de eventos.
Crea symlinks en music/ sin mover ni copiar archivos.

Uso:
    python scripts/setup_categorias.py          # crear/actualizar
    python scripts/setup_categorias.py --dry-run # solo mostrar plan
    python scripts/setup_categorias.py --reset   # borrar music/ y recriar
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
MUSIC = ROOT / "music"
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".flac"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def link(src: Path, dst: Path, dry: bool) -> bool:
    """Create absolute symlink dst → src. Return True if created."""
    if not src.exists():
        return False
    if dst.is_symlink() or dst.exists():
        return False  # ya existe
    if dry:
        print(f"    LINK {dst.name} → {src}")
        return True
    dst.symlink_to(src)
    return True


def link_folder(cat_dir: Path, source: Path, prefix: str = "",
                include: list = None, dry: bool = False) -> int:
    """
    Link all audio files from source into cat_dir.
    include: list of lowercase substrings; only files whose name contains
             at least one are linked. None = all files.
    """
    if not source.is_dir():
        print(f"  ⚠ No encontrado: {source.relative_to(ROOT)}")
        return 0

    count = 0
    for f in sorted(source.iterdir()):
        if not f.is_file() or f.suffix.lower() not in AUDIO_EXT:
            continue
        if include and not any(s in f.name.lower() for s in include):
            continue

        dest_name = f"{prefix}{f.name}" if prefix else f.name
        dst = cat_dir / dest_name
        # resolve conflict: add numeric suffix
        if (dst.exists() or dst.is_symlink()) and prefix == "":
            stem, ext = f.stem, f.suffix
            i = 2
            while True:
                dst = cat_dir / f"{stem}_{i}{ext}"
                if not dst.exists() and not dst.is_symlink():
                    break
                i += 1

        if link(f, dst, dry):
            count += 1

    return count


def create_category(name: str, sources: list, dry: bool) -> int:
    """
    sources: list of (path_str, prefix, [include_list])
             path_str relative to ROOT.
    """
    cat_dir = MUSIC / name
    if not dry:
        cat_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for item in sources:
        if len(item) == 3:
            path_str, prefix, include = item
        else:
            path_str, prefix = item
            include = None

        src = ROOT / path_str
        n = link_folder(cat_dir, src, prefix, include, dry)
        if n:
            print(f"  + {n:3d} archivos  ←  {path_str}")
        total += n

    marker = "[DRY] " if dry else ""
    print(f"  {marker}→ {total} total  →  music/{name}/\n")
    return total


# ── Definición de categorías ─────────────────────────────────────────────────
#
# Formato de cada fuente:  (carpeta_relativa_al_root, prefijo, [filtro_opcional])
# filtro_opcional: lista de substrings (minúsculas) que deben aparecer en el nombre.

def build_categories(dry: bool):

    total_global = 0
    run = lambda name, sources: create_category(name, sources, dry)

    # ──────────────────────────────────────────────────────────────────────────
    print("🎃  1_DIA_DE_MUERTOS")
    total_global += run("1_DIA_DE_MUERTOS", [
        # Efectos terror/suspenso ambiente (festivo oscuro)
        ("Efectos musica/EFECTOS DE TERROR",       ""),
        ("Efectos musica/EFECTOS DE TERROR 2.0",   ""),
        # Halloween Monsters – ambiente nocturno perfecto para DdM
        ("Sound efectos/Halloween Monsters & Halloween Monsters"
         "/Halloween Monsters & Halloween Monsters"
         "/2016 - Efectos de Sonido Mr Dj & Halloween & Musica de Terror "
         "Specialists & Scary Sound Effects",                               ""),
        # Cinematic scores (tensión dramática)
        ("Efectos musica/CST001 - Trailer and Percussive Scores - 320 kbps", "cst_"),
        # COCO – iconic para Día de Muertos
        ("MUSICA INFANTIL 2021", "", ["002", "082", "coco"]),
        # Risa de bruja & efectos noche
        ("Efectos Musica 2/samples de 2022/2", "risa_", ["bruja", "noche", "terror"]),
        ("Efectos Musica 2/SoloParaDJs - Pack de Efectos - Samples Vocales"
         "/SoloParaDJs - Pack de Efectos - Samples Vocales",
         "", ["bruja", "terror", "horror", "miedo"]),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("👻  2_HALLOWEEN_TERROR")
    total_global += run("2_HALLOWEEN_TERROR", [
        # 101 sonidos de horror (biblioteca profesional)
        ("Efectos Musica 2/101 Sounds of Horror Sound Effects"
         "/101 Sounds of Horror Sound Effects",                 ""),
        # Efectos terror clásicos
        ("Efectos musica/EFECTOS DE TERROR",                    ""),
        ("Efectos musica/EFECTOS DE TERROR 2.0",                ""),
        # Las brujas (infantil pero sirve para Halloween temático)
        ("MUSICA INFANTIL 2021", "", ["157", "bruja", "fantasma", "monstruo"]),
        # Alan Howarth – Hollywood Sound FX (paranormal, alien, etc.)
        ("Efectos Musica 2/Alan Howarth/Alan Howarth"
         "/2001 - Alan Howarth - Real Hollywood Sound Effects",  "hw_"),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🎂  3_CUMPLEANOS")
    total_global += run("3_CUMPLEANOS", [
        # Mañanitas base + versiones
        ("Sound efectos/Cumpleaños Por Nombre/Cumpleaños Por Nombre"
         "/Cumpleaños por nombre",                              ""),
        ("Efectos Musica 2/Cumpleaños Por Nombre/Cumpleaños Por Nombre"
         "/Cumpleaños por nombre",                              ""),
        # Masculinos
        ("Sound efectos/Cumpleaños Por Nombre/Cumpleaños Por Nombre"
         "/Cumpleaños por nombre/Cumpleaños Masculinos",        "m_"),
        ("Efectos Musica 2/Cumpleaños Por Nombre/Cumpleaños Por Nombre"
         "/Cumpleaños por nombre/Cumpleaños Masculinos",        "m_"),
        # Mañanitas de Cepillín + Ardillitas
        ("MUSICA INFANTIL 2021", "", ["036", "037", "076", "128", "131",
                                      "mañanitas", "cumpleaños", "feliz cumple"]),
        # DJ Tools party vocals (aplausos, conteos, etc.)
        ("Sound efectos/DJ Tools and Party Vocal Sound Effects"
         "/DJ Tools and Party Vocal Sound Effects",             "dj_"),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🧒  4_INFANTIL_DISNEY")
    total_global += run("4_INFANTIL_DISNEY", [
        # Disney/Pixar/Nickelodeon songs
        ("MUSICA INFANTIL 2021", "", [
            "002", "003", "004", "005", "006", "007", "008", "009",
            "020", "021", "028", "084", "151", "152", "153",
            "coco", "frozen", "minion", "toy story", "cars", "rio",
            "bob esponja", "dora", "monster high", "aladino",
            "el chavo", "chapulin",
        ]),
        # Botargas Disney (Toy Story, Bambi, Pocahontas, Bella)
        ("Musica y efectos para Show/Musica de botargas", ""),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🎵  5_INFANTIL_CLASICOS")
    total_global += run("5_INFANTIL_CLASICOS", [
        # Cepillín, Topo Gigio, Ardillitas, Cri Cri, Barney
        ("MUSICA INFANTIL 2021", "", [
            "011", "014", "017", "018", "019", "022", "023", "024",
            "025", "026", "027", "029", "030", "031", "032", "033",
            "034", "035", "038", "039", "040", "041", "042",
            "043", "044", "045", "046", "055", "056", "057", "058",
            "059", "060", "061", "062", "063", "064", "065", "066",
            "067", "068", "069", "070", "071", "072", "073", "074",
            "075", "077", "079", "080", "081", "083", "085", "086",
            "087", "088", "089",
            "cepillin", "topo", "ardillitas", "cri cri", "barney",
            "platero", "sapito", "pollito", "anguila",
        ]),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🎄  6_NAVIDAD")
    total_global += run("6_NAVIDAD", [
        # Canciones navideñas infantiles
        ("MUSICA INFANTIL 2021", "", [
            "090", "109", "134", "135", "136", "137", "138", "139",
            "140", "141", "142", "143", "144", "145", "146", "147",
            "148", "149",
            "navidad", "santa", "noche buena", "cascabel", "reno",
            "reyes magos", "noche de paz",
        ]),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🎪  7_CIRCO_SHOW")
    total_global += run("7_CIRCO_SHOW", [
        ("Musica y efectos para Show/Musica de Circo",              ""),
        ("Musica y efectos para Show/Musica Circo",                 ""),
        ("Musica y efectos para Show/Bienvenidos al circo",         "bv_"),
        ("Musica y efectos para Show/El Gran Circo de Montecarlo",  "gc_"),
        ("Musica y efectos para Show/Ringling Bros. Circus",        "rb_"),
        ("Musica y efectos para Show/Circus Zauber",                "cz_"),
        ("Musica y efectos para Show/China Town",                   "ct_"),
        ("Musica y efectos para Show/Tihany Music Hall",            "th_"),
        ("Musica y efectos para Show/Salto Mortal",                 "sm_"),
        ("Musica y efectos para Show/Master Works Domi",            "mw_"),
        ("Musica y efectos para Show/Musica Especial",              "me_"),
        ("Musica y efectos para Show/Musica para show 1",           "s1_"),
        ("Musica y efectos para Show/Musica para show 2",           "s2_"),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🤡  8_PAYASOS")
    total_global += run("8_PAYASOS", [
        # Show de payasit@s (Disney + efectos chistosos)
        ("Musica y efectos para Show/Show de payasit@s", ""),
        # Sonidos chistosos tipo payaso
        ("Efectos Musica 2/SoloParaDJs - Pack de Efectos - Samples Vocales"
         "/SoloParaDJs - Pack de Efectos - Samples Vocales",
         "", ["callate", "chan", "boing", "cri cri", "risa", "trompeta de perdedor",
              "acabatelo", "chamoy", "cancion triste", "beso"]),
        # Efectos payaso clásico
        ("Efectos Brincos Dieras/Programa y BRINCO D/1 BRINCO DIERAS",
         "", ["boing", "chan", "risa", "trompeta", "cri cri", "acabatelo",
              "chamoy", "beso"]),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🎙  9_BRINCO_DIERAS")
    total_global += run("9_BRINCO_DIERAS", [
        # Toda la colección Brinco Dieras
        ("Efectos Brincos Dieras/Programa y BRINCO D/1 BRINCO DIERAS", ""),
        # Samplers Brinco Dieras de Efectos Musica 2
        ("Efectos Musica 2/Samplers Brinco Dieras", "bd2_"),
        # Voces y efectos chistosos
        ("Efectos Musica 2/SoloParaDJs - Pack de Efectos - Samples Vocales"
         "/SoloParaDJs - Pack de Efectos - Samples Vocales",  "vox_"),
        # Efectos Musica 2 pack 2023
        ("Efectos Musica 2/PACK EFECTOS PARA DJS 2023 (VOL.4)", "p23_"),
        # Personal DJ effects
        ("Efectos musica/DISK - EFECTOS  PERSONALES"
         "/DISK - EFECTOS  PERSONALES -",                      "prv_"),
    ])

    # ──────────────────────────────────────────────────────────────────────────
    print("🔊  Extras (sin hotkey directo):")
    print("━  DJ_EFECTOS")
    total_global += run("DJ_EFECTOS", [
        ("Efectos musica/EFECTOS",                              ""),
        ("Sound efectos/Efectos De Sonido Mr DJ"
         "/Efectos De Sonido Mr DJ",                           "mr_"),
        ("Efectos musica/Libreria Dj",                         "lib_"),
        ("Sound efectos/DJ Tools and Party Vocal Sound Effects"
         "/DJ Tools and Party Vocal Sound Effects",             "dj_"),
        ("Efectos Musica 2/Dj Sound Effects FX"
         "/Dj Sound Effects FX",                               "fx_"),
        ("Efectos musica/A ENTRADAS ESPECIALES",               "ent_"),
    ])

    print("━  LOOPS_FIESTA")
    total_global += run("LOOPS_FIESTA", [
        ("Efectos musica/BASES REGGAETON",          "rgt_"),
        ("Efectos musica/LOOPS  BASE CUMBIA",       "cum_"),
        ("Efectos musica/LOOPS  BASE SALSA",        "sal_"),
        ("Efectos musica/LOOPS  BASE ELECTRO",      "elc_"),
        ("Efectos Musica 2/LOOPS BASE MERENGUE",    "mrg_"),
        ("Efectos Musica 2/LOOPS BASE REGGAESTON",  "rg2_"),
        ("Efectos Musica 2/Loops EXCLUSIVOS RADIO", "rad_"),
    ])

    print(f"\n✅  Total archivos enlazados: {total_global}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar plan")
    parser.add_argument("--reset",   action="store_true",
                        help="Borrar todas las categorías en music/ y recrear")
    args = parser.parse_args()

    if args.reset and not args.dry_run:
        import shutil
        if MUSIC.exists():
            print(f"🗑  Borrando {MUSIC}...")
            shutil.rmtree(MUSIC)

    MUSIC.mkdir(exist_ok=True)

    print(f"\n📂 Root:  {ROOT}")
    print(f"🎵 Music: {MUSIC}")
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Organizando categorías...\n")

    build_categories(dry=args.dry_run)

    if not args.dry_run:
        # Contar resultados finales
        cats = sorted(d for d in MUSIC.iterdir() if d.is_dir())
        print("\n📊 Resumen final:")
        for cat in cats:
            count = sum(1 for f in cat.iterdir() if f.is_symlink() or f.is_file())
            print(f"   {cat.name:30s}  {count:4d} tracks")


if __name__ == "__main__":
    main()
