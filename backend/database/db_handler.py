from re import DEBUG
import sqlite3
from typing import List, Tuple, Any, TYPE_CHECKING, Optional
import json
import logging

if TYPE_CHECKING:
    from shazam_core.fingerprinting import Fingerprint # For type hinting
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class DatabaseHandler:
    def __init__(self, db_path: str = 'data/fingerprints.db'):
        """Initialize the database handler.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()
    
    def _get_connection(self):
        """Create a new database connection."""
        return sqlite3.connect(self.db_path, timeout=30.0)  # 30-second timeout for locked db
    
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _init_db(self):
        """Initialize the database by running schema.sql."""
        with self._get_connection() as conn:
            with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r') as f:
                conn.executescript(f.read())
    
    def add_song(
        self,
        title: str,
        artist: str,
        source_type: str,
        source_id: str,
        album: str = None,
        duration_ms: int = None,
        cover_url: str = None,
        release_date: str = None,
        spotify_url: str = None,
        youtube_id: str = None,
    ) -> int:
        # Debug log all parameters being passed to add_song
        logger.debug(f"add_song called with parameters:")
        logger.debug(f"  title: {title} (type: {type(title)})")
        logger.debug(f"  artist: {artist} (type: {type(artist)})")
        logger.debug(f"  source_type: {source_type} (type: {type(source_type)})")
        logger.debug(f"  source_id: {source_id} (type: {type(source_id)})")
        logger.debug(f"  album: {album} (type: {type(album) if album is not None else 'None'})")
        logger.debug(f"  duration_ms: {duration_ms} (type: {type(duration_ms) if duration_ms is not None else 'None'})")
        logger.debug(f"  cover_url: {cover_url} (type: {type(cover_url) if cover_url is not None else 'None'})")
        logger.debug(f"  release_date: {release_date} (type: {type(release_date) if release_date is not None else 'None'})")
        logger.debug(f"  spotify_url: {spotify_url} (type: {type(spotify_url) if spotify_url is not None else 'None'})")
        logger.debug(f"  youtube_id: {youtube_id} (type: {type(youtube_id) if youtube_id is not None else 'None'})")
        """Add a new song to the database.
        
        Args:
            title: Song title
            artist: Artist name
            source_type: Source type ('youtube', 'spotify', 'file', etc.)
            source_id: Source-specific ID (YouTube video ID, Spotify track ID, etc.)
            album: Album name (optional)
            duration_ms: Duration in milliseconds (optional)
            cover_url: URL to album/cover art (optional)
            release_date: Release date in YYYY-MM-DD format (optional)
            spotify_url: Spotify URL (optional)
            youtube_id: YouTube URL (optional)
            
        Returns:
            int: The ID of the newly inserted song
            
        Raises:
            sqlite3.IntegrityError: If a song with the same source_type and source_id already exists
        """
        logger.debug(f"Executing SQL with parameters: {locals()}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Explicit type conversion
                params = (
                    str(title) if title is not None else '',
                    str(artist) if artist is not None else '',
                    str(album) if album is not None else '',
                    str(source_type),
                    str(source_id),
                    int(duration_ms) if duration_ms is not None else None,
                    str(cover_url) if cover_url is not None else None,
                    str(release_date) if release_date is not None else None,
                    str(spotify_url) if spotify_url is not None else None,
                    str(youtube_id) if youtube_id is not None else None
                )
                
                logger.debug(f"Final parameters tuple: {params}")
                logger.debug(f"Parameter types: {tuple(type(p) for p in params)}")
                
                sql = """
                INSERT INTO songs (
                    title, artist, album, source_type, source_id, duration_ms,
                    cover_url, release_date, spotify_url, youtube_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_type, source_id) 
                DO NOTHING
                """
                
                logger.debug(f"Executing SQL: {sql}")
                logger.debug(f"With parameters: {params}")
                
                cursor.execute(sql, params)
                conn.commit()
                logger.debug("SQL executed successfully")
                
                # If the insert happened, get the new ID. If it was ignored, get the existing ID.
                if cursor.lastrowid == 0:
                    cursor.execute('SELECT id FROM songs WHERE source_type = ? AND source_id = ?', (source_type, source_id))
                else:
                     cursor.execute('SELECT last_insert_rowid()')

                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Parameters: {params}")
            logger.error(f"Parameter types: {tuple(type(p) for p in params) if 'params' in locals() else 'N/A'}")
            return None
    
    def get_song_by_source(self, source_type: str, source_id: str) -> Optional[Dict[str, Any]]:
        """Get a song by its source type and ID.
        
        Args:
            source_type: Source type ('youtube', 'spotify', etc.)
            source_id: Source-specific ID
            
        Returns:
            Song dictionary or None if not found
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM songs WHERE source_type = ? AND source_id = ?',
                (source_type, source_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_songs(self) -> List[Dict[str, Any]]:
        """Get a list of all songs in the database."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs ORDER BY artist, title')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_song(self, song_id: int) -> bool:
        """Delete a song and all its associated fingerprints."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # First, delete fingerprints to maintain referential integrity
            cursor.execute('DELETE FROM fingerprints WHERE song_id = ?', (song_id,))
            # Then, delete the song
            cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
            conn.commit()
            # Return True if a row was affected (i.e., the song was deleted)
            return cursor.rowcount > 0
    
    def add_fingerprints(self, song_id: int, fingerprints: List[Tuple[int, int]]) -> None:
        """Add fingerprints for a song.
        
        Args:
            song_id: ID of the song
            fingerprints: List of (hash, timestamp) tuples
        """
        logging.info(f"[DB_HANDLER] add_fingerprints: Received {len(fingerprints)} fingerprints to add.")
        if not fingerprints:
            return

        data_to_insert = [(fp.hash, song_id, int(fp.offset)) for fp in fingerprints]
        if data_to_insert:
            logging.info(f"[DB_HANDLER] add_fingerprints: First 3 fingerprints to insert for song_id {song_id} [(hash, song_id, offset)]: {data_to_insert[:3]}")
        with self._get_connection() as conn:
            conn.executemany(
                'INSERT INTO fingerprints (hash, song_id, timestamp) VALUES (?, ?, ?)',
                data_to_insert
            )
            conn.commit()
        logging.info(f"[DB_HANDLER] add_fingerprints: Successfully added {len(fingerprints)} fingerprints.")

    def store_fingerprints(self, song_id: int, fingerprints: List[Tuple[int, int]]):
        """Store audio fingerprints for a song.
        
        Args:
            song_id: ID of the song (will be converted to int)
            fingerprints: List of (hash, timestamp) tuples (will be converted to int)
        """
        logging.info(f"[DB_HANDLER] store_fingerprints: Received {len(fingerprints)} fingerprints to store for song_id {song_id}.")
        if not fingerprints:
            logging.info(f"[DB_HANDLER] store_fingerprints: No fingerprints to store for song_id {song_id}.")
            return

        try:
            song_id_int = int(song_id)
            data = [(int(hash_val), song_id_int, int(timestamp)) 
                   for hash_val, timestamp in fingerprints]
            
            if data:
                logging.info(f"[DB_HANDLER] store_fingerprints: First {min(3, len(data))} processed fingerprints for song_id {song_id_int}: {data[:3]}")

            with self._get_connection() as conn:
                conn.executemany(
                    'INSERT OR IGNORE INTO fingerprints (hash, song_id, timestamp) VALUES (?, ?, ?)',
                    data
                )
                conn.commit()  # Ensure changes are committed
            logging.info(f"[DB_HANDLER] store_fingerprints: Successfully processed and attempted to insert {len(data)} fingerprints for song_id {song_id_int}.")
                
        except (ValueError, TypeError) as e:
            logging.error(f"Error storing fingerprints for song_id {song_id}: {e}")
            raise
    
    def get_matches_by_hashes(self, hashes: List[int]) -> List[Tuple[int, int, int]]:
        """
        Finds matching fingerprints in the database using a safe and standard query.
        """
        logging.info(f"[DB_HANDLER] get_matches_by_hashes: Received {len(hashes)} query hashes.")
        if hashes:
            logging.info(f"[DB_HANDLER] get_matches_by_hashes: First {min(3, len(hashes))} query hashes: {hashes[:3]}")
        else:
            logging.info("[DB_HANDLER] get_matches_by_hashes: No query hashes received, returning empty list.")
            return []

        # Create a string of placeholders (?, ?, ?, ...)
        placeholders = ', '.join('?' for _ in hashes)
        
        # The query is now much cleaner and safer
        query = f"SELECT hash, song_id, timestamp FROM fingerprints WHERE hash IN ({placeholders})"

        with self._get_connection() as conn:
            try:
                cursor = conn.cursor()
                logging.info(f"[DB_HANDLER] get_matches_by_hashes: Executing query for {len(hashes)} hashes. First 3: {hashes[:3] if hashes else 'N/A'}")
                cursor.execute(query, hashes)
                results = cursor.fetchall()
                logging.info(f"[DB_HANDLER] get_matches_by_hashes: DB query returned {len(results)} rows. First 3: {results[:3] if results else 'N/A'}")
                return results
            except sqlite3.Error as e:
                # Log the specific database error for better debugging
                logging.error(f"[DB_HANDLER] Database query failed for hashes {hashes[:3] if hashes else 'N/A'}...: {e}")
                return []
    
    def get_song_by_id(self, song_id: int) -> Optional[Dict[str, Any]]:
        """Get song metadata by ID.
        
        Args:
            song_id: ID of the song
            
        Returns:
            Dictionary with song metadata or None if not found
        """
        with self._get_connection() as conn:
            logger.debug(f"Executing SELECT by ID with parameter: {song_id} (type: {type(song_id)})")
            cursor = conn.execute(
                'SELECT id, title, artist, album, youtube_id FROM songs WHERE id = ?',
                (song_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'artist': row[2],
                    'album': row[3],
                    'youtube_id': row[4]
                }
            return None

    def get_song_by_spotify_url(self, spotify_url: str) -> Optional[Dict[str, Any]]:
        """Get a song by its Spotify URL.
        
        Args:
            spotify_url: The full Spotify URL of the track
            
        Returns:
            Song dictionary or None if not found
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            logger.debug(f"Executing SELECT by Spotify URL with parameter: {spotify_url} (type: {type(spotify_url)})")
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM songs WHERE spotify_url = ?',
                (spotify_url,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def verify_connection(self):
        """Verify the database connection is active and tables exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Debug: List all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                all_tables = cursor.fetchall()
                logger.debug(f"[DEBUG] Found tables: {all_tables}")
                
                # Check for our specific table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='background_tasks'")
                result = cursor.fetchone()
                logger.debug(f"[DEBUG] background_tasks check: {result}")
                
                if not result:
                    raise RuntimeError("background_tasks table not found")
        except Exception as e:
            logger.error(f"[ERROR] Verification failed: {str(e)}")
            raise RuntimeError(f"Database verification failed: {str(e)}")

    def create_task(self, task_id, task_type, spotify_url, total_items=1):
        """Create a new background task record"""
        self.verify_connection()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO background_tasks (task_id, task_type, spotify_url, status, total_items) "
                "VALUES (?, ?, ?, 'pending', ?)",
                (task_id, task_type, spotify_url, total_items)
            )
            conn.commit()

    def get_task(self, task_id):
        """Get task by task_id."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    task_id, task_type, spotify_url, status, created_at, 
                    started_at, completed_at, processed_items, total_items, result_json
                FROM background_tasks 
                WHERE task_id = ?
                """,
                (task_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_task_progress(self, task_id, processed_items=None, total_items=None):
        """Update task progress"""
        if processed_items is None and total_items is None:
            return

        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            if processed_items is not None:
                updates.append("processed_items = ?")
                params.append(processed_items)
            if total_items is not None:
                updates.append("total_items = ?")
                params.append(total_items)
            
            if not updates:
                return

            params.append(task_id)
            query = f"UPDATE background_tasks SET {', '.join(updates)} WHERE task_id = ?"
            cursor.execute(query, tuple(params))
            conn.commit()

    def complete_task(self, task_id, result_json):
        """Mark task as completed"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE background_tasks SET status = 'completed', "
                "completed_at = CURRENT_TIMESTAMP, result_json = ? "
                "WHERE task_id = ?",
                (json.dumps(result_json), task_id)
            )
            conn.commit()

    def cleanup_old_tasks(self, days: int = 7):
        """Delete tasks that were completed more than a certain number of days ago."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Use julianday for reliable date comparisons with TEXT dates
            cursor.execute(
                """DELETE FROM background_tasks 
                   WHERE status = 'completed' AND 
                   julianday('now') - julianday(completed_at) > ?""",
                (days,)
            )
            conn.commit()
            logger.info(f"Cleaned up {cursor.rowcount} old tasks.")
    def get_song_count(self):
        """Get the total number of songs in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM songs")
            count = cursor.fetchone()[0]
            return count


