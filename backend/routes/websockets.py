# backend/routes/websockets.py
import tempfile
import os
import uuid

from flask import Blueprint
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from shazam_core.audio_utils import load_audio
from database.db_handler import DatabaseHandler
import json
import logging

logger = logging.getLogger(__name__)

fingerprinter = Fingerprinter()
from flask import current_app

def register_websockets(sock):
    """Register all WebSocket routes with the provided sock instance"""
    db_handler = current_app.extensions['db_handler']

    @sock.route('/tasks/<task_id>')
    def task_updates(ws, task_id):
        try:
            # Get task from database
            task = db_handler.get_task(task_id)
            if not task:
                return ws.close(code=1008, reason='Task not found')
                
            # Send initial state
            ws.send(json.dumps({
                'type': 'initial',
                'task': task
            }))
            
            # If completed, send final message and close
            if task['status'] == 'completed':
                ws.send(json.dumps({
                    'type': 'complete', 
                    'task': task
                }))
                return ws.close()
                
            # Listen for updates
            last_progress = task['processed_items']
            while task and task['status'] not in ('completed', 'failed'):
                task = db_handler.get_task(task_id)
                if task and task['processed_items'] != last_progress:
                    ws.send(json.dumps({
                        "type": "progress",
                        "processed": task['processed_items'],
                        "total": task['total_items']
                    }))
                    last_progress = task['processed_items']
                
            # Final status
            if task:
                ws.send(json.dumps({
                    "type": "complete",
                    "status": task['status'],
                    "result": json.loads(task['result_json']) if task['result_json'] else None
                }))
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}", exc_info=True)
            try:
                ws.send(json.dumps({'type': 'error', 'message': str(e)}))
            except:
                pass
            return ws.close()

    @sock.route('/identify')
    def identify_socket(ws):
        """WebSocket endpoint for real-time song identification."""
        logger.info("WebSocket connection established.")
        db_handler = current_app.extensions['db_handler']
        matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter)
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
    
    return sock

"""WebSocket routes for real-time updates."""
import json
import logging
from database.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)
db = DatabaseHandler()

# Get sock from app context
def get_sock():
    return current_app.extensions['sock']

def main():
    sock = get_sock()
    register_websockets(sock)

if __name__ == "__main__":
    main()