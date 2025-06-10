# backend/test_endpoints.py
import requests
import json
import time

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


if __name__ == "__main__":
    print("Ensure the Flask server is running on http://localhost:5001")
    time.sleep(2)
    
    new_song_id = test_add_song_endpoint()
    test_get_and_delete_endpoints(new_song_id)