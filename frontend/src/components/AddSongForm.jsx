// frontend/src/components/AddSongForm.jsx
import React, { useState } from 'react';
import { addSongFromSpotify } from '../services/apiService'; // <-- Import the service
import '../styles/AddSongForm.css';

function AddSongForm() {
  const [url, setUrl] = useState('');
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) return;
    
    setMessage('Adding song to database...');
    setIsError(false);

    try {
      const response = await addSongFromSpotify(url);
      if (response.data.success) {
        setMessage(`Success! Song "${response.data.title}" ${response.data.status}.`);
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }
      setUrl('');
    } catch (error) {
      setIsError(true);
      setMessage(`Error: ${error.response?.data?.error || error.message}`);
      console.error('Error adding song:', error);
    } finally {
        setTimeout(() => setMessage(''), 5000); // Keep message on screen longer
    }
  };

  return (
    <div className="add-song-container">
      {/* ... The JSX remains the same, but we add a dynamic class for the message ... */}
      <h3>Add New Songs via Spotify</h3>
      <form onSubmit={handleSubmit} className="add-song-form">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste Spotify track URL"
        />
        <button type="submit">Add Song</button>
      </form>
      {message && <p className={`form-message ${isError ? 'error' : 'success'}`}>{message}</p>}
    </div>
  );
}

export default AddSongForm;