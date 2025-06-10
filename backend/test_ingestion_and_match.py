import os
import sys
import logging
import time
from unittest.mock import patch, DEFAULT # <-- Import DEFAULT
from pydub import AudioSegment # For creating audio clips

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from database.db_handler import DatabaseHandler
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from shazam_core.audio_utils import load_audio
from services.song_ingester import SongIngester
from api_clients.spotify_client import SpotifyClient
from api_clients.youtube_client import YouTubeClient
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "ingestion_test.db"
DOWNLOADS_DIR = "test_song_downloads" # Directory to store all downloaded songs for the test

SONG_URLS_TO_INGEST = [
    "https://open.spotify.com/track/2oenSXLDbWVaaL7QjSGYj5", # Original test song
    "https://open.spotify.com/track/4pqwGuGu34g8KtfN8LDGZm?si=b3180b3d61084018", # New song 1
    "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b", # New song 2
    "https://open.spotify.com/track/6UelLqGlWMcVH1E5c4H7lY", # New song 3
    "https://open.spotify.com/track/4Dvkj6JhhA12EX05fT7y2e", # New song 4
    "https://open.spotify.com/track/3AJwUDP919kvQ9QcozQPxg"  # New song 5
]

# Let's pick the first song as the one we'll make clips from for detailed testing (though new logic tests all)
TARGET_SONG_FOR_CLIPPING_URL = SONG_URLS_TO_INGEST[0]

# Define durations and start offsets for comprehensive clip testing
CLIP_DURATIONS_TO_TEST = [3, 4, 5, 6, 7, 8, 10, 12, 15, 20] # seconds
CLIP_START_OFFSETS_PERCENTAGES = [0.1, 0.3, 0.5, 0.7] # Percentage of song duration to start clip
MIN_MATCH_SCORE_THRESHOLD = 5 # Lower threshold for short clips to see if correct song is ID'd

def setup_clean_database():
    logger.info("--- Step 1: Setting up clean database ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return DatabaseHandler(db_path=DB_PATH)

# Change the signature and logic
def ingest_from_spotify_and_save(db_handler, ingester, spotify_url, song_index):
    logger.info(f"--- Ingesting song {song_index + 1}: {spotify_url} ---")
    
    # Define a unique path for this song's download
    downloaded_song_path = os.path.join(DOWNLOADS_DIR, f"downloaded_song_{song_index}.mp3")

    with patch('services.song_ingester.os.remove') as mock_os_remove:
        def save_instead_of_delete(path):
            logger.info(f"-> Mocking os.remove: Renaming {path} to {downloaded_song_path}")
            if os.path.exists(downloaded_song_path):
                # Use the real os.remove if we need to clean up an old version of this specific file
                # This requires careful handling of the mock or direct call.
                # For simplicity, ensure DOWNLOADS_DIR is clean before tests.
                pass 
            os.rename(path, downloaded_song_path)

        mock_os_remove.side_effect = save_instead_of_delete
        result = ingester.ingest_from_spotify(spotify_url)
    
    if result and result.get("success"):
        logger.info(f"✅ Successfully ingested song. ID: {result['song_id']}, Path: {downloaded_song_path}")
        # Return song_id and its path
        return result['song_id'], downloaded_song_path, result.get('title', 'Unknown Title') 
    else:
        logger.error(f"❌ FAILED to ingest song {spotify_url}. Error: {result.get('error') if result else 'Unknown'}")
        return None, None, None
        
# The rest of the script remains the same.

def test_partial_clips_match(
    db_handler, 
    fingerprinter_instance, 
    ingested_songs: dict, # Dict of {song_id: {"path": "...", "title": "..."}}
    clip_durations: list,
    start_offset_percentages: list,
    min_match_score_threshold: int
):
    logger.info("\n--- Starting Partial Clip Matching Tests ---")
    matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter_instance)
    
    overall_success = True
    min_time_results = {}

    for expected_song_id, song_data in ingested_songs.items():
        full_audio_path = song_data["path"]
        song_title = song_data["title"]
        logger.info(f"\n-- Testing clips for song: '{song_title}' (ID: {expected_song_id}) --")
        min_time_results[expected_song_id] = {"title": song_title, "min_duration_for_match": float('inf'), "best_score_at_min_duration": 0}
        
        if not os.path.exists(full_audio_path):
            logger.error(f"  SKIP: Full audio file not found for '{song_title}': {full_audio_path}")
            overall_success = False
            continue

        try:
            full_audio = AudioSegment.from_file(full_audio_path)
            full_duration_ms = len(full_audio)
            full_duration_s = full_duration_ms / 1000.0
        except Exception as e:
            logger.error(f"  SKIP: Could not load audio file '{full_audio_path}'. Error: {e}")
            overall_success = False
            continue

        found_match_for_song = False
        for clip_duration_s in sorted(clip_durations): # Test shorter durations first
            if found_match_for_song and clip_duration_s >= min_time_results[expected_song_id]["min_duration_for_match"]:
                 # Already found a match with this or shorter duration for this song, can optimize by skipping longer ones if only min_time is needed
                 # For comprehensive testing, we might want to continue. For now, let's be comprehensive.
                 pass 

            logger.info(f"  -- Testing with clip duration: {clip_duration_s}s --")
            if clip_duration_s > full_duration_s:
                logger.info(f"    SKIP: Clip duration {clip_duration_s}s exceeds song duration {full_duration_s:.2f}s.")
                continue

            for start_percentage in start_offset_percentages:
                start_time_s = full_duration_s * start_percentage
                
                if start_time_s + clip_duration_s > full_duration_s:
                    start_time_s = max(0, full_duration_s - clip_duration_s) # Adjust start time
                
                start_time_ms = int(start_time_s * 1000)
                end_time_ms = start_time_ms + int(clip_duration_s * 1000)
                
                # Ensure end_time_ms does not exceed full_duration_ms
                end_time_ms = min(end_time_ms, full_duration_ms)
                # Ensure clip has a minimum length (e.g. 1s) after adjustment
                if (end_time_ms - start_time_ms) < 1000:
                    logger.info(f"    SKIP: Adjusted clip for {song_title} is too short ({end_time_ms - start_time_ms}ms). Start: {start_time_s:.2f}s, Duration: {clip_duration_s}s.")
                    continue

                clip_audio = full_audio[start_time_ms:end_time_ms]
                
                temp_clip_dir = os.path.join(DOWNLOADS_DIR, "temp_clips")
                os.makedirs(temp_clip_dir, exist_ok=True)
                clip_file_name = f"clip_song{expected_song_id}_dur{clip_duration_s}s_start{start_time_s:.1f}s.mp3"
                temp_clip_path = os.path.join(temp_clip_dir, clip_file_name)

                try:
                    clip_audio.export(temp_clip_path, format="mp3")
                except Exception as e:
                    logger.error(f"    ERROR: Failed to export clip {temp_clip_path}. Error: {e}")
                    overall_success = False
                    continue
                
                logger.info(f"    Matching clip: {clip_file_name} (Song: '{song_title}')")
                results = matcher.match_file(temp_clip_path)

                if not results:
                    logger.info(f"    - NO MATCH for {clip_file_name} (Expected ID: {expected_song_id})")
                else:
                    best_match = results[0]
                    matched_song_id = best_match['song_id']
                    score = best_match['score']
                    
                    if matched_song_id == expected_song_id and score >= min_match_score_threshold:
                        logger.info(f"    ✅ CORRECT MATCH: ID {matched_song_id} (Score: {score}) for {clip_file_name}")
                        if clip_duration_s < min_time_results[expected_song_id]["min_duration_for_match"]:
                            min_time_results[expected_song_id]["min_duration_for_match"] = clip_duration_s
                            min_time_results[expected_song_id]["best_score_at_min_duration"] = score
                        elif clip_duration_s == min_time_results[expected_song_id]["min_duration_for_match"]:
                            min_time_results[expected_song_id]["best_score_at_min_duration"] = max(score, min_time_results[expected_song_id]["best_score_at_min_duration"])
                        found_match_for_song = True # Mark that we found at least one good match for this song
                    elif matched_song_id == expected_song_id:
                        logger.info(f"    - CORRECT SONG, LOW SCORE: ID {matched_song_id} (Score: {score} < {min_match_score_threshold}) for {clip_file_name}")
                    else:
                        logger.info(f"    ❌ WRONG SONG: Matched ID {matched_song_id} (Score: {score}), Expected ID {expected_song_id} for {clip_file_name}")
                        # If a wrong song is identified with high confidence, that's a concern.
                        if score >= min_match_score_threshold:
                             overall_success = False # Treat confident wrong match as failure
                
                if os.path.exists(temp_clip_path):
                    os.remove(temp_clip_path)
        
        if os.path.exists(temp_clip_dir) and not os.listdir(temp_clip_dir):
            try:
                os.rmdir(temp_clip_dir)
            except OSError as e:
                logger.warning(f"Could not remove temp_clips dir {temp_clip_dir}: {e}")

    logger.info("\n--- Summary of Minimum Durations for Correct Match (Score >= {min_match_score_threshold}) ---")
    for song_id, data in min_time_results.items():
        if data['min_duration_for_match'] != float('inf'):
            logger.info(f"  Song: '{data['title']}' (ID: {song_id}) - Min Duration: {data['min_duration_for_match']}s (Score: {data['best_score_at_min_duration']})")
        else:
            logger.info(f"  Song: '{data['title']}' (ID: {song_id}) - No confident match found with tested clips.")
            overall_success = False # If any song didn't get a match, mark as not fully successful

    return overall_success

def test_local_file_match(db_handler, fingerprinter, expected_song_id, downloaded_song_path, song_title="Unknown Song"):
    logger.info(f"--- Matching FULL downloaded file for '{song_title}' (ID: {expected_song_id}) ---")
    logger.info(f"--- Using file: {downloaded_song_path} ---")
    # ... (rest of the function remains similar, but uses the passed downloaded_song_path)
    # The assertion for score > 10 might be too low for a full match.
    # Consider increasing it or making it a parameter.
    # For now, let's keep it to ensure basic functionality.
    if not os.path.exists(downloaded_song_path): # Use the parameter
        logger.error(f"FATAL: Test file '{downloaded_song_path}' does not exist.")
        return False
        
    matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter) # Corrected db_handler
    logger.info(f"Attempting to match file: {downloaded_song_path}")
    results = matcher.match_file(downloaded_song_path) # Use the parameter
    
    if not results:
        logger.error("❌ MATCH FAILED: No results returned.")
        return False

    best_match = results[0]
    matched_song_id = best_match['song_id']
    score = best_match['score']

    logger.info("--- LOCAL MATCH RESULTS ---")
    logger.info(f"  Best Match Song ID: {matched_song_id} (Expected: {expected_song_id})")
    logger.info(f"  Score (Aligned Hashes): {score}")
    
    if matched_song_id == expected_song_id and score > 10:
        logger.info("✅ SUCCESS: The local file match worked perfectly as expected.")
        return True
    else:
        logger.error(f"❌ FAILURE: Local file match failed. Matched ID: {matched_song_id}, Score: {score}")
        return False

def cleanup(ingested_song_data_dict): # Pass the dictionary of song paths
    logger.info("--- Step 4: Cleaning up temporary files ---")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"Removed {DB_PATH}")
    
    # Remove all downloaded song files
    if os.path.exists(DOWNLOADS_DIR):
        for filename in os.listdir(DOWNLOADS_DIR):
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    logger.info(f"Removed {file_path}")
            except Exception as e:
                logger.error(f'Failed to delete {file_path}. Reason: {e}')
        # Optionally remove the directory itself if empty
        if not os.listdir(DOWNLOADS_DIR):
            os.rmdir(DOWNLOADS_DIR)
            logger.info(f"Removed directory {DOWNLOADS_DIR}")
        else:
            logger.info(f"Directory {DOWNLOADS_DIR} not empty, not removed.")

    logger.info("✅ Cleanup complete.")


if __name__ == "__main__":
    # Ensure DOWNLOADS_DIR exists and is empty
    if os.path.exists(DOWNLOADS_DIR):
        for filename in os.listdir(DOWNLOADS_DIR):
            os.remove(os.path.join(DOWNLOADS_DIR, filename)) # Clear out old files
    else:
        os.makedirs(DOWNLOADS_DIR) # Create if it doesn't exist

    db = setup_clean_database()
    spotify_client = SpotifyClient()
    youtube_client = YouTubeClient()
    ingester_instance = SongIngester(db, spotify_client, youtube_client)
    fingerprinter_instance = Fingerprinter()
    
    ingested_song_data = {} # To store {song_id: {"path": "...", "title": "..."}}
    target_song_id_for_clipping = None
    target_song_full_path_for_clipping = None
    target_song_title_for_clipping = None

    logger.info("--- Starting Batch Song Ingestion ---")
    for i, url in enumerate(SONG_URLS_TO_INGEST):
        song_id, file_path, song_title = ingest_from_spotify_and_save(db, ingester_instance, url, i)
        if song_id and file_path:
            ingested_song_data[song_id] = {"path": file_path, "title": song_title}
            if url == TARGET_SONG_FOR_CLIPPING_URL:
                target_song_id_for_clipping = song_id
                target_song_full_path_for_clipping = file_path
                target_song_title_for_clipping = song_title
        else:
            logger.error(f"Failed to ingest and save song: {url}")
    
    if not ingested_song_data:
        logger.error("No songs were successfully ingested. Aborting tests.")
        cleanup(ingested_song_data) # Pass the (empty) dict
        sys.exit(1)

    logger.info("--- Batch Song Ingestion Complete ---")
    logger.info(f"Ingested data: {ingested_song_data}")

    # Test full match for all ingested songs
    if target_song_id_for_clipping and target_song_full_path_for_clipping:
        logger.info(f"\n--- Testing Full Match for Target Song for Clipping ---")
        test_local_file_match(
            db, 
            fingerprinter_instance, 
            target_song_id_for_clipping, 
            target_song_full_path_for_clipping,
            target_song_title_for_clipping
        )
    else:
        logger.warning("Target song for clipping was not ingested successfully. Skipping its full match test.")

    logger.info("\n--- Initiating Partial Clip Matching Tests for ALL Ingested Songs ---")
    if ingested_song_data:
        partial_match_success = test_partial_clips_match(
            db, 
            fingerprinter_instance, 
            ingested_song_data, 
            CLIP_DURATIONS_TO_TEST,
            CLIP_START_OFFSETS_PERCENTAGES,
            MIN_MATCH_SCORE_THRESHOLD
        )
        if partial_match_success:
            logger.info("✅ All partial clip matching tests passed or met criteria.")
        else:
            logger.warning("⚠️ Some partial clip matching tests failed or did not find confident matches for all songs.")
    else:
        logger.warning("No songs were successfully ingested to test partial clips.")

    cleanup(ingested_song_data) # Pass the dict of paths