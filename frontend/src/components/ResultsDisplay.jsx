// frontend/src/components/ResultsDisplay.jsx
import React from 'react';
import PropTypes from 'prop-types';
import YouTube from 'react-youtube';
import '../styles/ResultsDisplay.css';

import { useState } from 'react';

function ResultsDisplay({ match }) {
  const [playerError, setPlayerError] = useState(false);

  const youtubeOptions = {
    playerVars: {
      autoplay: 1,
      start: match.timestamp || 0,
      origin: window.location.origin,
    },
  };

  const onPlayerReady = (event) => {
    console.log('YouTube Player is ready.');
  };

  const onPlayerError = (event) => {
    console.error('YouTube Player Error:', event.data);
    setPlayerError(true);
  };

  return (
    <div className="result-container">
      <div className="song-card">
        <img
          src={match.coverArt || `https://img.youtube.com/vi/${match.youtubeId}/0.jpg`}
          alt={`${match.title} cover art`}
          className="cover-art"
        />
        <div className="song-details">
          <h3>{match.title}</h3>
          <p>{match.artist} • {match.album}</p>
        </div>
      </div>
      <div className="youtube-player">
        {playerError ? (
          <div className="video-unavailable">
            Video playback is unavailable.
          </div>
        ) : (
          <YouTube
            videoId={match.youtubeId}
            opts={youtubeOptions}
            onReady={onPlayerReady}
            onError={onPlayerError}
            className="react-youtube-iframe" // Apply class for CSS targeting
          />
        )}
      </div>
    </div>
  );
}

// ... propTypes remain the same
ResultsDisplay.propTypes = {
  match: PropTypes.shape({
    title: PropTypes.string,
    artist: PropTypes.string,
    album: PropTypes.string,
    coverArt: PropTypes.string,
    youtubeId: PropTypes.string,
    timestamp: PropTypes.number,
  }).isRequired,
};

export default ResultsDisplay;