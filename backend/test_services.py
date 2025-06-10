# backend/test_services.py
import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_clients():
    """Test Spotify and YouTube API clients."""
    print("\n--- Testing API Clients ---")
    try:
        from api_clients.spotify_client import SpotifyClient
        from api_clients.youtube_client import YouTubeClient
        
        # Test Spotify
        spotify = SpotifyClient()
        track_url = "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b" # "Mr. Brightside"
        metadata = spotify.get_track_metadata(track_url)
        assert metadata['title'] == "Blinding Lights"
        assert metadata['artist'] == "The Weeknd"
        print("✅ SpotifyClient: Successfully fetched metadata.")

        # Test YouTube
        youtube = YouTubeClient()
        query = "The Killers - Mr. Brightside"
        results = youtube.search_videos(query, max_results=1)
        assert len(results) > 0
        video_id = results[0]['id']
        print(f"✅ YouTubeClient: Successfully found video ID: {video_id}")

        print("--- API Client Tests Passed ---\n")
    except Exception as e:
        logger.error(f"API Client test failed: {e}", exc_info=True)
        raise

def test_database_handler():
    """Test the DatabaseHandler methods."""
    print("\n--- Testing Database Handler ---")
    try:
        from database.db_handler import DatabaseHandler
        
        # Use an in-memory or test-specific DB
        db_handler = DatabaseHandler()
        print("✅ DB Handler: Initialized in-memory database.")

        # Test add_song and get_song_by_id
        song_id = db_handler.add_song(
            title="Test Song",
            artist="Test Artist",
            source_type="test",
            source_id="12345"
        )
        assert song_id is not None
        print(f"✅ DB Handler: Added song with ID {song_id}.")
        
        song = db_handler.get_song_by_id(song_id)
        assert song['title'] == "Test Song"
        print("✅ DB Handler: Retrieved song by ID successfully.")
        
        # Test get_all_songs
        songs = db_handler.get_all_songs()
        assert len(songs) == 1
        print("✅ DB Handler: get_all_songs returned correct count.")

        # Test delete_song
        deleted = db_handler.delete_song(song_id)
        assert deleted is True
        song_after_delete = db_handler.get_song_by_id(song_id)
        assert song_after_delete is None
        print("✅ DB Handler: Deleted song successfully.")

        print("--- Database Handler Tests Passed ---\n")
    except Exception as e:
        logger.error(f"Database Handler test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    test_api_clients()
    test_database_handler()