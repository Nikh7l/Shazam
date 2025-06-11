"""Integration tests for the complete song ingestion and matching flow."""
# backend/test_full_flow.py
import requests
import websocket
import threading
import time
import json
import os

API_BASE_URL = "http://localhost:5001"
WS_URL = "ws://localhost:5001/identify"
TEST_SNIPPET_FILE = "test_music.mp3"
SPOTIFY_URL_TO_ADD = "https://open.spotify.com/track/2oenSXLDbWVaaL7QjSGYj5" # "Take on Me" by a-ha

def add_song_to_db():
    """Step 1: Add a song to the database via REST API."""
    print("\n--- STEP 1: ADDING SONG TO DATABASE ---")
    url = f"{API_BASE_URL}/api/songs"
    payload = {"spotify_url": SPOTIFY_URL_TO_ADD}
    
    try:
        response = requests.post(url, json=payload, timeout=90) # Long timeout for download
        data = response.json()
        
        if response.status_code in [200, 201] and data.get("success"):
            song_id = data.get("song_id")
            print(f"✅ Successfully added song with ID: {song_id}")
            return song_id
        else:
            print(f"❌ FAILED to add song. Response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED to connect to server: {e}")
        return None

def match_snippet_via_websocket():
    """Step 2: Test matching a snippet of the added song."""
    print("\n--- STEP 2: MATCHING SNIPPET VIA WEBSOCKET ---")
    
    if not os.path.exists(TEST_SNIPPET_FILE):
        print(f"❌ ERROR: Test snippet '{TEST_SNIPPET_FILE}' not found.")
        return

    # Use a threading event to wait for the message
    message_received_event = threading.Event()
    
    def on_message(ws, message):
        print("\n<-- Received from server:")
        data = json.loads(message)
        print(json.dumps(data, indent=2))
        
        # Check if the match is correct
        if data.get("status") == "match_found" and data["data"]["title"] == "Lalkara":
            print("\n✅ SUCCESS: Correct song was identified!")
        else:
            print("\n❌ FAILED: Incorrect or no match found.")
            
        message_received_event.set()
        ws.close()

    def on_error(ws, error):
        print(f"### WebSocket Error: {error} ###")
        message_received_event.set()
        ws.close()

    def on_open(ws):
        print("--> WebSocket opened. Sending audio snippet...")
        with open(TEST_SNIPPET_FILE, "rb") as f:
            ws.send(f.read(), websocket.ABNF.OPCODE_BINARY)
        # In a real client, you might keep the connection open, but for this test,
        # we can close it after sending, or let the server close it.
        # The backend logic handles the closing after it processes.

    ws_app = websocket.WebSocketApp(WS_URL,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error)
    
    # Run the WebSocket client in a separate thread
    ws_thread = threading.Thread(target=ws_app.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for a message to be received or timeout
    print("--> Waiting for match result from server...")
    message_received_event.wait(timeout=30) # Wait up to 30 seconds
    if not message_received_event.is_set():
        print("❌ FAILED: Timed out waiting for a response from the server.")
    
    ws_app.close()


def delete_song_from_db(song_id):
    """Step 3: Clean up by deleting the song."""
    if not song_id:
        print("\n--- SKIPPING CLEANUP (no song_id) ---")
        return
        
    print(f"\n--- STEP 3: CLEANING UP SONG ID {song_id} ---")
    url = f"{API_BASE_URL}/api/songs/{song_id}"
    try:
        response = requests.delete(url)
        if response.status_code == 200:
            print(f"✅ Successfully deleted song {song_id}.")
        else:
            print(f"❌ FAILED to delete song {song_id}. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED to connect to server for cleanup: {e}")