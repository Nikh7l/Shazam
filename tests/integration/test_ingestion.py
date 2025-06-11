"""Integration tests for the song ingestion process via API endpoints,
including metadata fetching and storage.

This script covers Spotify and YouTube song ingestion.
"""
import os
import sys
import json
import time
import requests
from dotenv import load_dotenv

# Add parent directory to path

# Load environment variables
load_dotenv()

# API configuration
BASE_URL = "http://localhost:5001"

# Test data
SPOTIFY_TEST_URL = "https://open.spotify.com/track/5CQ30WqJwcep0pYcV4AMNc"  # Stairway to Heaven - Led Zeppelin
YOUTUBE_TEST_URL = "https://www.youtube.com/watch?v=fJ9rUzIMcZQ"  # Bohemian Rhapsody - Queen
YOUTUBE_TEST_QUERY = "Bohemian Rhapsody Queen"

def test_spotify_ingestion():
    """Test adding a song from Spotify."""
    print("\n=== Testing Spotify Ingestion ===")
    url = f"{BASE_URL}/api/songs/"
    
    # Test with valid URL
    print("Testing with valid Spotify URL...")
    response = requests.post(url, json={"url": SPOTIFY_TEST_URL})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
    # Test with missing URL
    print("\nTesting with missing URL...")
    response = requests.post(url, json={})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

def test_youtube_ingestion():
    """Test adding a song from YouTube."""
    print("\n=== Testing YouTube Ingestion ===")
    url = f"{BASE_URL}/api/songs/youtube"
    
    # Test with valid URL
    print("Testing with valid YouTube URL...")
    response = requests.post(url, json={"url": YOUTUBE_TEST_URL})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
    # Test with search query
    print("\nTesting with search query...")
    response = requests.post(url, json={"url": YOUTUBE_TEST_QUERY})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

def test_song_search():
    """Test searching for songs."""
    print("\n=== Testing Song Search ===")
    url = f"{BASE_URL}/api/songs/search"
    
    # Search for a song
    print("Searching for 'Bohemian'...")
    response = requests.get(url, params={"q": "Bohemian"})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    
    # Search with limit
    print("\nSearching with limit...")
    response = requests.get(url, params={"q": "Queen", "limit": 1})
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
