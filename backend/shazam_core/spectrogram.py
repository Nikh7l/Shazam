import numpy as np
from scipy import signal
from typing import Tuple, Optional

def generate_spectrogram(
    audio_data: np.ndarray,
    sample_rate: int = 11025,
    window_size: int = 2048,
    hop_size: int = 512,
    window_type: str = 'hann',
    log_scale: bool = True,
    db_scale: bool = True,
    ref: float = 1.0,
    top_db: float = 80.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate a spectrogram from audio data using Short-Time Fourier Transform (STFT).
    
    Args:
        audio_data: Input audio data (1D numpy array)
        sample_rate: Sample rate of the audio
        window_size: Size of the FFT window (samples)
        hop_size: Number of samples between successive frames
        window_type: Type of window function ('hann', 'hamming', 'blackman', etc.)
        log_scale: Whether to apply log scaling to the spectrogram
        db_scale: Whether to convert to decibel scale
        ref: Reference value for dB scaling
        top_db: Threshold the output at top_db below the peak
        
    Returns:
        Tuple of (spectrogram, frequencies, times)
    """
    # Validate input
    if len(audio_data) == 0:
        raise ValueError("Input audio data is empty")
    
    # Get window function
    window = signal.get_window(window_type, window_size, fftbins=True)
    
    # Compute STFT
    f, t, Zxx = signal.stft(
        audio_data,
        fs=sample_rate,
        window=window,
        nperseg=window_size,
        noverlap=window_size - hop_size,
        boundary=None,
        padded=False
    )
    
    # Calculate magnitude spectrum
    spectrogram = np.abs(Zxx)
    
    # Convert to dB scale if requested
    if db_scale:
        spectrogram = amplitude_to_db(spectrogram, ref=ref, top_db=top_db)
    # Apply log scaling if requested (but not in dB)
    elif log_scale:
        spectrogram = np.log1p(spectrogram)
    
    return spectrogram, f, t

def amplitude_to_db(S: np.ndarray, ref: float = 1.0, top_db: float = 80.0) -> np.ndarray:
    """
    Convert an amplitude spectrogram to dB-scaled spectrogram.
    
    Args:
        S: Input amplitude spectrogram
        ref: Reference value for dB scaling
        top_db: Threshold the output at top_db below the peak
        
    Returns:
        dB-scaled spectrogram
    """
    # Avoid division by zero
    magnitude = np.abs(S)
    ref_value = np.abs(ref)
    
    # Convert to dB
    min_db = -100
    log_spec = 10.0 * np.log10(np.maximum(1e-10, magnitude) / ref_value)
    
    # Apply threshold
    if top_db is not None:
        log_spec = np.maximum(log_spec, log_spec.max() - top_db)
    
    return log_spec

def mel_spectrogram(
    audio_data: np.ndarray,
    sample_rate: int = 11025,
    n_fft: int = 2048,
    hop_length: int = 512,
    n_mels: int = 128,
    fmin: float = 0.0,
    fmax: Optional[float] = None,
    **kwargs
) -> np.ndarray:
    """
    Generate a Mel-scaled spectrogram.
    
    Args:
        audio_data: Input audio data (1D numpy array)
        sample_rate: Sample rate of the audio
        n_fft: Size of the FFT window
        hop_length: Number of samples between successive frames
        n_mels: Number of Mel bands to generate
        fmin: Lowest frequency (in Hz)
        fmax: Highest frequency (in Hz). If None, use sample_rate/2
        
    Returns:
        Mel spectrogram
    """
    from scipy import signal
    
    # Compute STFT
    _, _, Zxx = signal.stft(
        audio_data,
        fs=sample_rate,
        nperseg=n_fft,
        noverlap=n_fft - hop_length,
        **kwargs
    )
    
    # Get power spectrogram
    S = np.abs(Zxx) ** 2
    
    # Create Mel filter bank
    fmax = fmax or sample_rate / 2
    mel_basis = mel_filter_bank(
        sample_rate=sample_rate,
        n_fft=n_fft,
        n_mels=n_mels,
        fmin=fmin,
        fmax=fmax
    )
    
    # Apply Mel filter bank
    mel_spectrum = np.dot(mel_basis, S)
    
    return mel_spectrum

def mel_filter_bank(
    sample_rate: int,
    n_fft: int,
    n_mels: int = 128,
    fmin: float = 0.0,
    fmax: Optional[float] = None,
    htk: bool = False
) -> np.ndarray:
    """
    Create a Mel filter bank.
    
    Args:
        sample_rate: Sample rate of the audio
        n_fft: Number of FFT bins
        n_mels: Number of Mel bands to generate
        fmin: Lowest frequency (in Hz)
        fmax: Highest frequency (in Hz). If None, use sample_rate/2
        htk: Use HTK formula instead of Slaney
        
    Returns:
        Mel filter bank (n_mels, n_fft//2 + 1)
    """
    from scipy.fftpack import dct
    
    if fmax is None:
        fmax = sample_rate / 2
    
    # Initialize the weights
    n_freqs = n_fft // 2 + 1
    weights = np.zeros((n_mels, n_freqs))
    
    # Center freqs of each FFT bin
    fftfreqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
    
    # 'Center freqs' of mel bands
    if htk:
        # HTK Mel scale
        mel_f = np.linspace(
            hz_to_mel(fmin, htk=True),
            hz_to_mel(fmax, htk=True),
            n_mels + 2
        )
    else:
        # Slaney's Mel scale
        mel_f = mel_frequencies(n_mels + 2, fmin, fmax, htk=False)
    
    # Convert Mel freqs to Hz
    fdiff = np.diff(mel_f)
    ramps = np.subtract.outer(mel_f, fftfreqs)
    
    for i in range(n_mels):
        # Lower and upper slopes for all bins
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i+2] / fdiff[i+1]
        
        # Intersect with the triangle
        weights[i] = np.maximum(0, np.minimum(lower, upper))
    
    # Slaney-style mel is scaled to be approx constant energy per channel
    if not htk:
        enorm = 2.0 / (mel_f[2:n_mels+2] - mel_f[:n_mels])
        weights *= enorm[:, np.newaxis]
    
    return weights

def hz_to_mel(frequencies: np.ndarray, htk: bool = False) -> np.ndarray:
    """Convert Hz to Mels."""
    frequencies = np.asanyarray(frequencies)
    
    if htk:
        return 2595.0 * np.log10(1.0 + frequencies / 700.0)
    
    # Fill in the linear part
    f_min = 0.0
    f_sp = 200.0 / 3
    mels = (frequencies - f_min) / f_sp
    
    # Fill in the log-scale part
    min_log_hz = 1000.0  # beginning of log region (Hz)
    min_log_mel = (min_log_hz - f_min) / f_sp  # same (Mels)
    logstep = np.log(6.4) / 27.0  # step size for log region
    
    if frequencies.ndim:
        log_t = (frequencies >= min_log_hz)
        mels[log_t] = min_log_mel + np.log(frequencies[log_t] / min_log_hz) / logstep
    elif frequencies >= min_log_hz:
        mels = min_log_mel + np.log(frequencies / min_log_hz) / logstep
    
    return mels

def mel_frequencies(n_mels: int = 128, fmin: float = 0.0, fmax: float = 11025.0, htk: bool = False) -> np.ndarray:
    """Compute the center frequencies of Mel bands."""
    # 'Center freqs' of mel bands
    min_mel = hz_to_mel(fmin, htk=htk)
    max_mel = hz_to_mel(fmax, htk=htk)
    
    mels = np.linspace(min_mel, max_mel, n_mels)
    
    if htk:
        return 700.0 * (10.0 ** (mels / 2595.0) - 1.0)
    
    # Fill in the linear scale
    f_min = 0.0
    f_sp = 200.0 / 3
    freqs = f_min + f_sp * mels
    
    # And now the nonlinear scale
    min_log_hz = 1000.0  # beginning of log region (Hz)
    min_log_mel = (min_log_hz - f_min) / f_sp  # same (Mels)
    logstep = np.log(6.4) / 27.0  # step size for log region
    
    log_t = (mels >= min_log_mel)
    freqs[log_t] = min_log_hz * np.exp(logstep * (mels[log_t] - min_log_mel))
    
    return freqs
