"""
Test script for the Shazam clone matching API.

This script demonstrates how to test the audio matching functionality.
"""
import os
import sys
import requests
import time

def test_match_audio(api_url, audio_file_path):
    """Test matching an audio file against the database.
    
    Args:
        api_url: Base URL of the API (e.g., 'http://localhost:5001')
        audio_file_path: Path to the audio file to match
    """
    if not os.path.isfile(audio_file_path):
        print(f"Error: File not found: {audio_file_path}")
        return False
    
    url = f"{api_url.rstrip('/')}/api/match"
    
    try:
        print(f"Matching {audio_file_path}...")
        with open(audio_file_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_file_path), f, 'audio/mp3')}
            start_time = time.time()
            response = requests.post(url, files=files)
            elapsed = time.time() - start_time
            
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            matches = result.get('matches', [])
            if matches:
                print(f"\nMatch completed in {elapsed:.2f} seconds")
                print(f"Found {len(matches)} matches:")
                print("-" * 80)
                for i, match in enumerate(matches, 1):
                    print(f"{i}. {match['artist']} - {match['title']}")
                    print(f"   Album: {match.get('album', 'N/A')}")
                    print(f"   Score: {match['score']:.2f}, Matches: {match['total_matches']}")
                    print(f"   Offset: {match['offset_seconds']:.2f}s")
                    print("-" * 80)
            else:
                print("No matches found")
            return True
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <audio_file>")
        print("Example: python test_match.py sample.mp3")
        return
    
    api_url = "http://localhost:5001"
    audio_file = sys.argv[1]
    
    test_match_audio(api_url, audio_file)

if __name__ == "__main__":
    main()
