import pytest
from unittest.mock import MagicMock, patch, mock_open
import os

from backend.services.song_ingester import SongIngester
# Assuming Fingerprint class is used for type hinting or comparison inside ingester
from backend.shazam_core.fingerprinting import Fingerprint

@pytest.fixture
def mock_db_handler():
    return MagicMock()

@pytest.fixture
def mock_spotify_client():
    return MagicMock()

@pytest.fixture
def mock_youtube_client():
    return MagicMock()

@pytest.fixture
def mock_fingerprinter():
    fp = MagicMock()
    fp.sample_rate = 11025 # Set a default sample_rate attribute
    return fp

@pytest.fixture
def song_ingester(mock_db_handler, mock_spotify_client, mock_youtube_client, mock_fingerprinter):
    # Patch os.makedirs in the context of the ingester's __init__ if it's called there
    with patch('os.makedirs') as mock_makedirs:
        ingester = SongIngester(mock_db_handler, mock_spotify_client, mock_youtube_client)
        # Replace the fingerprinter instance after __init__ with our mock
        ingester.fingerprinter = mock_fingerprinter
        return ingester

# --- Tests for _get_best_cover_url ---
def test_get_best_cover_url_empty_list(song_ingester):
    assert song_ingester._get_best_cover_url([]) == ''

def test_get_best_cover_url_present(song_ingester):
    images = [{'url': 'url1', 'width': 100, 'height': 100}, {'url': 'url2', 'width': 200, 'height': 200}]
    assert song_ingester._get_best_cover_url(images) == 'url2'

def test_get_best_cover_url_missing_dims(song_ingester):
    images = [{'url': 'url1'}, {'url': 'url2', 'width': 200, 'height': 200}]
    # It should pick url2 because url1 has 0 area due to missing width/height
    assert song_ingester._get_best_cover_url(images) == 'url2'

# --- Tests for _extract_youtube_id ---
def test_extract_youtube_id_standard(song_ingester):
    assert song_ingester._extract_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

def test_extract_youtube_id_short(song_ingester):
    assert song_ingester._extract_youtube_id('https://youtu.be/dQw4w9WgXcQ') == 'dQw4w9WgXcQ'

def test_extract_youtube_id_with_params(song_ingester):
    assert song_ingester._extract_youtube_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL...&index=2') == 'dQw4w9WgXcQ'

def test_extract_youtube_id_invalid(song_ingester):
    assert song_ingester._extract_youtube_id('not a youtube url') == ''

# --- Tests for ingest_from_spotify ---
@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_success(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client, mock_youtube_client, mock_fingerprinter):
    mock_spotify_client.get_track_metadata.return_value = {
        'id': 'spotify_id_123', 'title': 'Test Song', 'artist': 'Test Artist', 'album': 'Test Album',
        'duration_ms': 180000, 'images': [{'url': 'cover.jpg', 'width': 300, 'height': 300}],
        'release_date': '2023-01-01', 'spotify_url': 'spotify_track_url'
    }
    mock_db_handler.get_song_by_source.return_value = None # Not already in DB
    mock_youtube_client.search_videos.return_value = [{'id': 'youtube_id_789'}]
    mock_youtube_client.download_audio.return_value = ('/tmp/audio.mp3', {'title': 'YT Title', 'duration': 180})
    mock_os_exists.return_value = True # Simulate file downloaded
    mock_load_audio.return_value = (MagicMock(), 11025) # (audio_data, sample_rate)
    # Create mock Fingerprint objects
    mock_fingerprints = [Fingerprint(hash='fp1', song_id=0, offset=100, timestamp=0.1)]
    mock_fingerprinter.generate_fingerprints.return_value = mock_fingerprints
    mock_db_handler.add_song.return_value = 1 # New song_id from DB

    result = song_ingester.ingest_from_spotify('some_spotify_url')

    assert result['success'] is True
    assert result['song_id'] == 1
    assert result['status'] == 'added'
    mock_db_handler.add_song.assert_called_once()
    # Check that fingerprints were updated with song_id and stored
    assert mock_fingerprints[0].song_id == 1
    mock_db_handler.add_fingerprints.assert_called_once_with(1, mock_fingerprints)
    mock_os_remove.assert_called_once_with('/tmp/audio.mp3')

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_already_exists(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client):
    mock_spotify_client.get_track_metadata.return_value = {'id': 'spotify_id_123', 'title': 'Test Song'}
    mock_db_handler.get_song_by_source.return_value = {'id': 1, 'title': 'Test Song'} # Already in DB

    result = song_ingester.ingest_from_spotify('some_spotify_url')

    assert result['success'] is True
    assert result['song_id'] == 1
    assert result['status'] == 'already_exists'
    mock_youtube_client.search_videos.assert_not_called()
    mock_youtube_client.download_audio.assert_not_called()

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_spotify_failure(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_spotify_client):
    mock_spotify_client.get_track_metadata.return_value = None
    result = song_ingester.ingest_from_spotify('some_spotify_url')
    assert result['success'] is False
    assert 'Could not fetch track from Spotify' in result['error']

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_youtube_search_failure(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client, mock_youtube_client):
    mock_spotify_client.get_track_metadata.return_value = {'id': 'spotify_id_123', 'title': 'TS', 'artist': 'TA'}
    mock_db_handler.get_song_by_source.return_value = None
    mock_youtube_client.search_videos.return_value = [] # No YouTube results

    result = song_ingester.ingest_from_spotify('some_spotify_url')
    assert result['success'] is False
    assert 'No matching YouTube video found' in result['error']

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_download_failure(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client, mock_youtube_client):
    mock_spotify_client.get_track_metadata.return_value = {'id': 'spotify_id_123', 'title': 'TS', 'artist': 'TA'}
    mock_db_handler.get_song_by_source.return_value = None
    mock_youtube_client.search_videos.return_value = [{'id': 'youtube_id_789'}]
    mock_youtube_client.download_audio.return_value = (None, {}) # Download fails

    result = song_ingester.ingest_from_spotify('some_spotify_url')
    assert result['success'] is False
    assert 'Failed to download audio from YouTube' in result['error']

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_fingerprint_failure(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client, mock_youtube_client, mock_fingerprinter):
    mock_spotify_client.get_track_metadata.return_value = {'id': 'spotify_id_123', 'title': 'TS', 'artist': 'TA'}
    mock_db_handler.get_song_by_source.return_value = None
    mock_youtube_client.search_videos.return_value = [{'id': 'youtube_id_789'}]
    mock_youtube_client.download_audio.return_value = ('/tmp/audio.mp3', {})
    mock_os_exists.return_value = True
    mock_load_audio.return_value = (MagicMock(), 11025)
    mock_fingerprinter.generate_fingerprints.return_value = [] # Empty list = failure

    result = song_ingester.ingest_from_spotify('some_spotify_url')
    assert result['success'] is False
    assert 'Failed to generate fingerprints' in result['error']
    mock_os_remove.assert_called_once_with('/tmp/audio.mp3') # Ensure cleanup still happens

@patch('backend.services.song_ingester.load_audio')
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_spotify_db_add_failure(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_spotify_client, mock_youtube_client, mock_fingerprinter):
    mock_spotify_client.get_track_metadata.return_value = {'id': 'spotify_id_123', 'title': 'TS', 'artist': 'TA'}
    mock_db_handler.get_song_by_source.return_value = None
    mock_youtube_client.search_videos.return_value = [{'id': 'youtube_id_789'}]
    mock_youtube_client.download_audio.return_value = ('/tmp/audio.mp3', {})
    mock_os_exists.return_value = True
    mock_load_audio.return_value = (MagicMock(), 11025)
    mock_fingerprinter.generate_fingerprints.return_value = [Fingerprint(hash='fp1', song_id=0, offset=100, timestamp=0.1)]
    mock_db_handler.add_song.return_value = None # DB add_song fails

    result = song_ingester.ingest_from_spotify('some_spotify_url')
    assert result['success'] is False
    assert 'Failed to add song to the database' in result['error']
    mock_os_remove.assert_called_once_with('/tmp/audio.mp3')

# Similar tests would be needed for ingest_from_youtube
# For brevity, only one success case for ingest_from_youtube is shown here.

@patch('backend.services.song_ingester.load_audio') # Assuming Fingerprinter uses load_audio internally if path is passed
@patch('os.path.exists')
@patch('os.remove')
def test_ingest_from_youtube_success(mock_os_remove, mock_os_exists, mock_load_audio, song_ingester, mock_db_handler, mock_youtube_client, mock_fingerprinter):
    video_id = 'youtube_id_123'
    mock_db_handler.get_song_by_source.return_value = None # Not in DB
    mock_youtube_client.download_audio.return_value = ('/tmp/yt_audio.mp3', {
        'title': 'YouTube Song', 'uploader': 'YT Uploader', 'duration': 200,
        'thumbnail': 'yt_thumb.jpg'
    })
    mock_os_exists.return_value = True
    # If fingerprinter.generate_fingerprints takes a path, it might call load_audio itself.
    # If it takes audio_data, then load_audio needs to be mocked before fingerprinter call.
    # The current song_ingester.py calls: `fingerprints = self.fingerprinter.generate_fingerprints(file_path)`
    # So, Fingerprinter's generate_fingerprints method needs to handle the path, or load_audio needs to be part of its mock or this test setup.
    # For this test, let's assume Fingerprinter.generate_fingerprints directly returns fingerprints when given a path.
    mock_fingerprints_yt = [Fingerprint(hash='yt_fp1', song_id=0, offset=50, timestamp=0.05)]
    mock_fingerprinter.generate_fingerprints.return_value = mock_fingerprints_yt
    mock_db_handler.add_song.return_value = 2 # New song_id

    result = song_ingester.ingest_from_youtube(video_id)

    assert result['success'] is True
    assert result['song_id'] == 2
    assert result['status'] == 'added'
    mock_db_handler.add_song.assert_called_once()
    assert mock_fingerprints_yt[0].song_id == 2 # Check song_id propagation
    mock_db_handler.add_fingerprints.assert_called_once_with(2, mock_fingerprints_yt)
    mock_os_remove.assert_called_once_with('/tmp/yt_audio.mp3')
