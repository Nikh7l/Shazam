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
from concurrent.futures import ProcessPoolExecutor, as_completed

load_dotenv()

logger = logging.getLogger(__name__)

songs_bp = Blueprint('songs', __name__, url_prefix='/api')

# Initialize a ProcessPoolExecutor for parallel playlist track ingestion.
# This is defined globally as it doesn't depend on app state and can be shared.
playlist_executor = ProcessPoolExecutor(max_workers=os.cpu_count())


@songs_bp.route('/songs', methods=['POST'])
def add_from_spotify():
    data = request.get_json()
    if not data or 'spotify_url' not in data:
        return jsonify({"error": "Missing spotify_url parameter"}), 400

    spotify_url = data['spotify_url'].strip()
    task_id = str(uuid.uuid4())

    # Access dependencies from the application context
    db_handler = current_app.extensions['db_handler']
    spotify_client = current_app.extensions['spotify_client']
    db_path = current_app.config['DATABASE']

    try:
        if 'open.spotify.com/playlist/' in spotify_url:
            task_type = "playlist"
            tracks = spotify_client.get_playlist_tracks(spotify_url)
            if not tracks:
                return jsonify({"success": False, "error": "Playlist is empty or could not be fetched."}), 400
            
            db_handler.create_task(task_id, task_type, spotify_url, total_items=len(tracks))

            playlist_executor.submit(
                _process_playlist_async,
                task_id,
                tracks,
                db_path,
                os.getenv('SPOTIFY_CLIENT_ID'),
                os.getenv('SPOTIFY_CLIENT_SECRET')
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
                task_id,
                db_path,
                os.getenv('SPOTIFY_CLIENT_ID'),
                os.getenv('SPOTIFY_CLIENT_SECRET')
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
        db_handler.update_task_status(task_id, 'failed', result={'error': str(e)})
        return jsonify({"success": False, "error": str(e)}), 500


def _process_single_track_async(spotify_url, task_id, db_path, spotify_client_id, spotify_client_secret):
    """Process single track in background and update task status."""
    db_handler_process = DatabaseHandler(db_path=db_path)
    try:
        result = _ingest_track_safely(
            spotify_url,
            db_path,
            spotify_client_id,
            spotify_client_secret
        )
        db_handler_process.complete_task(task_id, result)
        return result
    except Exception as e:
        logger.error(f"Async track processing failed: {str(e)}", exc_info=True)
        db_handler_process.complete_task(task_id, {"error": str(e)})
        return {"success": False, "error": str(e)}


def _ingest_track_safely(spotify_url: str, db_path: str, spotify_client_id: Optional[str], spotify_client_secret: Optional[str]):
    """Helper function to process a single track, safe for ProcessPoolExecutor."""
    logger.info(f"Process {os.getpid()} initializing clients for track: {spotify_url}")
    # Initialize dependencies within the process
    current_spotify_client = SpotifyClient(client_id=spotify_client_id, client_secret=spotify_client_secret)
    current_youtube_client = YouTubeClient()
    current_db_handler = DatabaseHandler(db_path=db_path)

    current_song_ingester = SongIngester(
        db_handler=current_db_handler,
        spotify_client=current_spotify_client,
        youtube_client=current_youtube_client
    )

    try:
        existing_song = current_db_handler.get_song_by_spotify_url(spotify_url)
        if existing_song:
            logger.info(f"Song already exists (in process {os.getpid()}): {spotify_url}")
            return {
                "success": True, "status": "already_exists", "spotify_url": spotify_url,
                "song_id": existing_song['id'], "title": existing_song.get('title'), "artist": existing_song.get('artist')
            }

        logger.info(f"Ingesting song (in process {os.getpid()}): {spotify_url}")
        song_result = current_song_ingester.ingest_from_spotify(spotify_url)

        if song_result and song_result.get('success'):
            return {
                "success": True, "status": "added", "spotify_url": spotify_url,
                "song_id": song_result.get('song_id'), "title": song_result.get('title'), "artist": song_result.get('artist')
            }
        else:
            error_message = song_result.get('error', 'Unknown error during ingestion')
            logger.error(f"Failed to import song {spotify_url} (in process {os.getpid()}): {error_message}")
            return {"success": False, "error": error_message, "spotify_url": spotify_url}

    except Exception as e:
        logger.error(f"Error processing track {spotify_url} in child process {os.getpid()}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e), "spotify_url": spotify_url}


def _process_playlist_async(task_id, tracks, db_path, spotify_client_id, spotify_client_secret):
    """Actual playlist processing running in background."""
    db_handler_process = DatabaseHandler(db_path=db_path)
    try:
        futures = [
            playlist_executor.submit(
                _ingest_track_safely,
                track['spotify_url'],
                db_path,
                spotify_client_id,
                spotify_client_secret
            ) for track in tracks
        ]
        
        results = []
        for i, future in enumerate(as_completed(futures)):
            results.append(future.result())
            # Update progress after each track is processed
            db_handler_process.update_task_progress(task_id, processed_items=i + 1)
        
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
    db_handler = current_app.extensions['db_handler']
    songs = db_handler.get_all_songs()
    return jsonify({"success": True, "songs": songs})

@songs_bp.route('/songs/<int:song_id>', methods=['DELETE'])
def delete_song_by_id(song_id):
    """Endpoint to delete a song and its fingerprints."""
    db_handler = current_app.extensions['db_handler']
    success = db_handler.delete_song(song_id)
    if success:
        return jsonify({"success": True, "message": f"Song with ID {song_id} deleted."})
    else:
        return jsonify({"success": False, "error": "Song not found."}), 404


def _save_live_audio_file(audio_file):
    """Saves the uploaded audio file to a temporary location and returns the path."""
    temp_dir_base = os.path.join(current_app.root_path, '..', 'temp_downloads')
    live_recordings_dir = os.path.join(temp_dir_base, 'live_recordings')
    os.makedirs(live_recordings_dir, exist_ok=True)

    temp_filename = f"{uuid.uuid4()}.wav"
    temp_filepath = os.path.join(live_recordings_dir, temp_filename)
    audio_file.save(temp_filepath)
    logger.info(f"Saved live audio to temporary file: {temp_filepath}")
    return temp_filepath


def _perform_audio_match(filepath):
    """Matches the audio file against the database and returns results."""
    db_handler = current_app.extensions['db_handler']
    fingerprinter_instance = Fingerprinter()
    matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter_instance)
    
    logger.info(f"Attempting to match audio file: {filepath}")
    return matcher.match_file(filepath)


@songs_bp.route('/match_live_audio', methods=['POST'])
def match_live_audio():
    logger.info("Received request for /api/match_live_audio")
    if 'audio_data' not in request.files:
        return jsonify({"success": False, "error": "No audio_data part in the request"}), 400

    audio_file = request.files['audio_data']
    if audio_file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    temp_filepath = None
    try:
        temp_filepath = _save_live_audio_file(audio_file)
        match_results = _perform_audio_match(temp_filepath)

        if not match_results:
            logger.info("No match found for the live audio.")
            return jsonify({"success": True, "match_found": False, "message": "No match found."})

        best_match = match_results[0]
        matched_song_id = best_match['song_id']
        score = int(best_match['score'])

        db_handler = current_app.extensions['db_handler']
        song_details = db_handler.get_song_by_id(matched_song_id)

        if not song_details:
            logger.error(f"Match found for song_id {matched_song_id}, but could not retrieve details.")
            return jsonify({"success": True, "match_found": False, "message": "Match found but song details unavailable."})

        logger.info(f"Match found: ID {matched_song_id}, Title: {song_details.get('title')}, Score: {score}")
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
        })

    except Exception as e:
        logger.error(f"Error in match_live_audio: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error during matching"}), 500
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.info(f"Cleaned up temporary file: {temp_filepath}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary file {temp_filepath}: {e}")


@songs_bp.route('/tasks/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Cleanup completed tasks older than a specified number of days."""
    db_handler = current_app.extensions['db_handler']
    try:
        # Using a method on db_handler is cleaner than embedding SQL here
        count = db_handler.cleanup_old_tasks(days=7)
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
    db_handler = current_app.extensions['db_handler']
    try:
        task = db_handler.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found', 'success': False}), 404
        
        return jsonify({
            'success': True,
            'task': task
        })
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500