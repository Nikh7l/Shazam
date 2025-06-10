import sounddevice as sd
import numpy as np
import sys
import os
import logging
import time
from queue import Queue

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import our project components
from database.db_handler import DatabaseHandler
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SAMPLE_RATE = 11025  # Must match the fingerprinter's sample rate
BLOCK_DURATION_SEC = 2  # Process audio in 2-second chunks
RECORDING_DURATION_SEC = 7 # Duration of audio to analyze for one match attempt

# --- Audio Recording Setup ---
audio_queue = Queue()

def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(indata.copy())

def start_mic_stream():
    """Starts listening to the microphone in a non-blocking way."""
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1, # Mono
        dtype='float32',
        callback=audio_callback
    )
    stream.start()
    logger.info("🎤 Microphone stream started. Listening...")
    return stream

# --- Main Application Logic ---
if __name__ == "__main__":
    # Initialize core components
    db_handler = DatabaseHandler() # Uses the main shazam.db
    fingerprinter = Fingerprinter(sample_rate=SAMPLE_RATE)
    matcher = FingerprintMatcher(db_handler, fingerprinter)
    
    # Start listening to the microphone
    mic_stream = start_mic_stream()
    
    print("\n=============================================")
    print(" Shazam Clone CLI Listener")
    print(" Playing music? I'm trying to guess it...")
    print(" Press Ctrl+C to stop.")
    print("=============================================\n")

    try:
        while True:
            # 1. Collect a buffer of audio for one match attempt
            buffer_size = int(RECORDING_DURATION_SEC * SAMPLE_RATE)
            recording_buffer = np.array([], dtype=np.float32)

            while len(recording_buffer) < buffer_size:
                # Get audio data from the queue (which is filled by the callback)
                audio_chunk = audio_queue.get()
                recording_buffer = np.concatenate((recording_buffer, audio_chunk.flatten()))
            
            logger.info(f"Collected a {RECORDING_DURATION_SEC}s audio snippet. Analyzing...")

            # 2. Generate fingerprints for the collected audio
            try:
                query_fingerprints = fingerprinter.generate_fingerprints(recording_buffer)
                if not query_fingerprints:
                    logger.warning("Snippet was silent or no features found. Still listening...")
                    time.sleep(2) # Wait a bit before next attempt
                    continue
                logger.info(f"Generated {len(query_fingerprints)} fingerprints for the query.")
            except Exception as e:
                logger.error(f"Could not generate fingerprints: {e}", exc_info=True)
                continue

            # Match against the database
            try:
                # This is where the original error was happening. It's now fixed in db_handler.py
                results = matcher.match_fingerprints(query_fingerprints)
            except Exception as e:
                # This block will catch any other unexpected errors during matching
                logger.error(f"Error during matching: {e}", exc_info=True)
                continue

            # 4. Display the result
            if results:
                best_match = results[0]
                song = db_handler.get_song_by_id(best_match['song_id'])
                if song:
                    print("\n-------------------------------------------")
                    print(f"✅ MATCH FOUND: {song['artist']} - {song['title']}")
                    print(f"   (Score: {best_match['score']}, Offset: {best_match['offset_seconds']:.2f}s)")
                    print("-------------------------------------------\n")
                else:
                    print(f"\n[!] Found match for song ID {best_match['song_id']} but couldn't retrieve metadata.\n")
            else:
                print("... No confident match found. Still listening ...")

            # Wait a moment before the next attempt to avoid spamming
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping listener...")
        mic_stream.stop()
        mic_stream.close()
        print("Goodbye!")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        mic_stream.stop()
        mic_stream.close()