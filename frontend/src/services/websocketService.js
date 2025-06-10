// frontend/src/services/websocketService.js

/**
 * Creates and manages a dedicated WebSocket connection for a single
 * song identification request.
 * @param {Blob} audioBlob - The audio data to send.
 * @param {object} callbacks - An object with onMatch, onNoMatch, onError handlers.
 */
export const identifyViaWebSocket = (audioBlob, { onMatch, onNoMatch, onError }) => {
  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5001/identify';
  
  // Create a new socket for this specific request.
  const socket = new WebSocket(WS_URL);
  
  // Set a flag to ensure we only handle one terminal message (match, no-match, or error)
  let isClosed = false;

  const cleanup = () => {
    if (!isClosed) {
      isClosed = true;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    }
  };

  socket.onopen = () => {
    console.log('[WebSocket] Connection opened. Sending audio...');
    if (audioBlob && audioBlob.size > 0) {
      socket.send(audioBlob);
    } else {
      onError('Cannot send empty audio data.');
      cleanup();
    }
  };

  socket.onmessage = (event) => {
    if (isClosed) return; // Ignore messages after we've decided on an outcome

    try {
      const message = JSON.parse(event.data);
      console.log('[WebSocket] Message received:', message);

      switch (message.status) {
        case 'match_found':
          onMatch(message.data);
          break;
        case 'no_match':
          onNoMatch();
          break;
        case 'error':
          onError(message.message || 'An unknown server error occurred.');
          break;
        default:
          console.warn('[WebSocket] Received unknown status:', message.status);
          onError('Received an unexpected response from the server.');
      }
    } catch (e) {
      console.error('[WebSocket] Error parsing message:', e);
      onError('Failed to parse server response.');
    } finally {
      cleanup();
    }
  };

  socket.onerror = (error) => {
    if (isClosed) return;
    console.error('[WebSocket] Connection error:', error);
    onError('A connection error occurred. Please check the server.');
    cleanup();
  };
  
  socket.onclose = () => {
    console.log('[WebSocket] Connection closed.');
  };

  // Return a cleanup function in case the component unmounts
  return cleanup;
};