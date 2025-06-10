# Shazam Clone

A Python and React-based implementation of a music recognition service similar to Shazam.

## Project Structure

```
shazam/
├── backend/               # Python/Flask backend
│   ├── shazam_core/      # Core audio processing logic
│   ├── database/         # Database models and handlers
│   ├── api_clients/      # External API clients (Spotify, YouTube)
│   └── data/             # Data storage (database, audio files)
└── frontend/             # React frontend
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Activate the virtual environment:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```
     .\venv\Scripts\activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the `backend` directory with your API keys:
   ```
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Start the Backend

From the `backend` directory:
```bash
flask run
```

### Start the Frontend

From the `frontend` directory:
```bash
npm start
```

## Features

- Audio fingerprinting using spectrogram analysis
- Song matching against a database of known songs
- Web interface for recording and matching audio
- Integration with Spotify and YouTube for song metadata and playback

## Next Steps

- [ ] Implement audio processing pipeline
- [ ] Build the React frontend
- [ ] Add user authentication
- [ ] Deploy the application
