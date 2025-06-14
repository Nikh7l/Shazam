import React, { useState } from 'react';

const SpotifyIngestForm = ({ onIngestionSuccess }) => {
  const [spotifyUrl, setSpotifyUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState({ message: '', type: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setNotification({ message: '', type: '' });

    try {
      const response = await fetch('http://localhost:5001/api/songs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ spotify_url: spotifyUrl }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Failed to start ingestion task.');
      }

      setNotification({ 
        message: `Ingestion started successfully. The song count will update shortly.`,
        type: 'success' 
      });
      setSpotifyUrl('');
      if (onIngestionSuccess) {
        setTimeout(() => onIngestionSuccess(), 2000); // Refresh after a short delay
      }
    } catch (err) {
      setNotification({ message: err.message, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="spotify-ingest-form-container">
      <h3>Ingest from Spotify</h3>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
        Paste a Spotify track or playlist URL to add it to the library.
      </p>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={spotifyUrl}
          onChange={(e) => setSpotifyUrl(e.target.value)}
          placeholder="Enter Spotify URL"
          required
          disabled={isLoading}
          style={{ width: '100%', padding: '12px', marginBottom: '12px', borderRadius: '8px', border: '1px solid #333' }}
        />
        <button 
          type="submit" 
          disabled={isLoading}
          style={{ width: '100%', padding: '12px', borderRadius: '8px', border: 'none', background: 'var(--primary-color)', color: 'white', cursor: 'pointer' }}
        >
          {isLoading ? 'Ingesting...' : 'Add to Library'}
        </button>
      </form>
      {notification.message && (
        <p style={{ 
          color: notification.type === 'error' ? '#ff4d4d' : '#4caf50',
          marginTop: '15px',
          padding: '10px',
          borderRadius: '8px',
          background: notification.type === 'error' ? 'rgba(255, 77, 77, 0.1)' : 'rgba(76, 175, 80, 0.1)'
        }}>
          {notification.message}
        </p>
      )}
    </div>
  );
};

export default SpotifyIngestForm;
