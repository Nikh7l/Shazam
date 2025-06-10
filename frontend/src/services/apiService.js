import axios from 'axios';

// Get the URL from environment variables, with a fallback
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

/**
 * Adds a new song to the database via its Spotify URL.
 * The backend will handle downloading, fingerprinting, and storing.
 * @param {string} spotifyUrl - The full URL of the Spotify track.
 * @returns {Promise<object>} - The response from the server.
 */
export const addSongFromSpotify = (spotifyUrl) => {
  return axios.post(`${API_URL}/songs`, { spotify_url: spotifyUrl });
};

// You can add getSongs and deleteSong here later for your admin panel