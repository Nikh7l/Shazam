import os
import sys
import click
import logging
from dotenv import load_dotenv

# Add project root to Python path to allow backend.module imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from backend.database.db_handler import DatabaseHandler
from backend.shazam_core.fingerprinting import Fingerprinter, FingerprintMatcher
from backend.shazam_core.audio_utils import load_audio # Not directly used by CLI but good for context
from backend.services.song_ingester import SongIngester
from backend.api_clients.spotify_client import SpotifyClient
from backend.api_clients.youtube_client import YouTubeClient

dotenv_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(PROJECT_ROOT, "shazam_library.db")

@click.group()
def cli():
    """A simple CLI for the Shazam audio recognition system."""
    pass

@cli.command()
@click.argument('spotify_url')
def ingest(spotify_url):
    """Ingests a song from a Spotify URL into the database."""
    click.echo(f"Initializing components for ingestion...")
    db_handler = DatabaseHandler(db_path=DB_PATH)
    # Ensure tables are created if DB is new
    db_handler._init_db() 
    
    spotify_client = SpotifyClient()
    youtube_client = YouTubeClient()
    ingester = SongIngester(db_handler, spotify_client, youtube_client)
    
    click.echo(f"Attempting to ingest: {spotify_url}")
    result = ingester.ingest_from_spotify(spotify_url)
    
    if result and result.get("success"):
        click.echo(click.style(f"✅ Successfully ingested song: {result.get('title', 'Unknown Title')} (ID: {result['song_id']})", fg='green'))
    else:
        click.echo(click.style(f"❌ FAILED to ingest song. Error: {result.get('error') if result else 'Unknown'}", fg='red'))

@cli.command()
@click.argument('audio_filepath', type=click.Path(exists=True))
@click.option('--min-score', default=10, help='Minimum score to consider a match confident.')
def match(audio_filepath, min_score):
    """Matches an audio file against the song database."""
    click.echo(f"Initializing components for matching...")
    db_handler = DatabaseHandler(db_path=DB_PATH)
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        click.echo(click.style(f"Error: Database '{DB_PATH}' not found or is empty. Please ingest songs first.", fg='red'))
        return
        
    fingerprinter_instance = Fingerprinter()
    matcher = FingerprintMatcher(db_handler=db_handler, fingerprinter_instance=fingerprinter_instance)
    
    click.echo(f"Attempting to match audio file: {audio_filepath}")
    results = matcher.match_file(audio_filepath)
    
    if not results:
        click.echo(click.style("No match found.", fg='yellow'))
        return

    best_match = results[0]
    matched_song_id = best_match['song_id']
    score = best_match['score']
    
    # Fetch song details for better output
    song_details = db_handler.get_song_by_id(matched_song_id)
    title = song_details.get('title', 'Unknown Title') if song_details else 'Unknown Title'
    artist = song_details.get('artist', 'Unknown Artist') if song_details else 'Unknown Artist'

    click.echo(f"--- Match Results ---")
    click.echo(f"  Best Match Song ID: {matched_song_id}")
    click.echo(f"  Title: {title}")
    click.echo(f"  Artist: {artist}")
    click.echo(f"  Score (Aligned Hashes): {score}")
    
    if score >= min_score:
        click.echo(click.style(f"✅ Confident Match!", fg='green'))
    else:
        click.echo(click.style(f"⚠️ Low score match. (Threshold: {min_score})", fg='yellow'))

if __name__ == '__main__':
    # Create the downloads directory if it doesn't exist, for song ingester
    # This directory is used by SongIngester and also for temporary live recordings by the API.
    downloads_temp_dir = os.path.join(PROJECT_ROOT, 'temp_downloads') 
    os.makedirs(downloads_temp_dir, exist_ok=True)
    cli()
