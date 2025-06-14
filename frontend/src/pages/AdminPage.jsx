// frontend/src/pages/AdminPage.jsx
import React, { useState, useEffect } from 'react';
import SpotifyIngestForm from '../components/SpotifyIngestForm.jsx';

function AdminPage() {
  const [songCount, setSongCount] = useState(null);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:5001/api/stats');
      const data = await response.json();
      if (data.success) {
        setSongCount(data.stats.song_count);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="main-content">
      <div className="container" style={{ paddingTop: '40px', maxWidth: '700px', margin: '0 auto', textAlign: 'center' }}>
        <h2>Manage Database</h2>
        {songCount !== null ? (
          <p style={{ color: 'var(--text-secondary)', marginBottom: '40px', fontSize: '1.2rem' }}>
            There are currently <strong>{songCount}</strong> songs in the library.
          </p>
        ) : (
          <p style={{ color: 'var(--text-secondary)', marginBottom: '40px' }}>
            Loading stats...
          </p>
        )}
        <SpotifyIngestForm onIngestionSuccess={fetchStats} />
      </div>
    </div>
  );
}

export default AdminPage;