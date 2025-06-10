-- Create songs table
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    duration_ms INTEGER,
    source_type TEXT NOT NULL,  -- 'youtube', 'spotify', 'file', etc.
    source_id TEXT NOT NULL,    -- YouTube video ID, Spotify track ID, etc.
    cover_url TEXT,             -- URL to album/cover art
    release_date TEXT,          -- Release date (YYYY-MM-DD)
    spotify_url TEXT,           -- Spotify URL if available
    youtube_url TEXT,            -- YouTube URL if available
    youtube_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id)  -- Prevent duplicate entries from same source
);

-- Create fingerprints table
CREATE TABLE IF NOT EXISTS fingerprints (
    hash INTEGER NOT NULL,
    song_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Create index on hash for faster lookups
CREATE INDEX IF NOT EXISTS idx_fingerprints_hash ON fingerprints(hash);

-- Create index on song_id for faster joins
CREATE INDEX IF NOT EXISTS idx_fingerprints_song_id ON fingerprints(song_id);
