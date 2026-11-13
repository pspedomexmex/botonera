"""Thread-safe audio player with watchdog and memory monitor."""
import logging
import os
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil
import pygame

logger = logging.getLogger(__name__)

MEMORY_THRESHOLD_MB = 150
LOG_INTERVAL_S = 600        # 10 minutes
WATCHDOG_INTERVAL_S = 2.0


class PlayerStatus(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED  = "paused"
    ERROR   = "error"


class AudioPlayer:
    def __init__(self):
        self._lock = threading.RLock()
        self._status = PlayerStatus.STOPPED
        self._current_track: Optional[str] = None
        self._volume = 70
        self._play_start: Optional[float] = None
        self._elapsed_offset: float = 0.0
        self._shutdown = threading.Event()

        self._init_mixer()

        threading.Thread(target=self._watchdog_loop, daemon=True, name="watchdog").start()
        threading.Thread(target=self._monitor_loop,  daemon=True, name="monitor").start()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def play(self, file_path: Path, track_name: str) -> bool:
        with self._lock:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(str(file_path))
                pygame.mixer.music.set_volume(self._volume / 100.0)
                pygame.mixer.music.play()
                self._status = PlayerStatus.PLAYING
                self._current_track = track_name
                self._play_start = time.monotonic()
                self._elapsed_offset = 0.0
                logger.info(f"Play: {track_name}")
                return True
            except Exception as e:
                logger.error(f"Play error: {e}")
                self._status = PlayerStatus.ERROR
                return False

    def pause(self) -> bool:
        with self._lock:
            if self._status == PlayerStatus.PLAYING:
                pygame.mixer.music.pause()
                self._elapsed_offset = self._elapsed_unsafe()
                self._play_start = None
                self._status = PlayerStatus.PAUSED
                return True
            if self._status == PlayerStatus.PAUSED:
                pygame.mixer.music.unpause()
                self._play_start = time.monotonic()
                self._status = PlayerStatus.PLAYING
                return True
            return False

    def stop(self) -> bool:
        with self._lock:
            pygame.mixer.music.stop()
            self._reset_state()
            return True

    def set_volume(self, volume: int) -> bool:
        with self._lock:
            self._volume = max(0, min(100, volume))
            pygame.mixer.music.set_volume(self._volume / 100.0)
            return True

    def get_status(self) -> dict:
        with self._lock:
            self._sync_ended()
            return {
                "status":  self._status.value,
                "track":   self._current_track,
                "elapsed": round(self._elapsed_unsafe(), 2),
                "volume":  self._volume,
            }

    def shutdown(self):
        logger.info("AudioPlayer shutdown")
        self._shutdown.set()
        with self._lock:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _init_mixer(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self._volume / 100.0)
        logger.info("pygame mixer ready")

    def _elapsed_unsafe(self) -> float:
        if self._play_start is None:
            return self._elapsed_offset
        return self._elapsed_offset + (time.monotonic() - self._play_start)

    def _reset_state(self):
        self._status = PlayerStatus.STOPPED
        self._current_track = None
        self._play_start = None
        self._elapsed_offset = 0.0

    def _sync_ended(self):
        """Detect natural track end without blocking."""
        if self._status == PlayerStatus.PLAYING and not pygame.mixer.music.get_busy():
            self._reset_state()

    def _watchdog_loop(self):
        while not self._shutdown.wait(timeout=WATCHDOG_INTERVAL_S):
            try:
                with self._lock:
                    self._sync_ended()
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                try:
                    self._init_mixer()
                except Exception:
                    pass

    def _monitor_loop(self):
        proc = psutil.Process(os.getpid())
        while not self._shutdown.wait(timeout=LOG_INTERVAL_S):
            try:
                ram = proc.memory_info().rss / 1_048_576
                cpu = proc.cpu_percent(interval=0.1)
                level = logging.WARNING if ram > MEMORY_THRESHOLD_MB else logging.INFO
                logger.log(level, f"[MONITOR] RAM={ram:.1f}MB CPU={cpu:.1f}%")
            except Exception as e:
                logger.error(f"Monitor error: {e}")
