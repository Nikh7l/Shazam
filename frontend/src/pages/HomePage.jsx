// frontend/src/pages/HomePage.jsx
import { useState, useRef, useEffect, useCallback } from 'react';
import ListenButton from '../components/ListenButton.jsx';
import ResultsDisplay from '../components/ResultsDisplay.jsx';
// import { identifyViaWebSocket } from '../services/websocketService'; // Replaced with HTTP POST

function HomePage() {
  const [view, setView] = useState('idle');
  const [matchResult, setMatchResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]); // <-- Use a ref for audio chunks
  const webSocketCleanupRef = useRef(null); // Kept for potential future use, but current flow is HTTP

  useEffect(() => {
    // Cleanup WebSocket on component unmount
    // return () => webSocketCleanupRef.current?.(); // WebSocket cleanup not primary for HTTP
  }, []);

  const handleMatch = useCallback((matchData) => {
    setMatchResult(matchData);
    setView('result');
  }, []);

  const handleNoMatch = useCallback(() => {
    setErrorMessage('Could not find a confident match.');
    setView('error');
  }, []);

  const handleError = useCallback((errorMsg) => {
    setErrorMessage(errorMsg || 'An unknown error occurred.');
    setView('error');
  }, []);

  // This function will be called when recording stops
  const handleStopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }

    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

    if (audioBlob.size > 0) {
      setView('processing'); // Update view to show analyzing state
      sendAudioViaHttp(audioBlob); // Call new HTTP function
    } else {
      handleError('Recording failed or was empty. Please check microphone permissions and try again.');
    }
  };


  const handleStartListening = async () => {
    if (view === 'listening') return;

    setView('listening');
    setErrorMessage('');
    setMatchResult(null);
    audioChunksRef.current = []; // Reset the chunks ref

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      // Define event handlers for the recorder
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = handleStopRecording;

      // Start recording
      mediaRecorderRef.current.start();
      
      // Set a timer to automatically stop recording
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, 7000);

    } catch (err) {
      console.error("Microphone access error:", err);
      handleError('Microphone access denied. Please grant permission in your browser settings.');
    }
  };

  const reset = () => {
    setView('idle');
    setMatchResult(null);
    setErrorMessage('');
    // webSocketCleanupRef.current?.(); // WebSocket cleanup not primary for HTTP
  };

  // New function to send audio via HTTP POST
  const sendAudioViaHttp = async (audioBlob) => {
    const formData = new FormData();
    // The backend expects a .wav file, but MediaRecorder often produces .webm or .ogg.
    // We'll send it as 'live_recording.webm' and rely on the backend to process it.
    // If issues arise, backend might need to use ffmpeg or similar for conversion,
    // or frontend could try to record directly in WAV if browser supports.
    formData.append('audio_data', audioBlob, 'live_recording.webm'); 

    try {
      const response = await fetch('/api/match_live_audio', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Server returned an error' }));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        if (result.match_found) {
          handleMatch(result); // Pass the whole result object
        } else {
          handleNoMatch();
        }
      } else {
        handleError(result.error || 'Failed to process audio.');
      }
    } catch (err) {
      console.error('Error sending audio to backend:', err);
      handleError(err.message || 'An error occurred while sending audio.');
    }
  };

  // --- UI Rendering ---
  const renderContent = () => {
    switch(view) {
      case 'listening': return <p className="status-message">Listening...</p>;
      case 'processing': return <p className="status-message">Analyzing...</p>;
      case 'result': return matchResult && matchResult.match_found ? <ResultsDisplay match={matchResult} /> : null;
      case 'error': return <p className="status-message error">{errorMessage}</p>;
      default: return <p className="status-message">Tap the button to identify a song</p>;
    }
  };
  
  return (
    <div className="main-content">
      <div className="container">
        {view !== 'result' && (
          <ListenButton
            onStartListening={handleStartListening}
            isListening={view === 'listening'}
          />
        )}
        {renderContent()}
        {(view === 'result' || view === 'error') && (
            <button className="try-again-button" onClick={reset} style={{marginTop: '20px'}}>
              Try Again
            </button>
        )}
      </div>
    </div>
  );
}

export default HomePage;