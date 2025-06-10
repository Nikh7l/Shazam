// frontend/src/pages/AdminPage.jsx
import React from 'react';
import AddSongForm from '../components/AddSongForm.jsx';

function AdminPage() {
  return (
    <div className="main-content">
      <div className="container" style={{ paddingTop: '40px' }}>
        <h2>Manage Database</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Add new songs, albums, or playlists for the algorithm to recognize.
        </p>
        <AddSongForm />
      </div>
    </div>
  );
}

export default AdminPage;