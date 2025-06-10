import os
import sys
import logging
import time
from pydub import AudioSegment

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database.db_handler import DatabaseHandler
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from shazam_core.audio_utils import load_audio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
DB_PATH = "robust_test.db"
FULL_SONG_PATH = "test_music.mp3"
SNIPPET_DURATION_MS = 7 * 1000  # 7-second snippets, similar to the frontend
# Define multiple start times to test (in seconds)
SNIPPET_START_TIMES_SEC = [15,3,9,89, 45, 70, 110] 

def setup_clean_database():
    logger.info("--- Step 1: Setting up clean database ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return DatabaseHandler(db_path=DB_PATH)

def ingest_full_song(db_handler, fingerprinter):
    logger.info("--- Step 2: Ingesting full song into database ---")
    if not os.path.exists(FULL_SONG_PATH):
        logger.error(f"FATAL: Full song not found at '{FULL_SONG_PATH}'.")
        return None
    
    song_id = db_handler.add_song(title="Robustness Test Song", artist="Test Artist", source_type="local", source_id=FULL_SONG_PATH)
    audio_data, _ = load_audio(FULL_SONG_PATH, target_sample_rate=fingerprinter.sample_rate)
    fingerprints = fingerprinter.generate_fingerprints(audio_data, song_id=song_id)
    db_handler.add_fingerprints(song_id, fingerprints)
    logger.info(f"✅ Stored {len(fingerprints)} fingerprints for Song ID {song_id}.")
    return song_id

def run_matching_tests(db_handler, fingerprinter, expected_song_id):
    logger.info("--- Step 3: Running matching tests for multiple snippets ---")
    full_song_audio = AudioSegment.from_file(FULL_SONG_PATH)
    all_tests_passed = True
    
    for start_sec in SNIPPET_START_TIMES_SEC:
        start_ms = start_sec * 1000
        snippet_path = f"temp_snippet_{start_sec}s.mp3"
        
        logger.info(f"\n--- Testing snippet starting at {start_sec} seconds ---")
        
        # Create snippet
        snippet = full_song_audio[start_ms : start_ms + SNIPPET_DURATION_MS]
        snippet.export(snippet_path, format="mp3")
        
        # Match snippet
        matcher = FingerprintMatcher(db_handler, fingerprinter)
        snippet_audio, _ = load_audio(snippet_path, target_sample_rate=fingerprinter.sample_rate)
        query_fingerprints = fingerprinter.generate_fingerprints(snippet_audio)
        results = matcher.match_fingerprints(query_fingerprints)
        
        # Analyze result
        if results and results[0]['song_id'] == expected_song_id:
            score = results[0]['score']
            offset = results[0]['offset_seconds']
            logger.info(f"✅ PASSED: Correctly matched Song ID {expected_song_id} with score {score}. (Offset: {offset:.2f}s)")
        else:
            logger.error(f"❌ FAILED: Did not match correctly for snippet at {start_sec}s. Results: {results}")
            all_tests_passed = False
            
        # Clean up snippet file
        os.remove(snippet_path)
        
    return all_tests_passed

def cleanup():
    logger.info("--- Step 4: Cleaning up database ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    logger.info("✅ Cleanup complete.")

if __name__ == "__main__":
    fingerprinter_instance = Fingerprinter()
    
    db = setup_clean_database()
    song_id = ingest_full_song(db, fingerprinter_instance)
    
    if song_id:
        success = run_matching_tests(db, fingerprinter_instance, song_id)
        print("\n-------------------------------------------")
        if success:
            print("🎉🎉🎉 ALL ROBUSTNESS TESTS PASSED! 🎉🎉🎉")
        else:
            print("🚨 SOME ROBUSTNESS TESTS FAILED. 🚨")
        print("-------------------------------------------")

    cleanup()