from flask import Flask, current_app
from flask_cors import CORS
from flask_sock import Sock
from apscheduler.schedulers.background import BackgroundScheduler
import os
from pathlib import Path

app = Flask(__name__)
sock = Sock(app)

# Configuration
DB_PATH = Path('/Users/nikhilselvaraj/Projects/Shazam/shazam_library.db')
app.config['DATABASE'] = str(DB_PATH)

CORS(app)

# Initialize app
with app.app_context():
    try:
        # Database setup
        from database.db_handler import DatabaseHandler
        db_handler = DatabaseHandler(str(DB_PATH))
        app.extensions['db_handler'] = db_handler
        
        # Run migrations
        from database.migrations.v2_add_task_tracking import migrate
        migrate(str(DB_PATH))
        app.logger.info("Database migration completed")
        
        # Initialize services
        from api_clients.spotify_client import SpotifyClient
        from api_clients.youtube_client import YouTubeClient
        from services.song_ingester import SongIngester
        app.extensions['spotify_client'] = SpotifyClient()
        app.extensions['youtube_client'] = YouTubeClient()
        app.extensions['song_ingester'] = SongIngester(
            db_handler=db_handler,
            spotify_client=app.extensions['spotify_client'],
            youtube_client=app.extensions['youtube_client']
        )

        # Register routes
        from routes import songs
        app.register_blueprint(songs.songs_bp)
        
        # Register WebSocket routes
        from routes import websockets
        app.extensions['sock'] = sock  # Store sock in extensions
        websockets.register_websockets(sock)

        from routes import stats
        app.register_blueprint(stats.stats_bp)
        
    except Exception as e:
        app.logger.error(f"Initialization failed: {str(e)}", exc_info=True)
        raise

# Scheduler setup
scheduler = BackgroundScheduler()
# Use a lambda with app.app_context to ensure the db_handler is available.
scheduler.add_job(
    func=lambda: app.app_context().push() or db_handler.cleanup_old_tasks(days=1),
    trigger='interval',
    hours=24
)
try:
    if not scheduler.running:
        scheduler.start()
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()

app.extensions['scheduler'] = scheduler

@app.teardown_appcontext
def shutdown_scheduler(exception=None):
    """Shutdown the scheduler if running"""
    scheduler = current_app.extensions.get('scheduler')
    if scheduler:
        try:
            if scheduler.running:
                scheduler.shutdown()
        except Exception as e:
            current_app.logger.warning(f"Error shutting down scheduler: {str(e)}")

@app.route('/health')
def health_check():
    return "OK", 200

# The standard Flask development server can run this for testing.
# For production, we'll use gunicorn.
if __name__ == '__main__':
    # You can run this directly for development
    # The server will warn you not to use it in production, which is fine.
    app.run(debug=True, host='0.0.0.0', port=5001)
    print("Server starting on http://localhost:5001")