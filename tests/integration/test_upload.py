"""Integration tests for the file upload functionality of the Shazam clone API.

This script tests the `/api/songs` endpoint for audio file uploads with metadata.
"""
import os
import sys
import requests

def test_upload_audio(api_url, audio_file_path, title, artist, album=None):
    """Test uploading an audio file to the API.
    
    Args:
        api_url: Base URL of the API (e.g., 'http://localhost:5001')
        audio_file_path: Path to the audio file to upload
        title: Song title
        artist: Artist name
        album: Album name (optional)
    """
    if not os.path.isfile(audio_file_path):
        print(f"Error: File not found: {audio_file_path}")
        return False
    
    url = f"{api_url.rstrip('/')}/api/songs"
    files = {'file': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'))}
    data = {'title': title, 'artist': artist}
    
    if album:
        data['album'] = album
    
    try:
        print(f"Uploading {audio_file_path}...")
        response = requests.post(url, files=files, data=data)
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            print(f"Success! Song ID: {result.get('song_id')}")
            print(f"Message: {result.get('message')}")
            return True
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False
    finally:
        files['file'][1].close()
