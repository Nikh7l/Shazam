import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import './App.css';
import ListenButton from './frontend/src/components/ListenButton.jsx';

function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [matchResult, setMatchResult] = useState(null);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        // Here we would send the audio data to the backend for processing
        console.log('Audio recorded:', audioBlob);
        // For now, we'll just simulate a match after a delay
        setTimeout(() => {
          setMatchResult({
            title: 'Example Song',
            artist: 'Example Artist',
            album: 'Example Album',
            coverArt: 'https://via.placeholder.com/300',
            youtubeId: 'dQw4w9WgXcQ' // Example YouTube video ID
          });
          setIsLoading(false);
        }, 2000);
      };

      mediaRecorderRef.current.start();
      setIsListening(true);
      setIsLoading(true);
      setMatchResult(null);
      setError(null);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Could not access microphone. Please ensure you have granted microphone permissions.');
      setIsLoading(false);
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      
      // Stop all tracks in the stream
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      
      setIsListening(false);
      // Don't set loading to false here - we'll do that after processing
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Shazam Clone</h1>
      </header>
      <main className="main-content">
        <div className="container">
          {isLoading ? (
            <div className="loading">Listening...</div>
          ) : error ? (
            <div className="error">{error}</div>
          ) : matchResult ? (
            <div className="result">
              <h2>Match Found!</h2>
              {/* Will add ResultsDisplay component here */}
            </div>
          ) : (
            <div className="listen-container">
              <h2>Tap to identify music</h2>
              <ListenButton
                onStartListening={startListening}
                onStopListening={stopListening}
                isListening={isListening}
              />
            </div>
          )}
        </div>
      </main>
      <footer className="app-footer">
        <p>Shazam Clone © {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

export default App;
