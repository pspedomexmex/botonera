"""Flask REST API for Botonera event soundboard."""
import argparse
import fnmatch
import logging
import logging.handlers
import signal
import sys
import threading
from pathlib import Path

from flask import Flask, g, jsonify, request, abort, render_template

# ---------------------------------------------------------------------------
# Allow running as `python -m src.backend.app` from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backend.config import (
    BotoneraConfig, CategoryConfig,
    discover_categories, get_tracks, load_config, validate_file_path,
)
from src.backend.player import AudioPlayer

# ---------------------------------------------------------------------------
MAX_CLIENTS = 10

app = Flask(__name__, template_folder='templates')
_player: AudioPlayer = None
_config: BotoneraConfig = None
_categories: list = []
_sem = threading.Semaphore(MAX_CLIENTS)

logger = logging.getLogger(__name__)


# ── CORS / Security ─────────────────────────────────────────────────────────

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['X-Content-Type-Options']       = 'nosniff'
    return response


@app.before_request
def check_allowed():
    addr = request.remote_addr or ''
    if not _is_allowed(addr):
        logger.warning(f"Blocked {addr}")
        abort(403)
    if not _sem.acquire(blocking=False):
        abort(503, description="Too many concurrent clients")
    g.slot_acquired = True


@app.teardown_request
def release_slot(_exc):
    if getattr(g, 'slot_acquired', False):
        _sem.release()


def _is_allowed(addr: str) -> bool:
    if addr in ('127.0.0.1', '::1', 'localhost', ''):
        return True
    for pattern in (_config.server.allowed_ips if _config else []):
        if fnmatch.fnmatch(addr, pattern):
            return True
    return False


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})


@app.route('/api/categories')
def api_categories():
    cats = []
    for cat in _categories:
        cats.append({
            "name":        cat.name,
            "folder":      cat.folder,
            "hotkey":      cat.hotkey,
            "color":       cat.color,
            "track_count": len(get_tracks(_config.music_dir, cat.folder)),
        })
    return jsonify({"categories": cats, "status": "ready"})


@app.route('/api/tracks')
def api_tracks():
    category = request.args.get('category', '').strip()
    if not category:
        return jsonify({"error": "category required"}), 400
    cat = _find_category(category)
    if not cat:
        return jsonify({"error": "category not found"}), 404
    return jsonify({"tracks": get_tracks(_config.music_dir, cat.folder), "category": category})


@app.route('/api/play', methods=['POST'])
def api_play():
    data = request.get_json(silent=True) or {}
    filename = str(data.get('file', '')).strip()
    category = str(data.get('category', '')).strip()

    if not filename:
        return jsonify({"error": "file required"}), 400

    folder = category
    cat = _find_category(category)
    if cat:
        folder = cat.folder

    fpath = validate_file_path(_config.music_dir, folder, filename)
    if not fpath:
        return jsonify({"error": "invalid file"}), 400

    ok = _player.play(fpath, f"{folder}/{filename}")
    if ok:
        return jsonify({"status": "playing", "elapsed": 0, "track": filename})
    return jsonify({"error": "playback failed"}), 500


@app.route('/api/pause', methods=['POST'])
def api_pause():
    _player.pause()
    return jsonify({"status": _player.get_status()["status"]})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    _player.stop()
    return jsonify({"status": "stopped"})


@app.route('/api/volume', methods=['POST'])
def api_volume():
    data = request.get_json(silent=True) or {}
    try:
        vol = int(data.get('volume', 70))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid volume"}), 400
    vol = max(0, min(100, vol))
    _player.set_volume(vol)
    return jsonify({"volume": vol})


@app.route('/api/status')
def api_status():
    return jsonify(_player.get_status())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_category(name: str) -> CategoryConfig | None:
    name_l = name.lower().strip()
    # Strip emoji/symbols for fallback comparison (keep only letters/digits/spaces)
    import re as _re
    name_clean = _re.sub(r'[^\w\s]', '', name_l).strip()
    for c in _categories:
        cat_name_l  = c.name.lower()
        cat_clean   = _re.sub(r'[^\w\s]', '', cat_name_l).strip()
        if (cat_name_l == name_l
                or c.folder.lower() == name_l
                or cat_clean == name_clean
                or c.hotkey == name_l):
            return c
    return None


# ── Setup / Main ─────────────────────────────────────────────────────────────

def setup_logging(log_dir: str, level: str = "INFO"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fh = logging.handlers.TimedRotatingFileHandler(
        Path(log_dir) / "botonera.log", when='midnight', backupCount=7, encoding='utf-8'
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)


def _graceful_shutdown(signum, _frame):
    logger.info("Shutdown signal received")
    if _player:
        _player.shutdown()
    sys.exit(0)


def main():
    global _player, _config, _categories

    parser = argparse.ArgumentParser(description="Botonera Backend")
    parser.add_argument('--port',      type=int, default=5000)
    parser.add_argument('--host',      default='0.0.0.0')
    parser.add_argument('--music-dir', default='./music')
    parser.add_argument('--config',    default='./botonera_config.json')
    parser.add_argument('--log-dir',   default='./logs')
    parser.add_argument('--log-level', default='INFO')
    args = parser.parse_args()

    setup_logging(args.log_dir, args.log_level)
    logger.info("=== Botonera Backend starting ===")

    _config     = load_config(args.config, args.music_dir)
    _categories = discover_categories(_config.music_dir, _config.categories)
    logger.info(f"Loaded {len(_categories)} categories from '{_config.music_dir}'")

    _player = AudioPlayer()

    signal.signal(signal.SIGINT,  _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    host = args.host or _config.server.host
    port = args.port or _config.server.port
    logger.info(f"API on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
