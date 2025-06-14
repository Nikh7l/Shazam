# backend/routes/songs.py
from flask import Blueprint, request, jsonify, current_app
import os
from typing import Optional
import uuid
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from services.song_ingester import SongIngester
from database.db_handler import DatabaseHandler
import logging
from api_clients.spotify_client import SpotifyClient
from api_clients.youtube_client import YouTubeClient
from dotenv import load_dotenv
# import os # Removed duplicate import, already imported at the top
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize dependencies
# Construct the path to the database in the project root
project_root_for_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH_FOR_APP = os.path.join(project_root_for_db, "shazam_library.db")

songs_bp = Blueprint('songs', __name__, url_prefix='/api')

# Initialize dependencies that don't depend on the app context first
spotify_client = SpotifyClient()
youtube_client = YouTubeClient()



# Initialize a ProcessPoolExecutor for parallel playlist track ingestion.
# ProcessPoolExecutor is chosen because the song fingerprinting process (and other potential
# heavy computations like audio downloading/conversion, though currently handled before this stage),
# can be CPU-bound. Fingerprinting involves STFT and other numerical computations.
# Using processes allows bypassing Python's Global Interpreter Lock (GIL) for these tasks,
# leading to true parallelism on multi-core processors.
# max_workers is set to the number of CPU cores (os.cpu_count()) for optimal CPU utilization.
playlist_executor = ProcessPoolExecutor(max_workers=os.cpu_count())
db_handler = current_app.extensions['db_handler']

@songs_bp.route('/songs', methods=['POST'])
def add_from_spotify():
    data = request.get_json()
    if not data or 'spotify_url' not in data:
        return jsonify({"error": "Missing spotify_url parameter"}), 400

    spotify_url = data['spotify_url'].strip()
    task_id = str(uuid.uuid4())

    try:
        if 'open.spotify.com/playlist/' in spotify_url:
            task_type = "playlist"
            tracks = spotify_client.get_playlist_tracks(spotify_url)
            if not tracks:
                return jsonify({"success": False, "error": "Playlist is empty or could not be fetched."}), 400
            
            db_handler.create_task(task_id, task_type, spotify_url, total_items=len(tracks))

            playlist_executor.submit(
                _process_playlist_async,
                spotify_url, # Although not strictly needed, good for logging
                task_id,
                tracks
            )
            
            return jsonify({
                "success": True,
                "task_id": task_id,
                "message": "Playlist processing started"
            })
            
        elif 'open.spotify.com/track/' in spotify_url:
            task_type = "track"
            db_handler.create_task(task_id, task_type, spotify_url)

            
            playlist_executor.submit(
                _process_single_track_async,
                spotify_url,
                task_id
            )
            
            return jsonify({
                "success": True,
                "message": "Track processing started",
                "task_id": task_id
            })
            
        else:
            return jsonify({"error": "Invalid Spotify URL"}), 400
            
    except Exception as e:
        logger.error(f"Error submitting track task: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _process_single_track_async(spotify_url, task_id):
    """Process single track in background and update task status."""
    # This function runs in a separate process, so it needs to create its own db_handler.
    # We must ensure it uses the same DB_PATH.
    db_handler_process = DatabaseHandler(db_path=DB_PATH_FOR_APP)
    try:
        result = process_single_track_in_playlist_process_safe(
            spotify_url,
            DB_PATH_FOR_APP,
            os.getenv('SPOTIPY_CLIENT_ID'),
            os.getenv('SPOTIPY_CLIENT_SECRET'),
            os.getenv('YOUTUBE_API_KEY')
        )
        
        db_handler_process.complete_task(task_id, result)
        return result
        
    except Exception as e:
        logger.error(f"Async track processing failed: {str(e)}", exc_info=True)
        db_handler_process.complete_task(task_id, {"error": str(e)})
        return {"success": False, "error": str(e)}


def process_single_track_in_playlist_process_safe(spotify_url: str, db_path: str, spotify_client_id: Optional[str], spotify_client_secret: Optional[str], youtube_api_key: Optional[str]):
    """Helper function to process a single track within a playlist, safe for ProcessPoolExecutor."""
    logger.info(f"Process {os.getpid()} initializing clients for track: {spotify_url}")
    # Initialize dependencies within the process
    current_spotify_client = SpotifyClient(client_id=spotify_client_id, client_secret=spotify_client_secret)
    current_youtube_client = YouTubeClient()
    current_db_handler = DatabaseHandler(db_path=db_path)
    # _init_db is typically called in DatabaseHandler constructor, so explicit call might not be needed
    # current_db_handler._init_db()

    current_song_ingester = SongIngester(
        db_handler=current_db_handler,
        spotify_client=current_spotify_client,
        youtube_client=current_youtube_client
    )

    try:
        # Check if song already exists using current_db_handler
        existing_song = current_db_handler.get_song_by_spotify_url(spotify_url)
        if existing_song:
            logger.info(f"Song already exists (in process {os.getpid()}): {spotify_url}")
            return {
                "success": True, "type": "track", "song_id": existing_song['id'],
                "title": existing_song.get('title', 'Unknown'),
                "artist": existing_song.get('artist', 'Unknown'), "status": "already_exists",
                "spotify_url": spotify_url
            }

        logger.info(f"Ingesting song (in process {os.getpid()}): {spotify_url}")
        # ingest_from_spotify returns a dict like:
        # {'success': True, 'song_id': song_id, 'title': ..., 'artist': ...}
        # or {'success': False, 'error': ...}
        song_result = current_song_ingester.ingest_from_spotify(spotify_url)

        if song_result and song_result.get('success'):
            return {
                "success": True, "type": "track", "song_id": song_result.get('song_id'),
                "title": song_result.get('title'), "artist": song_result.get('artist'),
                "status": "added", "spotify_url": spotify_url
            }
        else:
            logger.error(f"Failed to import song (in process {os.getpid()}) {spotify_url}: {song_result.get('error', 'Unknown error')}")
            return {
                "success": False, "error": song_result.get('error', "Failed to import song"),
                "spotify_url": spotify_url
            }

    except Exception as e:
        logger.error(f"Error processing track {spotify_url} in child process {os.getpid()}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "spotify_url": spotify_url}





def _process_playlist_async(playlist_url, task_id, tracks):
    """Actual playlist processing running in background."""
    # This function also runs in a separate process.
    db_handler_process = DatabaseHandler(db_path=DB_PATH_FOR_APP)
    try:
        futures = []
        for i, track in enumerate(tracks):
            future = playlist_executor.submit(
                process_single_track_in_playlist_process_safe,
                track['spotify_url'],
                DB_PATH_FOR_APP,
                os.getenv('SPOTIPY_CLIENT_ID'),
                os.getenv('SPOTIPY_CLIENT_SECRET'),
                os.getenv('YOUTUBE_API_KEY')
            )
            futures.append(future)
            
            # Update progress every 5 tracks
            if i % 5 == 0:
                db_handler_process.update_task_progress(task_id, processed_items=i)
        
        # Wait for completion
        results = []
        for future in as_completed(futures):
            results.append(future.result())
            
        # Final update
        success_count = sum(1 for r in results if r.get('success'))
        db_handler_process.complete_task(task_id, {
            "success_count": success_count,
            "total_tracks": len(tracks),
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Async playlist processing failed: {str(e)}", exc_info=True)
        db_handler_process.complete_task(task_id, {"error": str(e)})


@songs_bp.route('/songs', methods=['GET'])
def get_all_songs():
    """Endpoint to get all songs (for admin panel)."""
    # Note: Add pagination for production use
    songs = db_handler.get_all_songs()
    return jsonify({"success": True, "songs": songs})

@songs_bp.route('/songs/<int:song_id>', methods=['DELETE'])
def delete_song_by_id(song_id):
    """Endpoint to delete a song and its fingerprints."""
    success = db_handler.delete_song(song_id)
    if success:
        return jsonify({"success": True, "message": f"Song with ID {song_id} deleted."})
    else:
        return jsonify({"success": False, "error": "Song not found."}), 404


# The /api/songs endpoint now handles both tracks and playlists


# Moved to process_single_track and process_single_track_in_playlist functions


@songs_bp.route('/match_live_audio', methods=['POST'])
def match_live_audio():
    logger.info("Received request for /api/match_live_audio")
    if 'audio_data' not in request.files:
        logger.warning("No audio_data found in request.files")
        return jsonify({"success": False, "error": "No audio_data part in the request"}), 400

    audio_file = request.files['audio_data']
    if audio_file.filename == '':
        logger.warning("No selected file for audio_data")
        return jsonify({"success": False, "error": "No selected file"}), 400

    # Ensure the main temp_downloads directory exists (SongIngester might also create this)
    # SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    # Using a simpler relative path from project root assuming app.py is in backend
    # and project root is one level up from where app.py is run.
    # For robustness, consider using app.config for base paths.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    temp_dir_base = os.path.join(project_root, 'temp_downloads')
    live_recordings_dir = os.path.join(temp_dir_base, 'live_recordings')
    os.makedirs(live_recordings_dir, exist_ok=True)

    # Generate a unique filename for the temporary audio file
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_filepath = os.path.join(live_recordings_dir, temp_filename)

    try:
        audio_file.save(temp_filepath)
        logger.info(f"Saved live audio to temporary file: {temp_filepath}")

        # Initialize Fingerprinter and Matcher
        # db_handler is already initialized globally in this file
        # For the API, we should use the production DB path if different from CLI's default.
        # Assuming db_handler uses the correct shazam_library.db
        fingerprinter_instance = Fingerprinter()
        matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter_instance)

        logger.info(f"Attempting to match audio file: {temp_filepath}")
        match_results = matcher.match_file(temp_filepath)

        if not match_results:
            logger.info("No match found for the live audio.")
            return jsonify({"success": True, "match_found": False, "message": "No match found."}), 200

        best_match = match_results[0]
        matched_song_id = best_match['song_id']
        score = int(best_match['score'])

        song_details = db_handler.get_song_by_id(matched_song_id)

        if not song_details:
            logger.error(f"Match found for song_id {matched_song_id}, but could not retrieve song details from DB.")
            return jsonify({"success": True, "match_found": False, "message": "Match found but song details are unavailable."}), 200

        logger.info(f"Match found: ID {matched_song_id}, Title: {song_details.get('title')}, Score: {score}")
        
        # The frontend ResultsDisplay.jsx component expects camelCase keys
        # and a specific set of data.
        return jsonify({
            "success": True,
            "match_found": True,
            "songId": song_details.get('id'),
            "youtubeId": song_details.get('youtube_id'),
            "title": song_details.get('title'),
            "artist": song_details.get('artist'),
            "album": song_details.get('album'),
            "coverArt": song_details.get('cover_art_url'),
            "timestamp": song_details.get('timestamp', 0),
            "score": score
        }), 200

    except Exception as e:
        logger.error(f"Error in match_live_audio: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error during matching"}), 500
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.info(f"Cleaned up temporary file: {temp_filepath}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file {temp_filepath}: {e}")


@songs_bp.route('/tasks/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Cleanup completed tasks older than 7 days."""
    try:
        with db_handler._get_connection() as conn:
            cursor = conn.cursor()
            # Delete tasks first due to foreign key constraint
            cursor.execute(
                """DELETE FROM task_notifications 
                WHERE task_id IN (
                    SELECT id FROM background_tasks 
                    WHERE status = 'completed' 
                    AND datetime(completed_at) < datetime('now', '-7 days')
                )"""
            )
            cursor.execute(
                """DELETE FROM background_tasks 
                WHERE status = 'completed' 
                AND datetime(completed_at) < datetime('now', '-7 days')"""
            )
            count = cursor.rowcount
            conn.commit()
            
        return jsonify({
            "success": True,
            "message": f"Cleaned up {count} old tasks"
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up tasks: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@songs_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Check status of background task."""
    try:
        task = db_handler.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found', 'success': False}), 404
            
        # Ensure response is complete before returning
        response = jsonify({
            'success': True,
            'task': task
        })
        response.headers['Content-Length'] = len(response.get_data())
        return response
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500