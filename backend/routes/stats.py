from flask import Blueprint, jsonify, current_app
import logging

stats_bp = Blueprint('stats_bp', __name__)
logger = logging.getLogger(__name__)

@stats_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Endpoint to get database statistics."""
    try:
        db_handler = current_app.extensions['db_handler']
        song_count = db_handler.get_song_count()
        return jsonify({
            'success': True,
            'stats': {
                'song_count': song_count
            }
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'message': 'Failed to retrieve stats.'}), 500
