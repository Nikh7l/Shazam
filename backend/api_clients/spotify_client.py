"""
Spotify API client for fetching track metadata.

This module provides functionality to interact with the Spotify Web API
to fetch track metadata using spotipy.
"""
import os
import logging
from typing import Dict, Optional, Union
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Configure logging
logger = logging.getLogger(__name__)

class SpotifyClient:
    """Client for interacting with the Spotify Web API."""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """Initialize the Spotify client.
        
        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
            
        Note:
            If client_id and client_secret are not provided, they will be
            read from the SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
            environment variables.
        """
        self.client_id = client_id or os.getenv('SPOTIPY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('SPOTIPY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Spotify client credentials not provided. "
                "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables "
                "or pass them to the constructor."
            )
            
        # Initialize the Spotify client
        auth_manager = SpotifyClientCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.client = spotipy.Spotify(auth_manager=auth_manager)
    
    def get_track_metadata(self, spotify_url: str) -> Dict[str, Union[str, int, float]]:
        """Get metadata for a track from its Spotify URL.
        
        Args:
            spotify_url: Spotify track URL
            
        Returns:
            Dictionary containing track metadata with the following keys:
            - id: Spotify track ID
            - title: Track name
            - artist: Primary artist name
            - artists: List of all artist names
            - album: Album name
            - release_date: Release date (YYYY-MM-DD)
            - duration_ms: Duration in milliseconds
            - popularity: Popularity score (0-100)
            - preview_url: URL to a 30-second preview (may be None)
            - external_urls: Dictionary of external URLs
            - images: List of album cover images in various sizes
        """
        try:
            # Extract track ID from URL if needed
            if 'open.spotify.com/track/' in spotify_url:
                track_id = spotify_url.split('track/')[-1].split('?')[0]
            else:
                track_id = spotify_url
                
            # Get track data
            track = self.client.track(track_id)
            
            # Get album data for additional metadata
            album = track.get('album', {})
            
            # Extract artists and ensure names are strings
            raw_artists = track.get('artists', [])
            processed_artists = []
            for artist_data in raw_artists:
                artist_name = artist_data.get('name')
                if isinstance(artist_name, dict):
                    # Attempt to extract a sensible string, e.g., from a common key or just convert
                    # This is a placeholder, actual extraction might need more specific logic
                    # based on the observed dictionary structure.
                    artist_name = str(artist_name.get('name', artist_name))
                processed_artists.append(str(artist_name) if artist_name else 'Unknown Artist')

            # Ensure track title is a string
            track_title = track.get('name')
            if isinstance(track_title, dict):
                # Similar placeholder logic for track title
                track_title = str(track_title.get('name', track_title))
            track_title = str(track_title) if track_title else 'Unknown Title'
            
            # Build metadata dictionary
            metadata = {
                'id': track['id'],
                'title': track_title,
                'artist': processed_artists[0] if processed_artists else 'Unknown Artist',
                'artists': processed_artists,
                'album': str(album.get('name', 'Unknown Album')), 
                'release_date': album.get('release_date', ''),
                'duration_ms': track.get('duration_ms', 0),
                'popularity': track.get('popularity', 0),
                'preview_url': track.get('preview_url'),
                'external_urls': track.get('external_urls', {}),
                'images': album.get('images', []),
                'spotify_url': track.get('external_urls', {}).get('spotify', '')
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching Spotify track {spotify_url}: {str(e)}", exc_info=True)
            raise ValueError(f"Could not fetch track metadata: {str(e)}")
    
    def search_track(self, query: str, limit: int = 5) -> list:
        """Search for tracks on Spotify.
        
        Args:
            query: Search query (e.g., "artist:Taylor Swift track:Love Story")
            limit: Maximum number of results to return (1-50)
            
        Returns:
            List of track metadata dictionaries
        """
        try:
            results = self.client.search(q=query, limit=limit, type='track')
            tracks = results.get('tracks', {}).get('items', [])
            
            return [{
                'id': track['id'],
                'title': track['name'],
                'artist': track['artists'][0]['name'] if track.get('artists') else 'Unknown Artist',
                'album': track['album']['name'] if track.get('album') else 'Unknown Album',
                'preview_url': track.get('preview_url'),
                'external_urls': track.get('external_urls', {})
            } for track in tracks]
            
        except Exception as e:
            logger.error(f"Error searching Spotify: {str(e)}", exc_info=True)
            return []
    
    def get_playlist_tracks(self, playlist_url: str) -> list[dict]:
        """Get all tracks from a Spotify playlist.
        
        Args:
            playlist_url: Spotify playlist URL or URI
            
        Returns:
            List of track metadata dictionaries, each containing the same fields as get_track_metadata()
            
        Raises:
            ValueError: If the playlist URL is invalid or an error occurs
        """
        logger.debug(f"Fetching playlist tracks for URL: {playlist_url}")
        try:
            # Extract playlist ID from URL or URI
            if 'spotify.com' in playlist_url:
                # Extract ID from URL
                parts = playlist_url.split('/')
                if 'playlist' in parts:
                    playlist_id = parts[parts.index('playlist') + 1].split('?')[0]
                else:
                    raise ValueError("Invalid Spotify playlist URL")
            elif 'spotify:playlist:' in playlist_url:
                # Extract ID from URI
                playlist_id = playlist_url.split(':')[-1]
            else:
                raise ValueError("Invalid Spotify playlist URL or URI")
            
            # Get all tracks from the playlist
            results = self.client.playlist_tracks(playlist_id, fields='items(track(id,name,artists,album,duration_ms,popularity,preview_url,external_urls))')
            logger.debug(f"Initial playlist_tracks API response: {results}")
            tracks = []
            
            while results:
                for item in results['items']:
                    track = item.get('track')
                    logger.debug(f"Processing track item: {track}")
                    if track:  # Skip None tracks (can happen with removed tracks)
                        # Debug log the raw track data structure
                        logger.debug(f"Raw track data: {track}")
                        logger.debug(f"Track name type: {type(track.get('name'))}, value: {track.get('name')}")
                        logger.debug(f"Track artists: {track.get('artists')}")
                        logger.debug(f"Track album: {track.get('album')}")
                        
                        # Format track data to match get_track_metadata()
                        artists = []
                        for artist in track.get('artists', []):
                            logger.debug(f"Processing artist: {artist}")
                            artist_name = artist.get('name')
                            if artist_name is not None:
                                artists.append(str(artist_name))
                            else:
                                logger.warning(f"Unexpected artist format: {artist}")
                                
                        album = track.get('album', {})
                        
                        # Ensure all values are JSON-serializable and of the correct type
                        track_id = str(track.get('id', ''))
                        track_name = str(track.get('name', 'Unknown Track'))
                        primary_artist = str(artists[0]) if artists else 'Unknown Artist'
                        album_name = str(album.get('name', 'Unknown Album'))
                        release_date = str(album.get('release_date', ''))
                        duration = int(track.get('duration_ms', 0)) if track.get('duration_ms') is not None else 0
                        popularity = int(track.get('popularity', 0)) if track.get('popularity') is not None else 0
                        preview_url = str(track.get('preview_url')) if track.get('preview_url') else None
                        external_urls = dict(track.get('external_urls', {}))
                        images = list(album.get('images', []))
                        spotify_url = str(external_urls.get('spotify', ''))
                        
                        track_metadata = {
                            'id': track_id,
                            'title': track_name,
                            'artist': primary_artist,
                            'artists': [str(a) for a in artists],
                            'album': album_name,
                            'release_date': release_date,
                            'duration_ms': duration,
                            'popularity': popularity,
                            'preview_url': preview_url,
                            'external_urls': external_urls,
                            'images': images,
                            'spotify_url': spotify_url
                        }
                        logger.debug(f"Processed track metadata: {track_metadata}")
                        tracks.append(track_metadata)
                
                # Check if there are more tracks to fetch
                if results and results.get('next'):
                    logger.debug("Fetching next page of tracks...")
                    results = self.client.next(results)
                    logger.debug(f"Next page results: {results is not None}")
                else:
                    logger.debug("No more pages to fetch")
                    results = None  # No more pages, exit loop
                    
            return tracks
            
        except Exception as e:
            logger.error(f"Error fetching Spotify playlist tracks: {str(e)}", exc_info=True)
            raise ValueError(f"Could not fetch playlist tracks: {str(e)}")

    def _extract_track_id(self, url_or_uri: str) -> str:
        """Extract track ID from a Spotify URL or URI.
        
        Args:
            url_or_uri: Spotify track URL or URI
            
        Returns:
            Spotify track ID
            
        Raises:
            ValueError: If the URL/URI is invalid
        """
        # Handle both URLs and URIs
        if 'spotify.com' in url_or_uri:
            # Extract ID from URL
            parts = url_or_uri.split('/')
            if 'track' in parts:
                track_id = parts[parts.index('track') + 1]
                # Remove any query parameters
                track_id = track_id.split('?')[0]
                return track_id
        elif 'spotify:track:' in url_or_uri:
            # Extract ID from URI
            return url_or_uri.split(':')[-1]
            
            return url_or_uri
            
        raise ValueError("Invalid Spotify track URL or URI")
