# backend/test_websocket.py
import websocket
import threading
import time
import json
import os

WS_URL = "ws://localhost:5001/identify"
TEST_AUDIO_FILE = "test_music.mp3" # Make sure this file exists!

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

if __name__ == "__main__":
    print("\n--- Testing WebSocket Identification Endpoint ---")
    
    if not os.path.exists(TEST_AUDIO_FILE):
        print(f"FATAL: Please create a test audio file named '{TEST_AUDIO_FILE}' in the backend directory.")
    else:
        websocket.enableTrace(False) # Set to True for verbose debugging
        ws = websocket.WebSocketApp(WS_URL,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        
        print("Connecting to WebSocket...")
        ws.run_forever()