"""ncurses CLI interface for Botonera. Min terminal: 80x24."""
import argparse
import curses
import logging
import sys
import threading
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

POLL_INTERVAL = 0.5   # status poll frequency (s)
UI_FPS        = 20    # redraws per second


class BotoneraUI:
    def __init__(self, server: str, stdscr):
        self.server  = server.rstrip('/')
        self.scr     = stdscr
        self.running = True
        self._lock   = threading.Lock()

        self.categories    = []
        self.cat_idx       = 0
        self.tracks        = []
        self.track_idx     = 0
        self.status        = {"status": "stopped", "track": None, "elapsed": 0, "volume": 70}
        self.message       = "Conectando..."
        self.connected     = False

        threading.Thread(target=self._poll_loop, daemon=True, name="poll").start()
        self._load_categories()

    # ── API helpers ───────────────────────────────────────────────────────

    def _get(self, endpoint: str, **params):
        try:
            r = requests.get(f"{self.server}{endpoint}", params=params, timeout=2)
            self.connected = True
            return r.json()
        except requests.ConnectionError:
            self.connected = False
            self.message = "Sin conexión — reintentando..."
            return None
        except Exception as e:
            self.message = f"Error: {e}"
            return None

    def _post(self, endpoint: str, **body):
        try:
            r = requests.post(f"{self.server}{endpoint}", json=body, timeout=2)
            self.connected = True
            return r.json()
        except requests.ConnectionError:
            self.connected = False
            return None
        except Exception as e:
            self.message = f"Error: {e}"
            return None

    # ── Data loading ──────────────────────────────────────────────────────

    def _load_categories(self):
        data = self._get('/api/categories')
        if data:
            with self._lock:
                self.categories = data.get('categories', [])
                self.cat_idx    = 0
            if self.categories:
                self._load_tracks(0)
            self.message = f"{len(self.categories)} categorías cargadas"

    def _load_tracks(self, idx: int):
        cats = self.categories
        if not cats or idx >= len(cats):
            return
        data = self._get('/api/tracks', category=cats[idx]['name'])
        if data:
            with self._lock:
                self.tracks    = data.get('tracks', [])
                self.track_idx = 0

    def _poll_loop(self):
        while self.running:
            data = self._get('/api/status')
            if data:
                with self._lock:
                    self.status = data
            # Auto-reload categories if disconnected and reconnected
            if not self.connected:
                time.sleep(2)
                self._load_categories()
            time.sleep(POLL_INTERVAL)

    # ── Input handling ────────────────────────────────────────────────────

    def _handle_key(self, key: int):
        with self._lock:
            cats  = self.categories
            trks  = self.tracks
            ci    = self.cat_idx
            ti    = self.track_idx
            vol   = self.status.get('volume', 70)
            state = self.status.get('status', 'stopped')

        # Category hotkeys 1-9
        if ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(cats):
                with self._lock:
                    self.cat_idx = idx
                self._load_tracks(idx)
                self.message = f"► {cats[idx]['name']}"
            return

        if key == ord(' '):            # play / pause toggle
            if state in ('playing', 'paused'):
                self._post('/api/pause')
            elif trks:
                self._play_selected(ci, ti)
            return

        if key in (curses.KEY_ENTER, 10, 13):   # play selected track
            self._play_selected(ci, ti)
            return

        if key in (27, ord('q')):      # ESC / q = stop
            self._post('/api/stop')
            self.message = "Detenido"
            return

        if key == curses.KEY_UP and trks:
            with self._lock:
                self.track_idx = max(0, ti - 1)
            return

        if key == curses.KEY_DOWN and trks:
            with self._lock:
                self.track_idx = min(len(trks) - 1, ti + 1)
            return

        if key == curses.KEY_LEFT and cats:
            new_idx = max(0, ci - 1)
            with self._lock:
                self.cat_idx = new_idx
            self._load_tracks(new_idx)
            return

        if key == curses.KEY_RIGHT and cats:
            new_idx = min(len(cats) - 1, ci + 1)
            with self._lock:
                self.cat_idx = new_idx
            self._load_tracks(new_idx)
            return

        if key in (ord('v'), ord('V')):
            self._post('/api/volume', volume=min(100, vol + 5))
            return

        if key in (ord('b'), ord('B')):
            self._post('/api/volume', volume=max(0, vol - 5))
            return

        if key == ord('r'):
            self._load_categories()
            return

    def _play_selected(self, cat_idx: int, track_idx: int):
        with self._lock:
            if not self.tracks or track_idx >= len(self.tracks):
                return
            track = self.tracks[track_idx]
            cat   = self.categories[cat_idx] if self.categories else {}
        self._post('/api/play', file=track, category=cat.get('folder', ''))
        self.message = f"► {track}"

    # ── Drawing ───────────────────────────────────────────────────────────

    def _draw(self):
        self.scr.erase()
        h, w = self.scr.getmaxyx()

        with self._lock:
            status   = dict(self.status)
            cats     = list(self.categories)
            trks     = list(self.tracks)
            ci       = self.cat_idx
            ti       = self.track_idx
            msg      = self.message
            conn     = self.connected

        curses.init_pair(1, curses.COLOR_CYAN,    -1)
        curses.init_pair(2, curses.COLOR_GREEN,   -1)
        curses.init_pair(3, curses.COLOR_YELLOW,  -1)
        curses.init_pair(4, curses.COLOR_RED,     -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)

        COL_BORDER  = curses.color_pair(1)
        COL_NOW     = curses.color_pair(2)
        COL_SEL     = curses.color_pair(3) | curses.A_BOLD
        COL_MSG     = curses.color_pair(4)
        COL_HELP    = curses.color_pair(5)

        def W(y, x, text, attr=0):
            if y >= h - 1 or x >= w - 1:
                return
            try:
                self.scr.addstr(y, x, text[:w - x - 1], attr)
            except curses.error:
                pass

        def row_fill(y, inner: str, attr=0):
            padded = inner[:w - 4]
            line   = '│ ' + padded + ' ' * (w - 4 - len(padded)) + ' │'
            W(y, 0, line, attr)

        def divider(y, left='├', right='┤'):
            W(y, 0, left + '─' * (w - 2) + right, COL_BORDER)

        state_map = {
            'playing': 'REPRODUCIENDO', 'paused': 'PAUSADO',
            'stopped': 'DETENIDO',      'error':  'ERROR',
        }
        estado = state_map.get(status.get('status', 'stopped'), 'DESCONOCIDO')
        conn_tag = '' if conn else ' [SIN CONEXIÓN]'

        row = 0
        W(row, 0, '┌' + '─' * (w - 2) + '┐', COL_BORDER);  row += 1
        title = f' BOTONERA EVENTO — {estado}{conn_tag} '
        pad   = (w - 2 - len(title)) // 2
        W(row, 0, '│' + ' ' * pad + title + ' ' * (w - 2 - pad - len(title)) + '│',
          COL_BORDER | curses.A_BOLD);                        row += 1
        divider(row);                                          row += 1

        # Now playing
        track   = status.get('track') or '---'
        elapsed = status.get('elapsed', 0)
        vol     = status.get('volume', 70)
        ela_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
        row_fill(row, f"♪  {track}   [{ela_str}]   Vol: {vol}%", COL_NOW)
        row += 1
        divider(row);  row += 1

        # Categories
        for i, cat in enumerate(cats[:9]):
            prefix = '►' if i == ci else ' '
            label  = f"{prefix}[{i+1}] {cat['name']}  ({cat.get('track_count', 0)} tracks)"
            attr   = COL_SEL if i == ci else 0
            row_fill(row, label, attr)
            row += 1
            if row >= h - 7:
                break

        divider(row);  row += 1

        # Track list (up to 5 visible)
        visible = min(5, h - row - 5)
        start   = max(0, ti - visible // 2)
        for i in range(start, min(len(trks), start + visible)):
            prefix = '►' if i == ti else '  '
            attr   = COL_NOW | curses.A_BOLD if i == ti else 0
            row_fill(row, f"{prefix} {trks[i]}", attr)
            row += 1
            if row >= h - 5:
                break

        if row < h - 5:
            divider(row);  row += 1

        # Message bar
        if msg and row < h - 4:
            row_fill(row, msg, COL_MSG);  row += 1

        # Help line
        if row < h - 3:
            divider(row);  row += 1
        if row < h - 2:
            row_fill(row, "1-9=cat  SPC=play/pausa  ENTER=play  ↑↓=track  ←→=cat  V/B=vol  ESC=stop  r=reload",
                     COL_HELP)
            row += 1

        # Footer
        if row < h - 1:
            W(row, 0, '└' + '─' * (w - 2) + '┘', COL_BORDER)

        self.scr.refresh()

    # ── Main loop ─────────────────────────────────────────────────────────

    def run(self):
        curses.curs_set(0)
        self.scr.nodelay(True)
        self.scr.keypad(True)
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()

        frame_dur = 1.0 / UI_FPS
        while self.running:
            key = self.scr.getch()
            if key != -1:
                self._handle_key(key)
            self._draw()
            time.sleep(frame_dur)


def main():
    parser = argparse.ArgumentParser(description="Botonera CLI")
    parser.add_argument('--server',  default='http://localhost:5000')
    parser.add_argument('--log-dir', default='./logs')
    args = parser.parse_args()

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(Path(args.log_dir) / "botonera_cli.log"),
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    def run_ui(stdscr):
        ui = BotoneraUI(args.server, stdscr)
        ui.run()

    try:
        curses.wrapper(run_ui)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
