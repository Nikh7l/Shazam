"""Unit tests for audio fingerprinting and matching logic in `backend.shazam_core`."""
import os
import sys
import pytest
from pathlib import Path

# Add the backend directory to the Python path

# Now import from the shazam_core package
from backend.shazam_core.audio_utils import load_audio
from backend.shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from backend.database.db_handler import DatabaseHandler

# Test audio file 
SAMPLE_AUDIO_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample.wav')
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_fingerprints.db')

@pytest.fixture
def sample_audio():
    """Load sample audio for testing."""
    if not os.path.exists(SAMPLE_AUDIO_FILE):
        pytest.skip(f"Sample audio file not found: {SAMPLE_AUDIO_FILE}")
    
    audio_data, sample_rate = load_audio(SAMPLE_AUDIO_FILE)
    return audio_data, sample_rate

@pytest.fixture
def db_handler():
    """Set up a test database."""
    # Make sure the test database doesn't exist
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # Create a test database
    db = DatabaseHandler(db_path=TEST_DB_PATH)
    
    # Add a test song
    song_id = db.add_song(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        youtube_id="test123"
    )
    
    yield db
    
    # Clean up - just remove the test database file, not the directory
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_fingerprinter_initialization():
    """Test that the Fingerprinter initializes with default parameters."""
    fingerprinter = Fingerprinter()
    assert fingerprinter.sample_rate == 11025
    assert fingerprinter.window_size == 2048
    assert fingerprinter.hop_size == 512
    assert fingerprinter.fan_value == 15

def test_generate_fingerprints(sample_audio):
    """Test generating fingerprints from audio."""
    audio_data, sample_rate = sample_audio
    fingerprinter = Fingerprinter(sample_rate=sample_rate)
    
    # Generate fingerprints
    fingerprints = fingerprinter.generate_fingerprints(audio_data, song_id=1)
    
    # Check that we got some fingerprints
    assert len(fingerprints) > 0
    
    # Check fingerprint structure
    fp = fingerprints[0]
    assert hasattr(fp, 'hash')
    assert hasattr(fp, 'song_id')
    assert hasattr(fp, 'offset')
    assert hasattr(fp, 'timestamp')

def test_fingerprint_matching(sample_audio, db_handler):
    """Test matching fingerprints against a database."""
    audio_data, sample_rate = sample_audio
    fingerprinter = Fingerprinter(sample_rate=sample_rate)

    # Generate fingerprints for the test song
    song_id = 1  # Should match the fixture
    fingerprints = fingerprinter.generate_fingerprints(audio_data, song_id=song_id)
    
    print(f"Generated {len(fingerprints)} fingerprints for the test song")

    # Store fingerprints in the database
    db_handler.store_fingerprints(song_id, [(fp.hash, fp.offset) for fp in fingerprints])
    
    # Verify fingerprints were stored
    with db_handler._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fingerprints WHERE song_id = ?", (song_id,))
        count = cursor.fetchone()[0]
        print(f"Stored {count} fingerprints in the database")

    # Create a matcher with the test database
    matcher = FingerprintMatcher(db_handler=db_handler)

    # Try to match the same audio
    query_fingerprints = fingerprinter.generate_fingerprints(audio_data, song_id=0)
    print(f"Generated {len(query_fingerprints)} query fingerprints")
    
    # Get matching hashes from the database for debugging
    hashes = [f.hash for f in query_fingerprints]
    with db_handler._get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(hashes))
        cursor.execute(f"SELECT COUNT(DISTINCT hash) FROM fingerprints WHERE hash IN ({placeholders})", hashes)
        matching_hashes = cursor.fetchone()[0]
        print(f"Found {matching_hashes} matching hashes in the database")
    
    matches = matcher.match_fingerprints(query_fingerprints)
    print(f"Found {len(matches)} matches")
    
    # Print debug info if no matches found
    if not matches:
        print("No matches found. Query hashes:", hashes[:10], "..." if len(hashes) > 10 else "")
        with db_handler._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hash FROM fingerprints LIMIT 10")
            db_hashes = [row[0] for row in cursor.fetchall()]
            print("First 10 hashes in database:", db_hashes)

    # We should get at least one match (the test song)
    assert len(matches) > 0, "No matches found in the database"
    assert matches[0]['song_id'] == song_id

def test_time_coherence(sample_audio, db_handler):
    """Test that time coherence is properly handled in matching."""
    audio_data, sample_rate = sample_audio
    fingerprinter = Fingerprinter(sample_rate=sample_rate)
    
    # Generate fingerprints for the test song
    song_id = 1
    full_fingerprints = fingerprinter.generate_fingerprints(audio_data, song_id=song_id)
    
    # Store fingerprints in the database
    db_handler.store_fingerprints(song_id, [(fp.hash, fp.offset) for fp in full_fingerprints])
    
    # Create a matcher with the test database
    matcher = FingerprintMatcher(db_handler=db_handler)
    
    # Take a snippet of the audio (first 5 seconds)
    snippet_duration = 5  # seconds
    snippet_samples = int(snippet_duration * sample_rate)
    snippet = audio_data[:snippet_samples]
    
    # Generate fingerprints for the snippet
    query_fingerprints = fingerprinter.generate_fingerprints(snippet, song_id=0)
    
    # Match against the full song
    matches = matcher.match_fingerprints(query_fingerprints)
    
    # We should get a match with the test song
    assert len(matches) > 0
    assert matches[0]['song_id'] == song_id
    
    # The best match should have a high number of matches
    assert matches[0]['total_matches'] > 10  # Check total unique hashes matched
