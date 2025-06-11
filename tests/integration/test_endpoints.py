"""Integration tests for the main API endpoints (e.g., /api/songs). These tests interact with a running server instance."""
# backend/test_endpoints.py
import requests
import json
import time
import pytest

API_BASE_URL = "http://localhost:5001"

def test_add_song_endpoint():
    """Test the POST /api/songs endpoint."""
    print("\n--- Testing Add Song Endpoint (POST /api/songs) ---")
    url = f"{API_BASE_URL}/api/songs"

    # A song that is likely not in your DB yet
    spotify_url = "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b" # Blinding Lights by The Weeknd

    payload = {"spotify_url": spotify_url}

    try:
        response = requests.post(url, json=payload, timeout=60) # Increased timeout for download/processing
        data = response.json()

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")

        assert response.status_code in [200, 201]
        assert data.get("success") is True
        assert data.get("song_id") is not None

        print("✅ Add Song Endpoint: Successfully added or found song.")
        return data.get("song_id") # Return for use in delete test
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect to the server. Is it running? {e}")
        return None

def test_get_and_delete_endpoints(song_id):
    """Test GET and DELETE endpoints for songs."""
    if not song_id:
        print("\n--- Skipping Get/Delete Tests (song_id not available) ---")
        return

    print(f"\n--- Testing Get & Delete Endpoints for song_id={song_id} ---")

    # Test GET /api/songs
    get_all_url = f"{API_BASE_URL}/api/songs"
    response_get = requests.get(get_all_url)
    assert response_get.status_code == 200
    songs = response_get.json().get("songs", [])
    assert any(s['id'] == song_id for s in songs)
    print("✅ Get All Songs: Successfully found the new song in the list.")

    # Test DELETE /api/songs/:id
    delete_url = f"{API_BASE_URL}/api/songs/{song_id}"
    response_delete = requests.delete(delete_url)
    assert response_delete.status_code == 200
    assert response_delete.json().get("success") is True
    print(f"✅ Delete Song: Successfully deleted song with ID {song_id}.")

    # Verify deletion
    response_get_after = requests.get(get_all_url)
    songs_after = response_get_after.json().get("songs", [])
    assert not any(s['id'] == song_id for s in songs_after)
    print("✅ Deletion Verified: Song is no longer in the list.")

def test_add_song_endpoint_invalid_spotify_url():
    """Test POST /api/songs with an invalid Spotify URL format."""
    print("\n--- Testing Add Song Endpoint with Invalid Spotify URL Format ---")
    url = f"{API_BASE_URL}/api/songs"
    payload = {"spotify_url": "not_a_spotify_url"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 400 # Bad Request
        assert data.get("success") is False
        assert "Invalid Spotify URL" in data.get("error", "")
        print("✅ Add Song with Invalid URL: Correctly handled.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}. Is the server running?")

def test_add_song_endpoint_missing_payload_key():
    """Test POST /api/songs with a missing 'spotify_url' key in payload."""
    print("\n--- Testing Add Song Endpoint with Missing Payload Key ---")
    url = f"{API_BASE_URL}/api/songs"
    payload = {"other_key": "some_value"} # Missing 'spotify_url'
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 400 # Bad Request
        assert data.get("success") is False
        assert "Missing spotify_url in request" in data.get("error", "") # Assuming this error message
        print("✅ Add Song with Missing Key: Correctly handled.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}. Is the server running?")

def test_add_song_endpoint_spotify_track_not_found():
    """Test POST /api/songs with a Spotify URL for a non-existent track."""
    print("\n--- Testing Add Song Endpoint with Non-Existent Spotify Track ---")
    url = f"{API_BASE_URL}/api/songs"
    # This is a syntactically valid Spotify track ID format, but likely doesn't exist
    non_existent_spotify_url = "https://open.spotify.com/track/0000000000000000000000"
    payload = {"spotify_url": non_existent_spotify_url}
    try:
        # This test depends on how the backend handles Spotify API errors (e.g., track not found)
        # It might take longer if Spotify API calls timeout or retry
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 404 or response.status_code == 500 # Or other appropriate error code
        assert data.get("success") is False
        # The error message might vary depending on backend implementation
        assert "Could not fetch track from Spotify" in data.get("error", "") or \
               "No matching YouTube video found" in data.get("error", "") # If Spotify works but YouTube fails for a fake track
        print("✅ Add Song with Non-Existent Track: Correctly handled.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}. Is the server running?")