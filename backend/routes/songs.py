# backend/routes/songs.py
from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from services.song_ingester import SongIngester
from database.db_handler import DatabaseHandler
import logging
from api_clients.spotify_client import SpotifyClient
from api_clients.youtube_client import YouTubeClient
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize dependencies
# Construct the path to the database in the project root
project_root_for_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH_FOR_APP = os.path.join(project_root_for_db, "shazam_library.db")

db_handler = DatabaseHandler(db_path=DB_PATH_FOR_APP)
logger.info(f"Flask app's DatabaseHandler initialized with DB path: {DB_PATH_FOR_APP}")

spotify_client = SpotifyClient() 
youtube_client = YouTubeClient()
song_ingester = SongIngester(
    db_handler=db_handler,
    spotify_client=spotify_client,
    youtube_client=youtube_client
)

songs_bp = Blueprint('songs_bp', __name__)

# Thread pool for parallel processing of playlist tracks
playlist_executor = ThreadPoolExecutor(max_workers=4)

@songs_bp.route('/api/songs', methods=['POST'])
def add_from_spotify():
    """
    Adds songs to the database from a Spotify URL.
    Can handle both individual tracks and playlists.
    
    Request body:
    {
        "spotify_url": "https://open.spotify.com/track/..."  # For individual track
        or
        "spotify_url": "https://open.spotify.com/playlist/..."  # For playlist
    }
    """
    data = request.get_json()
    if not data or 'spotify_url' not in data:
        return jsonify({"success": False, "error": "spotify_url is required"}), 400

    spotify_url = data['spotify_url'].strip()
    
    try:
        # Check if it's a playlist URL
        if 'open.spotify.com/playlist/' in spotify_url or 'spotify:playlist:' in spotify_url:
            logger.info(f"Processing Spotify playlist: {spotify_url}")
            return process_playlist(spotify_url)
        # Check if it's a track URL
        elif 'open.spotify.com/track/' in spotify_url or 'spotify:track:' in spotify_url:
            logger.info(f"Processing Spotify track: {spotify_url}")
            return process_single_track(spotify_url)
        else:
            return jsonify({
                "success": False, 
                "error": "Invalid Spotify URL. Must be a track or playlist URL"
            }), 400
    except Exception as e:
        logger.error(f"Error processing Spotify URL: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


def process_single_track(spotify_url):
    """Process a single Spotify track."""
    try:
        # Check if song already exists
        existing_song = db_handler.get_song_by_spotify_url(spotify_url)
        if existing_song:
            logger.info(f"Song already exists: {spotify_url}")
            return jsonify({
                "success": True,
                "type": "track",
                "song_id": existing_song['id'],
                "title": existing_song.get('title', 'Unknown'),
                "artist": existing_song.get('artist', 'Unknown'),
                "status": "already_exists"
            })

        # Ingest the song
        logger.info(f"Ingesting song: {spotify_url}")
        song = song_ingester.ingest_from_spotify(spotify_url)
        
        if song['success'] == True:
            return jsonify({
                "success": True,
                "type": "track",
                "song_id": song.get('song_id', 'Unknown'),
                "title": song.get('title', 'Unknown'),
                "artist": song.get('artist', 'Unknown'),
                "status": "added"
            })
        else:
            return jsonify({"success": False, "error": "Failed to import song"}), 400
            
    except Exception as e:
        logger.error(f"Error processing track: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400


def process_playlist(playlist_url):
    """Process all tracks from a Spotify playlist."""
    try:
        # Get all tracks from the playlist
        logger.info(f"Fetching tracks from playlist: {playlist_url}")
        tracks = spotify_client.get_playlist_tracks(playlist_url)
        
        if not tracks:
            return jsonify({"success": False, "error": "No tracks found in playlist"}), 400
        
        logger.info(f"Found {len(tracks)} tracks in playlist")
        
        # Process tracks in parallel
        results = []
        futures = []
        
        for track in tracks:
            spotify_url = track.get('spotify_url', '')
            if not spotify_url:
                logger.warning(f"Skipping track without Spotify URL: {track.get('title', 'Unknown')}")
                continue
                
            future = playlist_executor.submit(process_single_track_in_playlist, spotify_url)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing track: {str(e)}", exc_info=True)
                results.append({"success": False, "error": str(e)})
        
        # Count successful imports
        success_count = sum(1 for r in results if r is not None)
        
        return jsonify({
            "success": True,
            "type": "playlist",
            "message": f"Processed {len(tracks)} tracks, {success_count} successfully imported",
            "total_tracks": len(tracks),
            "imported_count": success_count,
            "results": results
        })
        
    except ValueError as e:
        logger.error(f"Error processing playlist: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error processing playlist: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


def process_single_track_in_playlist(spotify_url):
    """Helper function to process a single track within a playlist."""
    try:
        song_id = song_ingester.ingest_from_spotify(spotify_url)
        if song_id:
            return song_id 
        return None
    except Exception as e:
        logger.error(f"Error processing track {spotify_url}: {str(e)}", exc_info=True)
        raise


@songs_bp.route('/api/songs', methods=['GET'])
def get_all_songs():
    """Endpoint to get all songs (for admin panel)."""
    # Note: Add pagination for production use
    songs = db_handler.get_all_songs()
    return jsonify({"success": True, "songs": songs})

@songs_bp.route('/api/songs/<int:song_id>', methods=['DELETE'])
def delete_song_by_id(song_id):
    """Endpoint to delete a song and its fingerprints."""
    success = db_handler.delete_song(song_id)
    if success:
        return jsonify({"success": True, "message": f"Song with ID {song_id} deleted."})
    else:
        return jsonify({"success": False, "error": "Song not found."}), 404


# The /api/songs endpoint now handles both tracks and playlists


# Moved to process_single_track and process_single_track_in_playlist functions


@songs_bp.route('/api/match_live_audio', methods=['POST'])
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
        score = int(best_match['score']) # Ensure score is Python int for JSON

        song_details = db_handler.get_song_by_id(matched_song_id)
        title = song_details.get('title', 'Unknown Title') if song_details else 'Unknown Title'
        artist = song_details.get('artist', 'Unknown Artist') if song_details else 'Unknown Artist'

        logger.info(f"Match found: ID {matched_song_id}, Title: {title}, Score: {score}")
        return jsonify({
            "success": True,
            "match_found": True,
            "song_id": matched_song_id,
            "title": title,
            "artist": artist,
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