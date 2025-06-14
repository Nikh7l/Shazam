# Shazam Clone: A Full-Stack Music Recognition App

This project is a full-stack implementation of a music recognition service, inspired by Shazam. It uses a custom Python audio fingerprinting engine, a Flask REST API, and a React frontend to identify songs from live audio.

## Key Features

- **Live Audio Recognition:** Captures a 7-second audio clip from the user's microphone and identifies the song.
- **Robust Fingerprinting:** Implements a custom audio fingerprinting algorithm based on spectrogram analysis and combinatorial hashing to ensure accurate matching.
- **Spotify & YouTube Integration:** Fetches song metadata from Spotify and displays the corresponding music video from YouTube upon a successful match.
- **Asynchronous Song Ingestion:** An admin panel allows users to add songs or entire Spotify playlists to the recognition database. The ingestion process (downloading, fingerprinting, and storing) runs as a background task.
- **RESTful Backend:** A Flask-based backend that exposes a clean API for the frontend and manages the song database.
- **Modern Frontend:** A responsive and interactive user interface built with React and Vite.

For a detailed explanation of the fingerprinting algorithm, see [Audio Fingerprinting Explained](./audio_fingerprinting_explanation.md).

## How It Works (Architecture)

The application is composed of three main parts:

1.  **Core Fingerprinting Engine (`shazam_core`):** A Python library responsible for the heavy lifting of audio processing. It converts audio into a spectrogram, identifies unique peaks (landmarks), and generates a set of robust hashes that act as the song's fingerprint.
2.  **Flask Backend (REST API):** This is the central nervous system. It serves the React frontend, provides API endpoints for matching live audio and ingesting new songs, communicates with external APIs (Spotify, YouTube), and manages the SQLite database.
3.  **React Frontend:** The user-facing single-page application (SPA). It captures audio using the browser's `MediaRecorder` API, sends it to the backend for matching, and displays the results, including the embedded YouTube player.

## Technology Stack

-   **Backend:**
    -   Python 3, Flask, Waitress (as a production-grade WSGI server)
    -   `pydub`, `numpy`, `scipy` for audio processing
    -   `spotipy` for Spotify API communication
    -   `yt-dlp` for downloading audio from YouTube
    -   `SQLite` for the database
    -   `concurrent.futures` for background task processing

-   **Frontend:**
    -   React, Vite
    -   JavaScript (ES6+)
    -   `react-youtube` for video playback
    -   Standard Fetch API for backend communication

## Screenshots

### Main Application Interface
![Main Application Interface](./docs/images/shazam%20mainpage.png)

### Song Identified View
![Song Identified View](./docs/images/song%20identified.png)

## Setup and Installation

### Prerequisites

-   Python 3.8+
-   Node.js 16+
-   `ffmpeg` (must be installed and available in your system's PATH for audio conversion)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/shazam-clone.git
cd shazam-clone
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Create a .env file and add your API keys
cp .env.example .env
SPOTIFY_CLIENT_ID =
SPOTIFY_CLIENT_SECRET = 
DB_PATH = # Path to the db 
# Now, edit the .env file with your credentials
```
Get you Spotify Client ID and Secret [Spotify Docs](https://developer.spotify.com/documentation/web-api/tutorials/getting-started).

**Note:** The application will automatically create the `shazam_library.db` SQLite database on first run.

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

## Running the Application

1.  **Start the Backend Server:**
    From the `backend` directory:
    ```bash
    python app.py
    ```
    The backend will be running at `http://localhost:5001`.

2.  **Start the Frontend Dev Server:**
    From the `frontend` directory (in a new terminal):
    ```bash
    npm run dev
    ```
    The frontend will be available at `http://localhost:5173`.

Now, open your browser to `http://localhost:5173` to use the application.
