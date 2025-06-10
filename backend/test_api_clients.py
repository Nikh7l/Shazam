"""
Test script for the API clients.

This script tests the Spotify and YouTube API clients.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_spotify_client():
    """Test the Spotify client."""
    try:
        from api_clients.spotify_client import spotify
        
        # Test with a known track URL
        test_url = "https://open.spotify.com/track/5CQ30WqJwcep0pYcV4AMNc"  # Blinding Lights - The Weeknd
        
        print("\n=== Testing Spotify Client ===")
        print(f"Fetching metadata for: {test_url}")
        
        metadata = spotify.get_track_metadata(test_url)
        print("\nTrack Metadata:")
        for key, value in metadata.items():
            if key != 'images':
                print(f"{key}: {value}")
        
        # Test search
        print("\nSearching for 'The Weeknd Blinding Lights':")
        results = spotify.search_track("The Weeknd Blinding Lights", limit=3)
        for i, track in enumerate(results, 1):
            print(f"{i}. {track['artist']} - {track['title']} ({track['album']})")
            
    except Exception as e:
        logger.error(f"Spotify test failed: {str(e)}", exc_info=True)

def test_youtube_client():
    """Test the YouTube client."""
    try:
        from api_clients.youtube_client import youtube
        
        # Test search
        query = "The Weeknd Blinding Lights"
        print("\n=== Testing YouTube Client ===")
        print(f"Searching for: {query}")
        
        results = youtube.search_videos(query, max_results=3)
        if not results:
            print("No results found")
            return
            
        print("\nSearch Results:")
        for i, video in enumerate(results, 1):
            print(f"{i}. {video['title']} (by {video['uploader']}, {video['duration']}s)")
        
        # Test download (first result)
        video_id = results[0]['id']
        print(f"\nDownloading audio for video ID: {video_id}")
        
        file_path, metadata = youtube.download_audio(video_id)
        if file_path:
            print(f"\nDownload successful!")
            print(f"File path: {file_path}")
            print(f"Title: {metadata['title']}")
            print(f"Duration: {metadata['duration']}s")
            print(f"Thumbnail: {metadata['thumbnail']}")
            
            # Clean up
            try:
                os.remove(file_path)
                print(f"\nCleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {str(e)}")
        else:
            print(f"\nDownload failed: {metadata.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"YouTube test failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run tests
    test_spotify_client()
    test_youtube_client()
