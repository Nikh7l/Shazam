"""Integration tests for the core matching functionality of the Shazam clone API.

This script focuses on testing the `/api/match` endpoint, assuming songs
are already fingerprinted and stored in the database.
"""
import os
import sys # Keep for _helper_match_audio if it still uses sys.argv indirectly or for other reasons
import requests
import time # Keep for _helper_match_audio
import json
import pytest

API_BASE_URL = "http://localhost:5001"

def _helper_match_audio(api_url, audio_file_path):
    """Helper function to match an audio file against the database.

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

@pytest.fixture
def sample_audio_file_path():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample.wav')
    if not os.path.exists(path):
        pytest.skip(f"Sample audio file not found: {path}")
    return path

def test_match_audio_success_placeholder(sample_audio_file_path):
    """Placeholder test for successful audio match.
    This test currently only checks if the endpoint runs without crashing and returns a valid JSON structure.
    It does not guarantee a match is found, as that depends on DB state.
    """
    print("\n--- Testing /api/match (Placeholder Success) ---")
    url = f"{API_BASE_URL}/api/match"
    try:
        with open(sample_audio_file_path, 'rb') as f:
            files = {'file': (os.path.basename(sample_audio_file_path), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=20)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")

        assert response.status_code == 200
        assert 'success' in data # Either True (match found) or False (no match)
        if data.get('success', False):
            assert 'matches' in data
        else:
            # If success is False, there might be an error message or empty matches list
            assert 'matches' in data or 'error' in data
        print("✅ /api/match placeholder success test completed.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to /api/match failed: {e}. Is the server running?")

def test_match_no_file_uploaded():
    """Test POST /api/match with no file uploaded."""
    print("\n--- Testing /api/match with No File Uploaded ---")
    url = f"{API_BASE_URL}/api/match"
    try:
        response = requests.post(url, timeout=10) # No files dict
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 400 # Bad Request
        assert data.get("success") is False
        assert "No file part" in data.get("error", "") or "No file selected" in data.get("error", "") # Example error messages
        print("✅ /api/match with No File: Correctly handled.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to /api/match failed: {e}. Is the server running?")

def test_match_wrong_file_key(sample_audio_file_path):
    """Test POST /api/match with an incorrect file key."""
    print("\n--- Testing /api/match with Incorrect File Key ---")
    url = f"{API_BASE_URL}/api/match"
    try:
        with open(sample_audio_file_path, 'rb') as f:
            # Using 'audiofile' instead of the expected 'file' key
            files = {'audiofile': (os.path.basename(sample_audio_file_path), f, 'audio/wav')}
            response = requests.post(url, files=files, timeout=10)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 400 # Bad Request
        assert data.get("success") is False
        assert "No file part" in data.get("error", "") or "File key should be 'file'" in data.get("error", "") # Example error messages
        print("✅ /api/match with Incorrect Key: Correctly handled.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to /api/match failed: {e}. Is the server running?")
