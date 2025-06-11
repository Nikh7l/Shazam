import pytest
import os
from backend.database.db_handler import DatabaseHandler
from backend.database.schema import create_tables # To ensure schema is created

# Use a temporary in-memory database for most tests
# For tests requiring a file, use a temporary file path
TEST_DB_FILE = 'test_temp_db_handler.db'

@pytest.fixture
def in_memory_db():
    """Fixture for an in-memory SQLite database handler."""
    db = DatabaseHandler(db_path=':memory:')
    # create_tables(db._get_connection()) # Ensure tables are created for in-memory
    # The DatabaseHandler's __init__ already calls _ensure_schema_exists, which calls create_tables
    return db

@pytest.fixture
def file_db():
    """Fixture for a file-based SQLite database handler."""
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    db = DatabaseHandler(db_path=TEST_DB_FILE)
    yield db
    # Teardown: remove the database file after tests are done
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

def test_db_handler_initialization_in_memory(in_memory_db):
    """Test that DatabaseHandler initializes correctly with an in-memory DB."""
    assert in_memory_db is not None
    # Check if tables were created (e.g., by trying to query one)
    try:
        songs = in_memory_db.get_all_songs()
        assert isinstance(songs, list)
    except Exception as e:
        pytest.fail(f"Schema might not have been created correctly: {e}")

def test_db_handler_initialization_file_db(file_db):
    """Test that DatabaseHandler initializes correctly with a file DB."""
    assert file_db is not None
    assert os.path.exists(TEST_DB_FILE)
    try:
        songs = file_db.get_all_songs()
        assert isinstance(songs, list)
    except Exception as e:
        pytest.fail(f"Schema might not have been created correctly for file DB: {e}")

def test_add_and_get_song(in_memory_db):
    """Test adding a song and retrieving it by ID and source ID."""
    db = in_memory_db
    title = "Test Song"
    artist = "Test Artist"
    album = "Test Album"
    source_type = "spotify"
    source_id = "test_spotify_id_123"
    youtube_id = "test_youtube_id_456"
    duration_ms = 300000

    song_id = db.add_song(title, artist, album, source_type, source_id, youtube_id, duration_ms)
    assert song_id is not None, "add_song should return a song ID"

    retrieved_song = db.get_song_by_id(song_id)
    assert retrieved_song is not None
    assert retrieved_song['id'] == song_id
    assert retrieved_song['title'] == title
    assert retrieved_song['artist'] == artist
    assert retrieved_song['album'] == album
    assert retrieved_song['source_type'] == source_type
    assert retrieved_song['source_id'] == source_id
    assert retrieved_song['youtube_id'] == youtube_id
    assert retrieved_song['duration_ms'] == duration_ms

    retrieved_by_source = db.get_song_by_source_id(source_type, source_id)
    assert retrieved_by_source is not None
    assert retrieved_by_source['id'] == song_id

def test_add_song_duplicate_source_id(in_memory_db):
    """Test that adding a song with a duplicate source_id returns existing song_id."""
    db = in_memory_db
    song_id1 = db.add_song("Title1", "Artist1", "Album1", "spotify", "dup_id_001", "yt1", 1000)
    song_id2 = db.add_song("Title2", "Artist2", "Album2", "spotify", "dup_id_001", "yt2", 2000)
    assert song_id1 == song_id2, "Adding song with duplicate source_id should return existing ID"

    # Verify that no new record was inserted, and details were not overwritten (or define behavior)
    # Current add_song logic returns existing ID if found, does not update.
    song = db.get_song_by_id(song_id1)
    assert song['title'] == "Title1" # Should be the original title

def test_get_all_songs(in_memory_db):
    """Test retrieving all songs."""
    db = in_memory_db
    assert db.get_all_songs() == [] # Initially empty

    db.add_song("Song A", "Artist A", "Album A", "local", "local_a")
    db.add_song("Song B", "Artist B", "Album B", "spotify", "spotify_b")

    songs = db.get_all_songs()
    assert len(songs) == 2
    titles = {s['title'] for s in songs}
    assert titles == {"Song A", "Song B"}

def test_delete_song(in_memory_db):
    """Test deleting a song."""
    db = in_memory_db
    song_id = db.add_song("Deletable Song", "Artist", "Album", "test", "del_001")
    assert db.get_song_by_id(song_id) is not None

    delete_status = db.delete_song(song_id)
    assert delete_status is True
    assert db.get_song_by_id(song_id) is None

    # Test deleting a non-existent song
    delete_non_existent = db.delete_song(99999)
    assert delete_non_existent is False

def test_store_and_get_fingerprints(in_memory_db):
    """Test storing and retrieving fingerprints."""
    db = in_memory_db
    song_id = db.add_song("FP Test Song", "FP Artist", "FP Album", "fp_source", "fp_001")

    # Fingerprints are tuples of (hash_str, offset_int)
    fingerprints_to_store = [
        ("hash1", 10), ("hash2", 20), ("hash1", 30) # hash1 appears twice
    ]
    db.store_fingerprints(song_id, fingerprints_to_store)

    # Test get_fingerprints_by_song_id
    retrieved_by_song = db.get_fingerprints_by_song_id(song_id)
    assert len(retrieved_by_song) == 3
    # Convert to set of tuples for easier comparison as order might not be guaranteed
    assert set(retrieved_by_song) == {("hash1", 10, song_id), ("hash2", 20, song_id), ("hash1", 30, song_id)}

    # Test get_fingerprints_by_hashes
    hashes_to_query = ["hash1", "hash3"] # hash3 does not exist
    retrieved_by_hash = db.get_fingerprints_by_hashes(hashes_to_query)
    assert len(retrieved_by_hash) == 2 # Two entries for hash1
    # Retrieved items are dicts: {'hash': str, 'offset': int, 'song_id': int}
    retrieved_hashes_set = set()
    for fp in retrieved_by_hash:
        assert fp['song_id'] == song_id
        retrieved_hashes_set.add(fp['hash'])
    assert "hash1" in retrieved_hashes_set
    assert "hash3" not in retrieved_hashes_set
    assert len({(item['hash'], item['offset']) for item in retrieved_by_hash}) == 2 # (hash1,10), (hash1,30)

    # Test get_fingerprints_by_hashes with empty list
    assert db.get_fingerprints_by_hashes([]) == []

def test_store_fingerprints_empty(in_memory_db):
    """Test storing an empty list of fingerprints."""
    db = in_memory_db
    song_id = db.add_song("Empty FP Song", "Artist", "Album", "test", "empty_fp_001")
    db.store_fingerprints(song_id, []) # Should not raise an error
    assert db.get_fingerprints_by_song_id(song_id) == []

def test_get_non_existent_song(in_memory_db):
    """Test getting a non-existent song."""
    db = in_memory_db
    assert db.get_song_by_id(999) is None
    assert db.get_song_by_source_id("invalid_source", "invalid_id") is None

def test_get_fingerprints_for_non_existent_song(in_memory_db):
    """Test getting fingerprints for a non-existent song_id."""
    db = in_memory_db
    assert db.get_fingerprints_by_song_id(888) == []
