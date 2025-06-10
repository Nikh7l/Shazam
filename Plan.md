### **Phase 1: The Core Algorithm (Backend - Python)**

*   **Task 1.1: Audio Pre-processing Setup:**
    *   Set up a function to handle audio files. You will need a way to decode various formats (like MP3) into raw audio data (PCM/WAV). The video uses **FFmpeg** for this, which is a robust choice. Your function should:
        *   Convert the input audio to a standardized format (e.g., mono channel, 16-bit WAV).
        *   Downsample the audio to a lower sample rate (e.g., 11,025 Hz, as mentioned in the video) to reduce processing overhead.

*   **Task 1.2: Spectrogram Generation:**
    *   Implement the Short-Time Fourier Transform (STFT). This involves:
        1.  **Windowing:** Slicing the raw audio data into small, overlapping chunks (windows).
        2.  **Applying a Window Function:** For each chunk, apply a function like the **Hamming window** to reduce spectral leakage (artifacts at the edges of each chunk).
        3.  **Applying FFT:** Run the Fast Fourier Transform on each windowed chunk to get its frequency components.
    *   The output will be a 2D array (a matrix) of complex numbers, representing the spectrogram.

*   **Task 1.3: Peak Finding (Constellation Map):**
    *   Create a function that iterates through your spectrogram matrix.
    *   Identify local maxima, which are the "peaks" or the brightest points. These are points with higher intensity than their neighbors.
    *   To make this more robust (like Shazam), divide the frequency axis into logarithmic bands and find the strongest peak within each band for each time slice. This prevents low-frequency noise from dominating.

*   **Task 1.4: Hash Generation:**
    *   This is the fingerprinting magic. For each peak (let's call it an **anchor peak**):
        1.  Define a **target zone**—a rectangular area of the spectrogram that appears shortly after the anchor peak.
        2.  Identify a set number of peaks (e.g., 5) within that target zone. These are your **target peaks**.
        3.  For each `(anchor, target)` pair, create a unique hash. The hash should be a combination of:
            *   The frequency of the anchor peak (`freq1`).
            *   The frequency of the target peak (`freq2`).
            *   The time difference between them (`t2 - t1`).
        4.  Combine these three values into a single, compact hash (e.g., a 32-bit integer).

### **Phase 2: The Database**

You need a place to store the fingerprints and information about the songs. For a project like this, **SQLite** is a simple and excellent choice.

*   **Task 2.1: Design the Database Schema:**
    *   **`songs` table:** To store metadata.
        *   `song_id` (Primary Key, e.g., `song_A`)
        *   `title` (text)
        *   `artist` (text)
        *   `album` (text)
        *   `youtube_id` (text, for playback)
    *   **`fingerprints` table:** To store the hashes.
        *   `hash` (integer, your 32-bit hash)
        *   `song_id` (Foreign Key to `songs` table)
        *   `timestamp` (integer, the time of the *anchor peak* in milliseconds)
    *   **Index the `hash` column** in the `fingerprints` table for incredibly fast lookups.

### **Phase 3: Populating the Database (Ingestion Pipeline)**

You need to get songs into your system to be able to match against them.

*   **Task 3.1: Create an "Add Song" Backend Endpoint:** This function will orchestrate the process.
*   **Task 3.2: Integrate with Spotify API:**
    *   Set up a developer account with Spotify.
    *   Write a function that takes a Spotify track, album, or playlist URL.
    *   Use the Spotify API to fetch the metadata (title, artist, album) for the song(s).
*   **Task 3.3: Fetch Audio from YouTube:**
    *   Using the metadata from Spotify, create a search query (e.g., "Banners Got It In You Official Audio").
    *   Use the YouTube API or a command-line wrapper like `yt-dlp` to search for the song and download its audio.
*   **Task 3.4: The Ingestion Process:**
    1.  The "Add Song" endpoint receives the Spotify link.
    2.  It calls the Spotify API to get metadata.
    3.  It finds and downloads the audio from YouTube.
    4.  It runs the entire **Phase 1 Algorithm** on the downloaded audio to generate a full set of fingerprints.
    5.  It saves the song's metadata to the `songs` table and all its fingerprints to the `fingerprints` table.

### **Phase 4: The User Interface (Frontend - React)**

Now, build the user-facing part. The video uses **ReactJS**.

*   **Task 4.1: UI Scaffolding:**
    *   Set up a new React project (`create-react-app` or Vite).
    *   Design the main components: a central "Listen" button, icons for microphone and file upload, and an input field for adding new Spotify songs.
*   **Task 4.2: Audio Input:**
    *   **Microphone:** Use the `navigator.mediaDevices.getUserMedia` Web API to request microphone access and record a short audio snippet (e.g., 5-10 seconds).
    *   **File Upload:** Create a file input that allows users to upload an audio file from their computer.
*   **Task 4.3: Results Display:**
    *   Create a component to display the matching song. It should show the song's YouTube video embedded in an iframe, starting at the correct timestamp. A carousel for multiple matches is a nice touch.

### **Phase 5: Connecting Frontend and Backend (The Matching Process)**

This is where you bring it all together. The video uses **WebSockets** for fast, bi-directional communication.

*   **Task 5.1: Create the Matching Endpoint on the Backend:**
    *   Set up a WebSocket server in Go.
    *   This endpoint will accept a raw audio snippet from the client.
*   **Task 5.2: Implement the Client-Side Logic:**
    1.  When the user records or uploads an audio snippet, the React frontend runs **Phase 1's algorithm** on it (Spectrogram -> Peaks -> Hashes).
    2.  The client sends this list of hashes to the backend via WebSocket.
*   **Task 5.3: Implement the Server-Side Matching Logic:**
    1.  The backend receives the hashes from the snippet.
    2.  It queries the `fingerprints` database for all records that match any of the snippet's hashes.
    3.  It groups the results by `song_id`.
    4.  **Crucially, it performs the Time Coherence check:**
        *   For each candidate song, it calculates a score.
        *   It iterates through the matching hash pairs and finds the difference between the snippet's anchor times and the song's anchor times.
        *   If the time differences are consistent (within a small tolerance), it increments that song's score.
    5.  It sorts the candidate songs by their final score in descending order.
    6.  It fetches the full metadata for the top-scoring song(s) from the `songs` table.
    7.  It sends this final result (song metadata, YouTube ID, and the match timestamp) back to the frontend.

By following this plan, you will have systematically recreated the entire logic and architecture of the Shazam clone shown in the video. Good luck