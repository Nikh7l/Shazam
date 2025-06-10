"""
YouTube client for downloading audio from YouTube videos.

This module provides functionality to search for and download audio from YouTube
videos using yt-dlp.
"""
import os
import logging
import tempfile
from typing import Dict, Optional, Tuple, List
import yt_dlp

# Configure logging
logger = logging.getLogger(__name__)

class YouTubeClient:
    """Client for interacting with YouTube."""
    
    def __init__(self, download_dir: str = None, max_duration: int = 600):
        """Initialize the YouTube client.
        
        Args:
            download_dir: Directory to save downloaded files (default: system temp)
            max_duration: Maximum duration in seconds for videos to download
        """
        self.download_dir = download_dir or os.path.join(tempfile.gettempdir(), 'shazam_downloads')
        self.max_duration = max_duration
        
        # Create download directory if it doesn't exist
        os.makedirs(self.download_dir, exist_ok=True)
    
    def search_videos(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for videos on YouTube.
        
        Args:
            query: Search query (e.g., "Artist - Song")
            max_results: Maximum number of results to return
            
        Returns:
            List of video metadata dictionaries
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': True,
            'noplaylist': True,
            'skip_download': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for videos
                search_query = f"ytsearch{max_results}:{query}"
                result = ydl.extract_info(search_query, download=False)
                
                if not result or 'entries' not in result:
                    return []
                
                videos = []
                for entry in result['entries']:
                    if not entry:
                        continue
                        
                    videos.append({
                        'id': entry.get('id'),
                        'title': entry.get('title', 'Unknown Title'),
                        'uploader': entry.get('uploader', 'Unknown Uploader'),
                        'duration': entry.get('duration', 0),
                        'url': f"https://youtube.com/watch?v={entry.get('id')}",
                        'thumbnail': self._get_best_thumbnail(entry.get('thumbnails', [])),
                    })
                
                return videos
                
        except Exception as e:
            logger.error(f"YouTube search failed: {str(e)}", exc_info=True)
            return []
    
    def download_audio(self, video_id: str) -> Tuple[Optional[str], Dict]:
        """Download audio from a YouTube video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Tuple of (file_path, metadata) or (None, error_info) on failure
        """
        output_template = os.path.join(self.download_dir, '%(id)s.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'max_filesize': 100 * 1024 * 1024,  # 100MB
            'max_duration': self.max_duration,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first to check duration
                info = ydl.extract_info(
                    f'https://youtube.com/watch?v={video_id}',
                    download=False
                )
                
                if not info:
                    return None, {'error': 'Could not get video info'}
                
                # Download the audio
                ydl.download([f'https://youtube.com/watch?v={video_id}'])
                
                # Get the downloaded file path
                file_path = os.path.join(self.download_dir, f"{video_id}.mp3")
                
                if not os.path.exists(file_path):
                    return None, {'error': 'Downloaded file not found'}
                
                # Return file path and metadata
                metadata = {
                    'id': video_id,
                    'title': info.get('title', 'Unknown Title'),
                    'uploader': info.get('uploader', 'Unknown Uploader'),
                    'duration': info.get('duration', 0),
                    'url': f"https://youtube.com/watch?v={video_id}",
                    'thumbnail': self._get_best_thumbnail(info.get('thumbnails', [])),
                }
                
                return file_path, metadata
                
        except Exception as e:
            logger.error(f"YouTube download failed: {str(e)}", exc_info=True)
            return None, {'error': str(e)}
    
    def _get_best_thumbnail(self, thumbnails: List[Dict]) -> str:
        """Get the best quality thumbnail URL from available thumbnails."""
        if not thumbnails:
            return ''
            
        # Sort by resolution (width * height), descending
        sorted_thumbs = sorted(
            thumbnails,
            key=lambda x: x.get('width', 0) * x.get('height', 0),
            reverse=True
        )
        return sorted_thumbs[0].get('url', '') if sorted_thumbs else ''


