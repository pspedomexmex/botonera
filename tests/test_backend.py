"""Unit tests: config parsing, category discovery, file validation."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.config import (
    ALLOWED_EXTENSIONS,
    CategoryConfig,
    discover_categories,
    get_tracks,
    load_config,
    validate_file_path,
)


# ── Config loading ────────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_defaults_when_no_file(self):
        cfg = load_config()
        assert cfg.server.port == 5000
        assert cfg.server.host == "0.0.0.0"
        assert cfg.categories == []

    def test_missing_path_returns_defaults(self):
        cfg = load_config("/nonexistent/path.json")
        assert cfg.server.port == 5000

    def test_invalid_json_returns_defaults(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{{not valid json{{")
        cfg = load_config(str(bad))
        assert cfg.server.port == 5000

    def test_full_config(self, tmp_path):
        data = {
            "categories": [
                {"name": "FX",    "folder": "fx_folder",  "hotkey": "1", "color": "red"},
                {"name": "Music", "folder": "music_folder", "hotkey": "2", "color": "green"},
            ],
            "server": {"host": "127.0.0.1", "port": 8080, "allowed_ips": ["192.168.2.*"]},
        }
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps(data))

        cfg = load_config(str(cfg_file))
        assert cfg.server.port == 8080
        assert cfg.server.host == "127.0.0.1"
        assert len(cfg.categories) == 2
        assert cfg.categories[0].name == "FX"
        assert cfg.categories[0].hotkey == "1"
        assert cfg.categories[1].color == "green"

    def test_music_dir_override_via_arg(self, tmp_path):
        cfg = load_config(music_dir=str(tmp_path))
        assert cfg.music_dir == str(tmp_path)

    def test_music_dir_from_json(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({"music_dir": "/custom/music"}))
        cfg = load_config(str(cfg_file))
        assert cfg.music_dir == "/custom/music"

    def test_argparse_music_dir_overrides_json(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({"music_dir": "/json/music"}))
        cfg = load_config(str(cfg_file), music_dir="/arg/music")
        assert cfg.music_dir == "/arg/music"


# ── Category discovery ────────────────────────────────────────────────────────

class TestDiscoverCategories:
    def _make_folder(self, base: Path, name: str, files: list[str]):
        d = base / name
        d.mkdir()
        for f in files:
            (d / f).touch()
        return d

    def test_discovers_folders_with_audio(self, tmp_path):
        self._make_folder(tmp_path, "Efectos", ["a.mp3", "b.wav"])
        self._make_folder(tmp_path, "Música",  ["c.ogg"])

        cats = discover_categories(str(tmp_path), [])
        names = [c.folder for c in cats]
        assert "Efectos" in names
        assert "Música" in names

    def test_skips_folders_without_audio(self, tmp_path):
        self._make_folder(tmp_path, "Docs",   ["readme.txt"])
        self._make_folder(tmp_path, "Audio",  ["track.mp3"])

        cats = discover_categories(str(tmp_path), [])
        folders = [c.folder for c in cats]
        assert "Docs" not in folders
        assert "Audio" in folders

    def test_configured_categories_come_first(self, tmp_path):
        self._make_folder(tmp_path, "Z_last", ["z.mp3"])
        self._make_folder(tmp_path, "A_first", ["a.mp3"])

        existing = [CategoryConfig(name="Z Config", folder="Z_last", hotkey="1")]
        cats = discover_categories(str(tmp_path), existing)

        assert cats[0].folder == "Z_last"
        assert cats[0].name   == "Z Config"

    def test_configured_folders_not_duplicated(self, tmp_path):
        self._make_folder(tmp_path, "FX", ["s.mp3"])
        existing = [CategoryConfig(name="Sound FX", folder="FX", hotkey="1")]

        cats = discover_categories(str(tmp_path), existing)
        fx_cats = [c for c in cats if c.folder == "FX"]
        assert len(fx_cats) == 1

    def test_hotkeys_auto_assigned(self, tmp_path):
        for name in ["Cat1", "Cat2", "Cat3"]:
            self._make_folder(tmp_path, name, ["t.mp3"])

        cats = discover_categories(str(tmp_path), [])
        hotkeys = [c.hotkey for c in cats if c.hotkey]
        assert set(hotkeys) == {'1', '2', '3'}

    def test_nonexistent_music_dir(self):
        cats = discover_categories("/nonexistent/dir", [])
        assert cats == []


# ── Track listing ─────────────────────────────────────────────────────────────

class TestGetTracks:
    def test_returns_only_audio_files(self, tmp_path):
        folder = tmp_path / "FX"
        folder.mkdir()
        for f in ["a.mp3", "b.wav", "c.ogg", "d.flac", "e.txt", "f.py"]:
            (folder / f).touch()

        tracks = get_tracks(str(tmp_path), "FX")
        assert set(tracks) == {"a.mp3", "b.wav", "c.ogg", "d.flac"}
        assert "e.txt" not in tracks

    def test_returns_sorted(self, tmp_path):
        folder = tmp_path / "FX"
        folder.mkdir()
        for f in ["c.mp3", "a.mp3", "b.mp3"]:
            (folder / f).touch()

        tracks = get_tracks(str(tmp_path), "FX")
        assert tracks == ["a.mp3", "b.mp3", "c.mp3"]

    def test_empty_folder(self, tmp_path):
        (tmp_path / "Empty").mkdir()
        assert get_tracks(str(tmp_path), "Empty") == []

    def test_nonexistent_folder(self, tmp_path):
        assert get_tracks(str(tmp_path), "ghost") == []


# ── File validation / security ────────────────────────────────────────────────

class TestValidateFilePath:
    def _setup(self, tmp_path):
        folder = tmp_path / "FX"
        folder.mkdir()
        f = folder / "sound.mp3"
        f.touch()
        return tmp_path, f

    def test_valid_file_returns_path(self, tmp_path):
        base, _ = self._setup(tmp_path)
        result = validate_file_path(str(base), "FX", "sound.mp3")
        assert result is not None
        assert result.name == "sound.mp3"

    def test_disallowed_extension(self, tmp_path):
        folder = tmp_path / "FX"
        folder.mkdir()
        (folder / "malware.exe").touch()
        assert validate_file_path(str(tmp_path), "FX", "malware.exe") is None

    def test_path_traversal_blocked(self, tmp_path):
        assert validate_file_path(str(tmp_path), "../../../etc", "passwd") is None

    def test_double_dot_in_filename(self, tmp_path):
        folder = tmp_path / "FX"
        folder.mkdir()
        assert validate_file_path(str(tmp_path), "FX", "../../secret.mp3") is None

    def test_nonexistent_file(self, tmp_path):
        (tmp_path / "FX").mkdir()
        assert validate_file_path(str(tmp_path), "FX", "ghost.mp3") is None


# ── Allowed extensions whitelist ──────────────────────────────────────────────

class TestAllowedExtensions:
    def test_permitted(self):
        for ext in ('.mp3', '.wav', '.ogg', '.flac'):
            assert ext in ALLOWED_EXTENSIONS

    def test_forbidden(self):
        for ext in ('.exe', '.py', '.sh', '.txt', '.bat'):
            assert ext not in ALLOWED_EXTENSIONS
