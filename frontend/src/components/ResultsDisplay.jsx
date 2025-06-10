// frontend/src/components/ResultsDisplay.jsx
import React from 'react';
import PropTypes from 'prop-types';
import YouTube from 'react-youtube';
import '../styles/ResultsDisplay.css';

function ResultsDisplay({ match }) {
  const youtubeOptions = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 1,
      start: match.timestamp || 0,
    },
  };

  const onPlayerError = (event) => {
    // This handles cases like "Video unavailable"
    event.target.getIframe().style.display = 'none';
    const errorDiv = document.createElement('div');
    errorDiv.className = 'video-unavailable';
    errorDiv.innerText = 'Video playback is unavailable.';
    event.target.getIframe().parentNode.appendChild(errorDiv);
  };

  return (
    <div className="result-container">
      <div className="song-card">
        <img src={match.coverArt} alt={`${match.title} cover art`} className="cover-art" />
        <div className="song-details">
          <h3>{match.title}</h3>
          <p>{match.artist} • {match.album}</p>
        </div>
      </div>
      <div className="youtube-player">
        <YouTube videoId={match.youtubeId} opts={youtubeOptions} onError={onPlayerError} />
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