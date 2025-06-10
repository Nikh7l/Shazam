# backend/app.py
from flask import Flask
from flask_cors import CORS

# Import your Blueprints
from routes.songs import songs_bp
from routes.websockets import ws_bp # <-- Import the new WebSocket Blueprint

# Initialize Flask App
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Register your REST API blueprint
app.register_blueprint(songs_bp)

# Register your WebSocket blueprint
app.register_blueprint(ws_bp)


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