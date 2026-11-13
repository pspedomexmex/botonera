"""
Longevity / stress test.
Usage:
  python -m tests.stability_test --server http://localhost:5000 --duration 4h --log-interval 10m
  python -m tests.stability_test --stress          # 100 track changes in 60s
"""
import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


# ── Duration parser ───────────────────────────────────────────────────────────

def _secs(s: str) -> int:
    s = s.strip().lower()
    if s.endswith('h'):
        return int(s[:-1]) * 3600
    if s.endswith('m'):
        return int(s[:-1]) * 60
    if s.endswith('s'):
        return int(s[:-1])
    return int(s)


# ── Core test class ───────────────────────────────────────────────────────────

class StabilityTest:
    def __init__(self, server: str, duration_s: int, log_interval_s: int):
        self.server        = server.rstrip('/')
        self.duration_s    = duration_s
        self.log_interval_s = log_interval_s
        self.plays         = 0
        self.errors        = 0
        self.tracks: list[dict] = []

    def _api(self, method: str, path: str, **kw):
        try:
            fn = getattr(requests, method)
            r  = fn(f"{self.server}{path}", timeout=5, **kw)
            return r.json()
        except Exception as e:
            self.errors += 1
            logger.error(f"API {method.upper()} {path}: {e}")
            return None

    def _discover(self) -> bool:
        cats = self._api('get', '/api/categories')
        if not cats:
            logger.error("Cannot reach server")
            return False
        for cat in cats.get('categories', []):
            trks = self._api('get', '/api/tracks', params={'category': cat['name']})
            if trks:
                for t in trks.get('tracks', []):
                    self.tracks.append({'file': t, 'category': cat['folder']})
        logger.info(f"Discovered {len(self.tracks)} tracks across {len(cats['categories'])} categories")
        return bool(self.tracks)

    def _play_next(self):
        if not self.tracks:
            return
        track = self.tracks[self.plays % len(self.tracks)]
        t0    = time.monotonic()
        result = self._api('post', '/api/play', json=track)
        latency = (time.monotonic() - t0) * 1000
        if result and result.get('status') == 'playing':
            self.plays += 1
            if latency > 500:
                logger.warning(f"HIGH LATENCY: {latency:.0f}ms for {track['file']}")
            else:
                logger.debug(f"Play #{self.plays} {track['file']} ({latency:.0f}ms)")
        else:
            self.errors += 1

    def _log_state(self, elapsed_s: float):
        status = self._api('get', '/api/status')
        mem_info = ""
        try:
            import psutil, os
            p = psutil.Process(os.getpid())
            mem_info = f"test-RAM={p.memory_info().rss/1_048_576:.1f}MB"
        except Exception:
            pass
        logger.info(
            f"[CHECKPOINT] elapsed={elapsed_s/3600:.2f}h "
            f"plays={self.plays} errors={self.errors} "
            f"server_status={status.get('status') if status else 'N/A'} "
            f"{mem_info}"
        )

    # ── Longevity mode ────────────────────────────────────────────────────

    def run_longevity(self) -> bool:
        PLAY_INTERVAL_S = 10
        start     = time.monotonic()
        end       = start + self.duration_s
        last_log  = start
        last_play = start - PLAY_INTERVAL_S

        logger.info(f"Longevity test: {self.duration_s/3600:.1f}h target")

        while time.monotonic() < end:
            now = time.monotonic()
            if now - last_play >= PLAY_INTERVAL_S:
                self._play_next()
                last_play = now
            if now - last_log >= self.log_interval_s:
                self._log_state(now - start)
                last_log = now
            time.sleep(0.5)

        self._log_state(time.monotonic() - start)
        success = self.errors == 0
        logger.info(f"Result: {'PASS' if success else 'FAIL'} | errors={self.errors}")
        return success

    # ── Stress mode ───────────────────────────────────────────────────────

    def run_stress(self, n_plays: int = 100, window_s: int = 60) -> bool:
        logger.info(f"Stress test: {n_plays} plays in {window_s}s")
        start = time.monotonic()
        for i in range(n_plays):
            self._play_next()
            elapsed = time.monotonic() - start
            if i % 10 == 0:
                logger.info(f"  {i}/{n_plays} plays, elapsed={elapsed:.1f}s, errors={self.errors}")
        total = time.monotonic() - start
        logger.info(
            f"Stress done: {n_plays} plays in {total:.1f}s "
            f"({n_plays/total:.1f} plays/s) errors={self.errors}"
        )
        return self.errors == 0 and total <= window_s


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Botonera Stability Test")
    parser.add_argument('--server',       default='http://localhost:5000')
    parser.add_argument('--duration',     default='4h')
    parser.add_argument('--log-interval', default='10m')
    parser.add_argument('--log-dir',      default='./logs')
    parser.add_argument('--stress',       action='store_true',
                        help="Run stress test (100 plays/60s) instead of longevity")
    args = parser.parse_args()

    Path(args.log_dir).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f"{args.log_dir}/stability_{stamp}.log"),
            logging.StreamHandler(),
        ],
    )

    test = StabilityTest(
        server       = args.server,
        duration_s   = _secs(args.duration),
        log_interval_s = _secs(args.log_interval),
    )

    if not test._discover():
        sys.exit(2)

    if args.stress:
        ok = test.run_stress()
    else:
        ok = test.run_longevity()

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
