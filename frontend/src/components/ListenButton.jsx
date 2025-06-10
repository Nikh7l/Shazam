// frontend/src/components/ListenButton.jsx
import React from 'react';
import PropTypes from 'prop-types';
import '../styles/ListenButton.css';

const ShazamIcon = () => (
  // Your SVG Icon from before...
  <svg className="listen-button-icon" viewBox="0 0 24 24" fill="currentColor">
    <path d="M16.36 7.64a5.5 5.5 0 0 0-7.78 0l-1.41 1.41a7.5 7.5 0 0 1 10.6 0l-1.41-1.41zM12 3a9.5 9.5 0 0 0-6.72 2.78l1.41 1.41A7.5 7.5 0 0 1 12 5a7.5 7.5 0 0 1 5.3 2.2l1.42-1.42A9.5 9.5 0 0 0 12 3zm0 18a9.5 9.5 0 0 0 6.72-2.78l-1.41-1.41A7.5 7.5 0 0 1 12 19a7.5 7.5 0 0 1-5.3-2.2L5.28 18.22A9.5 9.5 0 0 0 12 21zm-2.07-5.64a5.5 5.5 0 0 0 7.78 0l1.41-1.41a7.5 7.5 0 0 1-10.6 0l1.41 1.41z"/>
  </svg>
);

function ListenButton({ onStartListening, isListening }) {
  return (
    <div className="listen-button-wrapper">
      <button
        className="listen-button"
        onClick={onStartListening}
        disabled={isListening}
        aria-label="Start listening"
      >
        <ShazamIcon />
      </button>
      {isListening && (
        <>
          <div className="ring"></div>
          <div className="ring delay1"></div>
          <div className="ring delay2"></div>
        </>
      )}
    </div>
  );
}

ListenButton.propTypes = {
  onStartListening: PropTypes.func.isRequired,
  isListening: PropTypes.bool.isRequired,
};

export default ListenButton;