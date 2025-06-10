# backend/routes/websockets.py
import tempfile
import os
import uuid

from flask import Blueprint
from flask_sock import Sock # <-- Import Sock
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from shazam_core.audio_utils import load_audio
from database.db_handler import DatabaseHandler
import json
import logging

logger = logging.getLogger(__name__)

# Create a Blueprint for our websocket route
ws_bp = Blueprint('ws_bp', __name__)
sock = Sock(ws_bp) # <-- Initialize Sock on the Blueprint

# Initialize dependencies
db_handler = DatabaseHandler()
fingerprinter = Fingerprinter()
matcher = FingerprintMatcher(db_handler=db_handler,fingerprinter_instance=fingerprinter)

@sock.route('/identify')
def identify_socket(ws):
    """WebSocket endpoint for real-time song identification."""
    logger.info("WebSocket connection established.")
    audio_buffer = bytearray()
    
    while True:
        try:
            data = ws.receive(timeout=5)
            if data is None:
                break
            audio_buffer.extend(data)
        except Exception:
            break
            
    logger.info(f"Received {len(audio_buffer)} bytes of audio data. Processing...")

    if not audio_buffer:
        logger.warning("Received empty audio buffer.")
        return

    # --- THE FIX STARTS HERE ---
    temp_file_path = None
    try:
        # Step 1: Write the received bytes to a temporary file
        # This gives ffmpeg a real, seekable file to work with.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_f:
            temp_f.write(audio_buffer)
            temp_file_path = temp_f.name
        
        logger.info(f"Audio buffer written to temporary file: {temp_file_path}")

        # Step 2: Load the audio from the temporary file path
        # The load_audio function is robust and handles file paths well.
        audio_data, _ = load_audio(temp_file_path)

        # Step 3: Generate fingerprints
        logger.info("Audio loaded successfully. Generating fingerprints...")
        query_fingerprints = fingerprinter.generate_fingerprints(audio_data)

        # Step 4: Match against the database
        logger.info(f"Generated {len(query_fingerprints)} fingerprints. Matching...")
        matches = matcher.match_fingerprints(query_fingerprints)

        if not matches:
            ws.send(json.dumps({"status": "no_match"}))
            logger.info("No match found.")
            return

        # Step 5: Get best match details
        best_match = matches[0]
        song = db_handler.get_song_by_id(best_match['song_id'])
        
        # ... (rest of the matching logic is the same) ...
        if song:
            response_data = {
                "status": "match_found",
                "data": {
                    "title": song.get('title'),
                    "artist": song.get('artist'),
                    "album": song.get('album'),
                    "coverArt": song.get('cover_url'),
                    "youtubeId": song.get('youtube_id'),
                    "timestamp": best_match['offset_seconds']
                }
            }
            ws.send(json.dumps(response_data))
            logger.info(f"Match found: {song.get('title')} by {song.get('artist')}")
        else:
            ws.send(json.dumps({"status": "no_match"}))

    except Exception as e:
        logger.error(f"Error during matching process: {e}", exc_info=True)
        ws.send(json.dumps({"status": "error", "message": "Failed to process audio."}))
    finally:
        # Step 6: Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.error(f"Failed to remove temporary file {temp_file_path}: {e}")
    # --- END OF FIX ---