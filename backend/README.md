# Shazam Clone - Backend

This is the Flask backend for the Shazam Clone project. It handles audio processing, fingerprinting, database management, and communication with external APIs like Spotify and YouTube.

## Setup

These instructions assume you are in the `backend` directory.

1.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Up Environment Variables:**
    Create a `.env` file in this directory by copying the example:
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file with your credentials and desired database path:
    ```dotenv
    SPOTIFY_CLIENT_ID=your_spotify_client_id
    SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    DB_PATH=/path/to/your/shazam_library.db
    ```

**Note:** The application will create and migrate the database automatically on the first run.

## Running the Server

To start the development server:

```bash
python app.py
```

The server will run on `http://localhost:5001` and will automatically reload on code changes.

## Project Structure

-   `app.py`: Main Flask application entry point.
-   `routes/`: Flask Blueprints for different API routes.
-   `services/`: Business logic for core features (e.g., `SongIngester`).
-   `shazam_core/`: The core audio fingerprinting and matching engine.
-   `database/`: Database handler, models, and migrations.
-   `api_clients/`: Clients for interacting with Spotify and YouTube.
-   `data/`: Default location for the database and temporary audio files (gitignored).
