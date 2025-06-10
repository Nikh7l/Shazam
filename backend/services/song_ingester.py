"""
Song ingestion service.

This module provides functionality to ingest songs from various sources
(YouTube, Spotify, etc.) into the database.
"""
import logging
import tempfile
import os
import re
from typing import Dict, Optional, List, Tuple, Any

from database.db_handler import DatabaseHandler # For type hinting
from shazam_core.audio_utils import load_audio
from shazam_core.fingerprinting import Fingerprinter
from api_clients.spotify_client import SpotifyClient
from api_clients.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SongIngester:
    """Service for ingesting songs from various sources."""
    
    def __init__(self, db_handler: DatabaseHandler, spotify_client: SpotifyClient, youtube_client: YouTubeClient):
        """Initialize the song ingester.
        
        Args:
            download_dir: Directory to store temporary downloads (default: system temp)
        """
        self.download_dir = os.path.join(tempfile.gettempdir(), 'shazam_downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        self.fingerprinter = Fingerprinter()
        self.db = db_handler
        self.spotify = spotify_client
        self.youtube = youtube_client
    
    def ingest_from_spotify(self, spotify_url: str) -> Dict[str, Any]:
        """Ingest a song from Spotify.
        
        1. Get metadata from Spotify
        2. Find matching YouTube video
        3. Download audio
        4. Generate fingerprints
        5. Store in database
        
        Args:
            spotify_url: Spotify track URL or ID
            
        Returns:
            Dictionary with song information and status
        """
        try:
            spotify_metadata = self.spotify.get_track_metadata(spotify_url)
            if not spotify_metadata:
                return {'success': False, 'error': 'Could not fetch track from Spotify'}

            existing = self.db.get_song_by_source('spotify', spotify_metadata['id'])
            if existing:
                return {'success': True, 'song_id': existing['id'], 'status': 'already_exists'}

            query = f"{spotify_metadata['artist']} - {spotify_metadata['title']} official audio"
            yt_results = self.youtube.search_videos(query, max_results=1)

            if not yt_results:
                return {'success': False, 'error': f"No matching YouTube video found for query: '{query}'"}
            
            yt_video_id = yt_results[0]['id']

            file_path, _ = self.youtube.download_audio(yt_video_id)
            if not file_path or not os.path.exists(file_path):
                return {'success': False, 'error': 'Failed to download audio from YouTube'}

            try:
                # --- CORRECTED BLOCK ---
                audio_data, _ = load_audio(file_path, target_sample_rate=self.fingerprinter.sample_rate)
                fingerprints = self.fingerprinter.generate_fingerprints(audio_data)

                if not fingerprints:
                    return {'success': False, 'error': 'Failed to generate fingerprints'}
                
                # Log all parameters before passing to db.add_song()
                logger.debug('Parameters for db.add_song():')
                logger.debug(f"title: {spotify_metadata.get('title')} (type: {type(spotify_metadata.get('title'))})")
                logger.debug(f"artist: {spotify_metadata.get('artist')} (type: {type(spotify_metadata.get('artist'))})")
                logger.debug(f"album: {spotify_metadata.get('album')} (type: {type(spotify_metadata.get('album'))})")
                logger.debug(f"source_id: {spotify_metadata.get('id')} (type: {type(spotify_metadata.get('id'))})")
                logger.debug(f"duration_ms: {spotify_metadata.get('duration_ms')} (type: {type(spotify_metadata.get('duration_ms'))})")
                logger.debug(f"cover_url: {self._get_best_cover_url(spotify_metadata.get('images', []))} (type: {type(self._get_best_cover_url(spotify_metadata.get('images', [])))})")
                logger.debug(f"release_date: {spotify_metadata.get('release_date')} (type: {type(spotify_metadata.get('release_date'))})")
                logger.debug(f"spotify_url: {spotify_metadata.get('spotify_url')} (type: {type(spotify_metadata.get('spotify_url'))})")
                logger.debug(f"youtube_id: {yt_video_id} (type: {type(yt_video_id)})")
                
                # Add song to DB, now including the youtube_id
                song_id = self.db.add_song(
                    title=str(spotify_metadata['title']) if spotify_metadata.get('title') else '',
                    artist=str(spotify_metadata['artist']) if spotify_metadata.get('artist') else '',
                    album=str(spotify_metadata.get('album', '')),
                    source_type='spotify',
                    source_id=str(spotify_metadata['id']),
                    duration_ms=int(spotify_metadata.get('duration_ms', 0)) if spotify_metadata.get('duration_ms') else None,
                    cover_url=str(self._get_best_cover_url(spotify_metadata.get('images', []))),
                    release_date=str(spotify_metadata.get('release_date', '')) if spotify_metadata.get('release_date') else None,
                    spotify_url=str(spotify_metadata.get('spotify_url', '')),
                    youtube_id=str(yt_video_id)
                )

                if song_id is None:
                    return {'success': False, 'error': 'Failed to add song to the database.'}

                # Update fingerprints with the correct song_id and store them
                for fp in fingerprints:
                    fp.song_id = song_id
                self.db.add_fingerprints(song_id, fingerprints)
                # --- END OF CORRECTED BLOCK ---

                return {
                    'success': True,
                    'song_id': song_id,
                    'title': spotify_metadata['title'],
                    'artist': spotify_metadata['artist'],
                    'status': 'added'
                }
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            logger.error(f"Error ingesting from Spotify: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _get_best_cover_url(self, images: list) -> str:
        """Get the best quality cover image URL from a list of images."""
        return images[0]['url'] if images else ''
    
    def ingest_from_youtube(self, youtube_url: str) -> Dict[str, Any]:
        """Ingest a song from YouTube.
        
        1. Download audio
        2. Generate fingerprints
        3. Store in database
        
        Args:
            youtube_url: YouTube video URL or ID
            
        Returns:
            Dictionary with song information and status
        """
        try:
            # Extract video ID if full URL is provided
            if 'youtube.com' in youtube_url or 'youtu.be' in youtube_url:
                video_id = self._extract_youtube_id(youtube_url)
                if not video_id:
                    return {'success': False, 'error': 'Invalid YouTube URL'}
            else:
                video_id = youtube_url
            
            # Check if already in database
            existing = self.db.get_song_by_source('youtube', video_id)
            if existing:
                return {'success': True, 'song_id': existing['id'], 'status': 'already_exists'}
            
            # Download audio
            file_path, yt_metadata = youtube.download_audio(video_id)
            
            if not file_path or not os.path.exists(file_path):
                return {'success': False, 'error': 'Failed to download audio from YouTube'}
            
            try:
                # Generate fingerprints
                fingerprints = self.fingerprinter.generate_fingerprints(file_path)
                
                if not fingerprints:
                    return {'success': False, 'error': 'Failed to generate fingerprints'}
                
                # Store in database
                song_id = self.db.add_song(
                    title=yt_metadata['title'],
                    artist=yt_metadata['uploader'],
                    source_type='youtube',
                    source_id=video_id,
                    duration_ms=yt_metadata.get('duration', 0) * 1000 if yt_metadata.get('duration') else None,
                    youtube_url=f"https://youtube.com/watch?v={video_id}",
                    cover_url=yt_metadata.get('thumbnail', '')
                )
                
                # Store fingerprints
                self.db.add_fingerprints(song_id, fingerprints)
                
                return {
                    'success': True,
                    'song_id': song_id,
                    'title': yt_metadata['title'],
                    'artist': yt_metadata['uploader'],
                    'status': 'added'
                }
                
            finally:
                # Clean up downloaded file
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up {file_path}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error ingesting from YouTube: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_best_cover_url(self, images: List[Dict[str, Any]]) -> str:
        """Get the best quality cover image URL from a list of images."""
        if not images:
            return ''
        # Sort by size (width * height), descending
        sorted_images = sorted(
            images,
            key=lambda x: x.get('width', 0) * x.get('height', 0),
            reverse=True
        )
        return sorted_images[0].get('url', '') if sorted_images else ''
    
    def _extract_youtube_id(self, url: str) -> str:
        """Extract YouTube video ID from URL."""
        # Handle youtu.be/ID format
        if 'youtu.be/' in url:
            return url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
            
        # Handle youtube.com/watch?v=ID format
        match = re.search(r'(?:v=|youtu\.be\/|\/v\/|\/e\/|embed\/|\?v=|\&v=)([^#\&\?]*)', url)
        return match.group(1) if match else ''
