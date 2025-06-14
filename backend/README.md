# Shazam Clone - Backend

This is the backend service for the Shazam clone, providing audio fingerprinting and matching capabilities.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (create a `.env` file in the backend directory):
   ```
   FLASK_ENV=development
   DATABASE_URL=sqlite:///data/fingerprints.db
   ```


## Running the Server

```bash
python app.py
```

The server will start on `http://localhost:5001`.

## API Endpoints

### Health Check
- `GET /api/health` - Check if the API is running

### Songs
- `POST /api/songs` - Add a new song (file upload or YouTube URL)
- `GET /api/songs/<song_id>` - Get song information

### Matching
- `POST /api/match` - Match an audio sample against the database

## Adding Songs

### Via File Upload
```bash
curl -X POST -F "file=@/path/to/audio.mp3" \
     -F "title=Song Title" \
     -F "artist=Artist Name" \
     -F "album=Album Name" \
     http://localhost:5001/api/songs
```

### Via YouTube URL
```bash
curl -X POST -F "youtube_url=https://www.youtube.com/watch?v=VIDEO_ID" \
     -F "title=Song Title" \
     -F "artist=Artist Name" \
     http://localhost:5001/api/songs
```

## Testing

Run the test suite:
```bash
pytest tests/
```

## Project Structure

- `app.py` - Main Flask application
- `shazam_core/` - Core audio processing logic
  - `fingerprinting.py` - Audio fingerprinting implementation
  - `spectrogram.py` - Spectrogram generation
  - `peak_finding.py` - Peak detection algorithms
- `database/` - Database handling
  - `db_handler.py` - Database operations
  - `schema.sql` - Database schema
- `api_clients/` - External API clients
  - `youtube_client.py` - YouTube audio download
  - `spotify_client.py` - Spotify API integration
- `tests/` - Test files
- `data/` - Uploaded files and database (gitignored)
