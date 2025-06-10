import os
import sys
import logging
from pydub import AudioSegment

# Add project root to Python path to find our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import our project's components
from database.db_handler import DatabaseHandler
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from shazam_core.audio_utils import load_audio

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "test_local_db.db"
FULL_SONG_PATH = "test_music.mp3"
SNIPPET_PATH = "temp_snippet.mp3"
SNIPPET_START_MS = 30 * 1000  # Start snippet at 30 seconds
SNIPPET_DURATION_MS = 10 * 1000 # Make it 10 seconds long

# --- Test Functions ---

def setup_clean_database():
    """Deletes the old test database and creates a fresh one."""
    logger.info("--- Step 1: Setting up clean database ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"Removed old database: {DB_PATH}")
    
    # Initializing the handler will create the DB and schema
    db_handler = DatabaseHandler(db_path=DB_PATH)
    logger.info("✅ New database created successfully.")
    return db_handler

def ingest_full_song(db_handler, fingerprinter):
    """Takes the full song, fingerprints it, and stores it in the database."""
    logger.info("--- Step 2: Ingesting full song into database ---")
    if not os.path.exists(FULL_SONG_PATH):
        logger.error(f"FATAL: Full song not found at '{FULL_SONG_PATH}'. Please add it.")
        return None

    try:
        # Add a record for the song to the 'songs' table
        song_id = db_handler.add_song(
            title="Test Song (Local)",
            artist="Test Artist",
            source_type="local_file",
            source_id=FULL_SONG_PATH
        )
        logger.info(f"Added song to DB with ID: {song_id}")

        # Generate fingerprints for the full song
        audio_data, _ = load_audio(FULL_SONG_PATH, target_sample_rate=fingerprinter.sample_rate)
        fingerprints = fingerprinter.generate_fingerprints(audio_data)
        
        # Assign the correct song_id to each fingerprint
        for fp in fingerprints:
            fp.song_id = song_id
            
        # Store the fingerprints in the database
        db_handler.add_fingerprints(song_id, fingerprints)
        logger.info(f"✅ Stored {len(fingerprints)} fingerprints for Song ID {song_id}.")
        return song_id
    except Exception as e:
        logger.error(f"Failed to ingest song: {e}", exc_info=True)
        return None

def create_test_snippet():
    """Creates a short audio snippet from the full song."""
    logger.info("--- Step 3: Creating test snippet from full song ---")
    try:
        full_song_audio = AudioSegment.from_file(FULL_SONG_PATH)
        snippet_end_ms = SNIPPET_START_MS + SNIPPET_DURATION_MS
        
        if len(full_song_audio) < snippet_end_ms:
            logger.error("Song is too short to create a snippet at the configured time.")
            return False

        snippet = full_song_audio[SNIPPET_START_MS:snippet_end_ms]
        snippet.export(SNIPPET_PATH, format="mp3")
        logger.info(f"✅ Snippet created successfully: {SNIPPET_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to create snippet: {e}", exc_info=True)
        return False

def match_snippet(db_handler, fingerprinter, expected_song_id):
    """Matches the snippet against the database and validates the result."""
    logger.info("--- Step 4: Matching snippet against database ---")
    try:
        matcher = FingerprintMatcher(db_handler, fingerprinter)
        
        # Generate fingerprints for the query snippet
        snippet_audio, _ = load_audio(SNIPPET_PATH, target_sample_rate=fingerprinter.sample_rate)
        query_fingerprints = fingerprinter.generate_fingerprints(snippet_audio)
        logger.info(f"Generated {len(query_fingerprints)} fingerprints for the snippet.")
        
        # Perform the match
        results = matcher.match_fingerprints(query_fingerprints)
        
        # --- Analyze the Results ---
        if not results:
            logger.error("❌ MATCH FAILED: No results returned.")
            return

        best_match = results[0]
        matched_song_id = best_match['song_id']
        score = best_match['score']
        offset = best_match['offset_seconds']

        logger.info("--- MATCH RESULTS ---")
        logger.info(f"  Best Match Song ID: {matched_song_id} (Expected: {expected_song_id})")
        logger.info(f"  Score (Aligned Hashes): {score}")
        logger.info(f"  Match Time Offset: {offset:.2f} seconds")
        
        if matched_song_id == expected_song_id:
            logger.info("✅ SUCCESS: The correct song was identified!")
        else:
            logger.error(f"❌ FAILURE: The wrong song was identified! Matched ID {matched_song_id} but expected {expected_song_id}.")

    except Exception as e:
        logger.error(f"An error occurred during matching: {e}", exc_info=True)

def cleanup():
    """Removes temporary files created during the test."""
    logger.info("--- Step 5: Cleaning up temporary files ---")
    for f in [DB_PATH, SNIPPET_PATH]:
        if os.path.exists(f):
            os.remove(f)
            logger.info(f"Removed {f}")
    logger.info("✅ Cleanup complete.")


if __name__ == "__main__":
    fingerprinter_instance = Fingerprinter()
    
    # Run the full test workflow
    db_handler_instance = setup_clean_database()
    ingested_song_id = ingest_full_song(db_handler_instance, fingerprinter_instance)
    
    if ingested_song_id:
        if create_test_snippet():
            match_snippet(db_handler_instance, fingerprinter_instance, ingested_song_id)

    # Always run cleanup
    cleanup()