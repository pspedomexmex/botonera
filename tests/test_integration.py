"""Integration tests: Flask API with mocked player."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pygame at import time so tests run without a display/SDL
_pygame_mock = MagicMock()
sys.modules.setdefault('pygame', _pygame_mock)
sys.modules.setdefault('pygame.mixer', _pygame_mock.mixer)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def music_dir(tmp_path):
    for cat in ("Efectos", "Música"):
        d = tmp_path / cat
        d.mkdir()
        for i in range(3):
            (d / f"track{i+1}.mp3").touch()
    return tmp_path


@pytest.fixture()
def client(music_dir):
    """Flask test client with mocked AudioPlayer."""
    import src.backend.app as bk
    from src.backend.config import load_config, discover_categories

    bk._config     = load_config(music_dir=str(music_dir))
    bk._categories = discover_categories(str(music_dir), [])

    mock_player = MagicMock()
    mock_player.get_status.return_value = {
        "status": "stopped", "track": None, "elapsed": 0.0, "volume": 70,
    }
    mock_player.play.return_value  = True
    mock_player.stop.return_value  = True
    mock_player.pause.return_value = True
    bk._player = mock_player

    bk.app.config['TESTING'] = True
    with bk.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealthAndStatus:
    def test_health(self, client):
        r = client.get('/api/health')
        assert r.status_code == 200
        assert r.get_json()['status'] == 'ok'

    def test_status_shape(self, client):
        r = client.get('/api/status')
        assert r.status_code == 200
        d = r.get_json()
        assert 'status' in d
        assert 'volume' in d
        assert 'elapsed' in d


class TestCategories:
    def test_categories_list(self, client):
        r = client.get('/api/categories')
        assert r.status_code == 200
        d = r.get_json()
        assert d['status'] == 'ready'
        assert len(d['categories']) == 2

    def test_category_has_required_fields(self, client):
        cats = client.get('/api/categories').get_json()['categories']
        for cat in cats:
            assert 'name'        in cat
            assert 'folder'      in cat
            assert 'track_count' in cat


class TestTracks:
    def test_get_tracks_by_category(self, client):
        r = client.get('/api/tracks?category=Efectos')
        assert r.status_code == 200
        d = r.get_json()
        assert len(d['tracks']) == 3

    def test_missing_category_param(self, client):
        r = client.get('/api/tracks')
        assert r.status_code == 400

    def test_unknown_category(self, client):
        r = client.get('/api/tracks?category=NoExiste')
        assert r.status_code == 404


class TestPlay:
    def test_play_valid_file(self, client):
        r = client.post('/api/play', json={'file': 'track1.mp3', 'category': 'Efectos'})
        assert r.status_code == 200
        assert r.get_json()['status'] == 'playing'

    def test_play_missing_file(self, client):
        r = client.post('/api/play', json={})
        assert r.status_code == 400

    def test_play_path_traversal_blocked(self, client):
        r = client.post('/api/play', json={'file': '../../etc/passwd', 'category': 'Efectos'})
        assert r.status_code == 400

    def test_play_invalid_extension(self, client):
        r = client.post('/api/play', json={'file': 'malware.exe', 'category': 'Efectos'})
        assert r.status_code == 400


class TestPauseStop:
    def test_pause(self, client):
        r = client.post('/api/pause')
        assert r.status_code == 200
        assert 'status' in r.get_json()

    def test_stop(self, client):
        r = client.post('/api/stop')
        assert r.status_code == 200
        assert r.get_json()['status'] == 'stopped'


class TestVolume:
    def test_volume_set(self, client):
        r = client.post('/api/volume', json={'volume': 50})
        assert r.status_code == 200
        assert r.get_json()['volume'] == 50

    def test_volume_clamped_high(self, client):
        r = client.post('/api/volume', json={'volume': 999})
        assert r.get_json()['volume'] == 100

    def test_volume_clamped_low(self, client):
        r = client.post('/api/volume', json={'volume': -5})
        assert r.get_json()['volume'] == 0

    def test_volume_invalid(self, client):
        r = client.post('/api/volume', json={'volume': 'loud'})
        assert r.status_code == 400
