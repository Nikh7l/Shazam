import numpy as np
from pydub import AudioSegment
import io
import os
from typing import Tuple, Optional

def load_audio(file_path: str, target_sample_rate: int = 11025) -> Tuple[np.ndarray, int]:
    """
    Load an audio file and convert it to a mono waveform with the target sample rate.
    
    Args:
        file_path: Path to the audio file
        target_sample_rate: Target sample rate in Hz
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # Load audio file
    audio = AudioSegment.from_file(file_path)
    
    # Convert to mono if stereo
    if audio.channels > 1:
        audio = audio.set_channels(1)
    
    # Resample to target sample rate if needed
    if audio.frame_rate != target_sample_rate:
        audio = audio.set_frame_rate(target_sample_rate)
    
    # Convert to numpy array
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    
    # Normalize to [-1, 1]
    if audio.sample_width == 2:  # 16-bit
        samples = samples / 32768.0
    elif audio.sample_width == 1:  # 8-bit
        samples = (samples - 128) / 128.0
    
    return samples, target_sample_rate

def load_audio_from_bytes(audio_bytes: bytes, format: str = 'wav', target_sample_rate: int = 11025) -> Tuple[np.ndarray, int]:
    """
    Load audio from bytes and convert it to a mono waveform with the target sample rate.
    
    Args:
        audio_bytes: Audio data as bytes
        format: Format of the audio data (e.g., 'wav', 'mp3')
        target_sample_rate: Target sample rate in Hz
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    # Create a file-like object from bytes
    audio_file = io.BytesIO(audio_bytes)
    
    # Load audio using pydub
    audio = AudioSegment.from_file(audio_file, format=format)
    
    # Convert to mono if stereo
    if audio.channels > 1:
        audio = audio.set_channels(1)
    
    # Resample to target sample rate if needed
    if audio.frame_rate != target_sample_rate:
        audio = audio.set_frame_rate(target_sample_rate)
    
    # Convert to numpy array
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    
    # Normalize to [-1, 1]
    if audio.sample_width == 2:  # 16-bit
        samples = samples / 32768.0
    elif audio.sample_width == 1:  # 8-bit
        samples = (samples - 128) / 128.0
    
    return samples, target_sample_rate

def preprocess_audio(
    audio_data: np.ndarray, 
    sample_rate: int, 
    target_sample_rate: int = 11025,
    normalize: bool = True
) -> np.ndarray:
    """
    Preprocess audio data by resampling and normalizing.
    
    Args:
        audio_data: Input audio data as a numpy array
        sample_rate: Original sample rate
        target_sample_rate: Target sample rate
        normalize: Whether to normalize the audio to [-1, 1]
        
    Returns:
        Preprocessed audio data
    """
    # Convert to float32 if not already
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    
    # Resample if needed
    if sample_rate != target_sample_rate:
        from scipy import signal
        num_samples = int(len(audio_data) * target_sample_rate / sample_rate)
        audio_data = signal.resample(audio_data, num_samples)
    
    # Normalize to [-1, 1]
    if normalize:
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val
    
    return audio_data
