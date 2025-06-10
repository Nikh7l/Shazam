Excellent! Using Python for the backend and React for the frontend is a powerful and popular combination. Here is a detailed coding plan, broken down into a directory structure with file-by-file tasks, presented in markdown for easy tracking.

---

## Shazam Clone: Python & React Project Plan

This plan outlines the directory structure, key files, and the tasks required for each part of the application.

### **I. Project Setup & Dependencies**

-   **[ ] Task 0.1: Initialize Project Structure**
    -   Create a main project folder (e.g., `shazam`).
    -   Inside, create `backend` and `frontend` directories.

-   **[ ] Task 0.2: Backend Dependencies (Python)**
    -   Create a virtual environment (`python -m venv venv`).
    -   Create a `requirements.txt` file in the `backend` directory and add the following:
        ```
        flask
        flask_sockets
        numpy
        scipy
        pydub
        spotipy
        yt-dlp
        ```
    -   Install dependencies: `pip install -r requirements.txt`.

-   **[ ] Task 0.3: Frontend Dependencies (React)**
    -   Navigate to the `frontend` directory and initialize a React project: `npx create-react-app .` or `npm create vite@latest . -- --template react`.
    -   Install necessary libraries: `npm install axios react-youtube`.

### **II. Directory & File Structure**

```
shazam/
├── backend/
│   ├── app.py                  # Main Flask server, API routes, and WebSocket handlers
│   ├── shazam_core/
│   │   ├── __init__.py
│   │   ├── fingerprinting.py   # Main audio fingerprinting logic
│   │   ├── spectrogram.py      # Spectrogram generation (STFT)
│   │   └── peak_finding.py     # Logic to find peaks in the spectrogram
│   ├── database/
│   │   ├── db_handler.py       # Functions to interact with the database
│   │   └── schema.sql          # SQL script to initialize tables
│   ├── api_clients/
│   │   ├── __init__.py
│   │   ├── spotify_client.py   # Functions to interact with Spotify API
│   │   └── youtube_client.py   # Functions to download audio from YouTube
│   ├── data/                   # (Should be in .gitignore)
│   │   ├── fingerprints.db     # SQLite database file
│   │   └── mp3s/               # Temporary storage for downloaded songs
│   └── requirements.txt
└── frontend/
    ├── public/
    ├── src/
    │   ├── components/
    │   │   ├── ListenButton.js     # The main circular button
    │   │   ├── AudioInput.js       # Component for mic/upload buttons
    │   │   ├── AddSongForm.js      # Form to submit Spotify links
    │   │   ├── ResultsDisplay.js   # Component to show matched video
    │   │   └── LoadingSpinner.js   # Visual feedback during processing
    │   ├── hooks/
    │   │   └── useAudioRecorder.js # Custom hook for microphone logic
    │   ├── services/
    │   │   └── websocketService.js # Manages WebSocket connection
    │   ├── App.js
    │   ├── App.css
    │   └── index.js
    └── package.json
```

### **III. Backend Development Plan (Python/Flask)**

#### `backend/database/schema.sql`
- **[ ] Task 1.1:** Define SQL for creating two tables:
    - **`songs` table:** `id` (PK), `title`, `artist`, `album`, `youtube_id`.
    - **`fingerprints` table:** `hash` (INTEGER), `song_id` (FK), `timestamp` (INTEGER).
- **[ ] Task 1.2:** Create an index on the `hash` column of the `fingerprints` table.

#### `backend/database/db_handler.py`
- **[ ] Task 2.1:** Implement `init_db()` to create the database and tables from `schema.sql`.
- **[ ] Task 2.2:** Implement `add_song(metadata)` to insert a new song's info into the `songs` table.
- **[ ] Task 2.3:** Implement `store_fingerprints(song_id, fingerprints)` to save a list of hashes and their timestamps.
- **[ ] Task 2.4:** Implement `get_matches_by_hashes(hashes)` to query the `fingerprints` table and return all matching records.
- **[ ] Task 2.5:** Implement `get_song_by_id(song_id)` to retrieve song metadata.

#### `backend/shazam_core/spectrogram.py`
- **[ ] Task 3.1:** Create a function `generate_spectrogram(audio_data, sample_rate)`.
- **[ ] Task 3.2:** Inside, use `scipy.signal.stft` to perform the Short-Time Fourier Transform.
- **[ ] Task 3.3:** Ensure you apply a windowing function like `hann` or `hamming` as part of the STFT process.

#### `backend/shazam_core/peak_finding.py`
- **[ ] Task 4.1:** Create a function `find_peaks(spectrogram)`.
- **[ ] Task 4.2:** Divide the frequency dimension into logarithmic bands (e.g., 0-500Hz, 500-1kHz, etc.).
- **[ ] Task 4.3:** Iterate through time slices and find the point of maximum magnitude (the peak) within each frequency band.
- **[ ] Task 4.4:** Filter these peaks to keep only the most prominent ones, using a dynamic threshold based on the average magnitude.

#### `backend/shazam_core/fingerprinting.py`
- **[ ] Task 5.1:** Create the main function `generate_fingerprints(audio_path)`.
- **[ ] Task 5.2:** Use `pydub` to load the audio, convert to mono, and downsample.
- **[ ] Task 5.3:** Call `generate_spectrogram()` and `find_peaks()` to get the constellation map.
- **[ ] Task 5.4:** Implement the hashing logic: iterate through each peak (anchor) and its neighbors in a "target zone" to create `(freq1, freq2, time_delta)` tuples.
- **[ ] Task 5.5:** Convert each tuple into a single hash value.

#### `backend/api_clients/spotify_client.py` & `youtube_client.py`
- **[ ] Task 6.1:** (`spotify_client.py`) Create a function using `spotipy` to take a URL and return a dictionary of track metadata.
- **[ ] Task 6.2:** (`youtube_client.py`) Create a function using `yt-dlp` to search YouTube with song title/artist and download the best match as an MP3 to a temporary folder.

#### `backend/app.py`
- **[ ] Task 7.1:** Set up a basic Flask application with Flask-Sockets.
- **[ ] Task 7.2:** Create a REST endpoint `/add-song` (POST) that:
    - Takes a Spotify URL.
    - Uses the API clients to get metadata and download the audio.
    - Calls the `fingerprinting.py` logic to generate hashes.
    - Uses the `db_handler.py` to store everything in the database.
- **[ ] Task 7.3:** Create a WebSocket route `/match` that:
    - Receives a raw audio snippet (e.g., in Base64).
    - Decodes it and runs it through the fingerprinting process to get hashes.
    - Queries the database for matching hashes.
    - Performs the time coherence check to score candidate songs.
    - Returns the best match (or top 3) to the client.

### **IV. Frontend Development Plan (React)**

#### `frontend/src/App.js`
- **[ ] Task 8.1:** Set up the main layout with the `ListenButton`, `AddSongForm`, and `ResultsDisplay` components.
- **[ ] Task 8.2:** Manage the application's state: `isLoading`, `matchResult`, `error`.
- **[ ] Task 8.3:** Initialize the WebSocket connection in a `useEffect` hook.

#### `frontend/src/hooks/useAudioRecorder.js`
- **[ ] Task 9.1:** Create a custom hook to handle microphone recording logic.
- **[ ] Task 9.2:** Use `navigator.mediaDevices.getUserMedia` to start recording.
- **[ ] Task 9.3:** Use the `MediaRecorder` API to capture audio chunks and compile them into a Blob when stopped.

#### `frontend/src/components/AudioInput.js`
- **[ ] Task 10.1:** Use the `useAudioRecorder` hook for the microphone button.
- **[ ] Task 10.2:** On record stop, convert the audio Blob to a Base64 string and send it over the WebSocket for matching.
- **[ ] Task 10.3:** Implement the file upload button using a file input, read the file as a Base64 string, and send it for matching.

#### `frontend/src/components/AddSongForm.js`
- **[ ] Task 11.1:** Create a form with a single text input and a submit button.
- **[ ] Task 11.2:** On submit, use `axios` to make a POST request to the backend's `/add-song` endpoint with the Spotify URL.

#### `frontend/src/components/ResultsDisplay.js`
- **[ ] Task 12.1:** Conditionally render based on the `matchResult` state from `App.js`.
- **[ ] Task 12.2:** If a match is found, use the `react-youtube` library to embed the video.
- **[ ] Task 12.3:** Use the `opts` prop of the YouTube component to set `playerVars.start` to the timestamp returned by the backend.

This structured plan allows you to tackle the project in logical phases, starting with the database, moving to the core algorithm, and finally building the user-facing elements. Good luck with your project