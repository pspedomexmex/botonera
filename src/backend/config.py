"""Category discovery, config loading, and file path validation."""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.flac'}


@dataclass
class CategoryConfig:
    name: str
    folder: str
    hotkey: str = ""
    color: str = "white"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    allowed_ips: list = field(default_factory=lambda: ["127.0.0.1", "192.168.1.*", "192.168.0.*", "10.0.*.*"])


@dataclass
class BotoneraConfig:
    categories: list = field(default_factory=list)
    server: ServerConfig = field(default_factory=ServerConfig)
    music_dir: str = "./music"


def load_config(config_path: Optional[str] = None, music_dir: Optional[str] = None) -> BotoneraConfig:
    config = BotoneraConfig()

    if music_dir:
        config.music_dir = music_dir

    if not config_path or not os.path.exists(config_path):
        return config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'music_dir' in data and not music_dir:
            config.music_dir = data['music_dir']

        if 'server' in data:
            s = data['server']
            config.server = ServerConfig(
                host=s.get('host', '0.0.0.0'),
                port=s.get('port', 5000),
                allowed_ips=s.get('allowed_ips', config.server.allowed_ips),
            )

        if 'categories' in data:
            for i, cat in enumerate(data['categories']):
                config.categories.append(CategoryConfig(
                    name=cat.get('name', cat.get('folder', f'Cat{i+1}')),
                    folder=cat.get('folder', ''),
                    hotkey=cat.get('hotkey', str(i + 1) if i < 9 else ''),
                    color=cat.get('color', 'white'),
                ))

        logger.info(f"Config loaded: {config_path} ({len(config.categories)} categories)")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Config parse error ({e}), using defaults")

    return config


def discover_categories(music_dir: str, existing: list) -> list:
    """Auto-discover subfolders as categories; append after pre-configured ones."""
    music_path = Path(music_dir)
    if not music_path.exists():
        logger.warning(f"Music dir not found: {music_dir}")
        return list(existing)

    configured_folders = {c.folder.lower() for c in existing}
    result = list(existing)
    next_hotkey = len(result) + 1

    for folder in sorted(music_path.iterdir()):
        if not folder.is_dir() or folder.name.lower() in configured_folders:
            continue
        has_audio = any(
            f.suffix.lower() in ALLOWED_EXTENSIONS
            for f in folder.rglob('*')
            if f.is_file()
        )
        if not has_audio:
            continue
        result.append(CategoryConfig(
            name=folder.name,
            folder=folder.name,
            hotkey=str(next_hotkey) if next_hotkey <= 9 else '',
            color='white',
        ))
        next_hotkey += 1

    return result


def get_tracks(music_dir: str, folder: str) -> list:
    folder_path = Path(music_dir) / folder
    if not folder_path.exists():
        return []
    return sorted(
        f.name for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
    )


def validate_file_path(music_dir: str, folder: str, filename: str) -> Optional[Path]:
    """
    Validate file path against traversal attacks and extension whitelist.
    Supports symlinks inside music_dir pointing to files anywhere on disk
    (symlinks are safe because their location is admin-controlled).
    """
    import os as _os
    try:
        music_abs = _os.path.abspath(music_dir)
        # Detect traversal using normalized unresolved path (ignores symlink targets)
        candidate_str = _os.path.normpath(_os.path.join(music_abs, folder, filename))
        if not (candidate_str + _os.sep).startswith(music_abs + _os.sep):
            logger.warning(f"Path traversal attempt blocked: folder={folder!r} file={filename!r}")
            return None

        candidate = Path(candidate_str)
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.warning(f"Blocked extension: {candidate.suffix}")
            return None

        # Resolve symlink to get the real file for the audio player
        real = Path(_os.path.realpath(str(candidate)))
        if not real.exists():
            return None

        return real
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return None
