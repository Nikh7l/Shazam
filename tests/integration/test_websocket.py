"""Integration tests for the WebSocket communication and real-time client updates."""
# backend/test_websocket.py
import websocket
import threading
import time
import json
import os

WS_URL = "ws://localhost:5001/identify"
TEST_AUDIO_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "test_music.mp3") # Make sure this file exists!

def on_message(ws, message):
    print("\n<-- Received from server:")
    data = json.loads(message)
    print(json.dumps(data, indent=2))
    ws.close()

def on_error(ws, error):
    print(f"### WebSocket Error: {error} ###")
    ws.close()

def on_close(ws, close_status_code, close_msg):
    print("### WebSocket Closed ###")

def on_open(ws):
    def run(*args):
        print("--> WebSocket opened. Sending audio file...")
        try:
            with open(TEST_AUDIO_FILE, "rb") as f:
                audio_bytes = f.read()
            
            # Send the binary data
            ws.send(audio_bytes, websocket.ABNF.OPCODE_BINARY)
            print(f"--> Sent {len(audio_bytes)} bytes of audio data.")
            
            # The server will process after the connection closes when the client is done sending
            # In a real streaming scenario, you'd send an 'end' message. For this test,
            # we just close the connection after sending the file.
            time.sleep(1) # Give a moment for data to be sent
            ws.close()
            print("--> Audio sent. Connection closed.")
            
        except FileNotFoundError:
            print(f"ERROR: Test audio file not found at '{TEST_AUDIO_FILE}'")
            ws.close()
            
    threading.Thread(target=run).start()