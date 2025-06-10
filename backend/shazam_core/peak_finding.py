import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import scipy.ndimage as ndimage
from dataclasses import dataclass

@dataclass
class Peak:
    """A class representing a peak in the spectrogram."""
    time_idx: int      # Time index
    freq_idx: int       # Frequency index
    magnitude: float    # Magnitude of the peak
    time: Optional[float] = None  # Time in seconds
    freq: Optional[float] = None  # Frequency in Hz
    
    def to_tuple(self) -> Tuple[int, int, float]:
        """Convert peak to a tuple of (time_idx, freq_idx, magnitude)."""
        return (self.time_idx, self.freq_idx, self.magnitude)

def find_peaks(
    spectrogram: np.ndarray,
    time_axis: int = 1,
    freq_axis: int = 0,
    amp_min: Optional[float] = None,
    num_peaks: Optional[int] = None,
    **kwargs
) -> List[Peak]:
    """
    Find peaks in a spectrogram.
    
    Args:
        spectrogram: Input spectrogram (2D numpy array)
        time_axis: Axis corresponding to time in the spectrogram
        freq_axis: Axis corresponding to frequency in the spectrogram
        amp_min: Minimum amplitude threshold for peaks
        num_peaks: Maximum number of peaks to return (top N by magnitude)
        **kwargs: Additional arguments to pass to the peak finding function
        
    Returns:
        List of Peak objects
    """
    # Ensure spectrogram is 2D
    if spectrogram.ndim != 2:
        raise ValueError(f"Expected 2D spectrogram, got {spectrogram.ndim}D")
    
    # Swap axes if needed to ensure time is axis 1 and frequency is axis 0
    if time_axis != 1 or freq_axis != 0:
        # Create a mapping of old axes to new axes
        axes = list(range(spectrogram.ndim))
        axes[time_axis], axes[1] = axes[1], axes[time_axis]
        axes[freq_axis], axes[0] = axes[0], axes[freq_axis]
        spectrogram = np.transpose(spectrogram, axes=axes)
    
    # Find local maxima in the spectrogram
    neighborhood = np.ones((3, 3), bool)
    local_max = ndimage.maximum_filter(spectrogram, footprint=neighborhood) == spectrogram
    
    # Find coordinates and values of local maxima
    freq_idxs, time_idxs = np.where(local_max)
    magnitudes = spectrogram[freq_idxs, time_idxs]
    
    # Filter by minimum amplitude if specified
    if amp_min is not None:
        mask = magnitudes >= amp_min
        time_idxs = time_idxs[mask]
        freq_idxs = freq_idxs[mask]
        magnitudes = magnitudes[mask]
    
    # Sort by magnitude in descending order
    if num_peaks is not None and len(magnitudes) > num_peaks:
        # Get indices of top N peaks by magnitude
        top_indices = np.argpartition(magnitudes, -num_peaks)[-num_peaks:]
        time_idxs = time_idxs[top_indices]
        freq_idxs = freq_idxs[top_indices]
        magnitudes = magnitudes[top_indices]
    
    # Create Peak objects
    peaks = [
        Peak(time_idx=time_idx, freq_idx=freq_idx, magnitude=magnitude)
        for time_idx, freq_idx, magnitude in zip(time_idxs, freq_idxs, magnitudes)
    ]
    
    return peaks

def find_peaks_in_bands(
    spectrogram: np.ndarray,
    freq_bands: List[Tuple[float, float]],
    freq_axis: int = 0,
    time_axis: int = 1,
    **kwargs
) -> Dict[Tuple[float, float], List[Peak]]:
    """
    Find peaks within specific frequency bands.
    
    Args:
        spectrogram: Input spectrogram
        freq_bands: List of (freq_min, freq_max) tuples defining the bands
        freq_axis: Axis corresponding to frequency in the spectrogram
        time_axis: Axis corresponding to time in the spectrogram
        **kwargs: Additional arguments to pass to find_peaks
        
    Returns:
        Dictionary mapping frequency bands to lists of peaks in those bands
    """
    if spectrogram.ndim != 2:
        raise ValueError("Expected 2D spectrogram")
    
    # Ensure frequency axis is first and time axis is second
    if freq_axis != 0 or time_axis != 1:
        axes = list(range(spectrogram.ndim))
        axes[freq_axis], axes[0] = axes[0], axes[freq_axis]
        axes[time_axis], axes[1] = axes[1], axes[time_axis]
        spectrogram = np.transpose(spectrogram, axes=axes)
    
    # Convert frequency bands to indices
    _, num_freq_bins = spectrogram.shape
    
    # For this simplified version, we'll assume the spectrogram is already in the right shape
    # and the frequency bands are given as fraction of the total frequency range
    band_peaks = {}
    
    for band in freq_bands:
        freq_min, freq_max = band
        # Convert frequency range to indices
        min_idx = int(freq_min * num_freq_bins)
        max_idx = int(freq_max * num_freq_bins)
        
        # Extract the frequency band
        band_spectrogram = spectrogram[min_idx:max_idx, :]
        
        # Find peaks in this band
        peaks = find_peaks(
            band_spectrogram,
            time_axis=1,
            freq_axis=0,
            **kwargs
        )
        
        # Adjust frequency indices to be relative to the full spectrogram
        for peak in peaks:
            peak.freq_idx += min_idx
        
        band_peaks[band] = peaks
    
    return band_peaks

def find_peaks_with_time_freq(
    spectrogram: np.ndarray,
    times: np.ndarray,
    freqs: np.ndarray,
    **kwargs
) -> List[Peak]:
    """
    Find peaks in a spectrogram and include time and frequency information.
    
    Args:
        spectrogram: Input spectrogram (2D numpy array)
        times: Array of time values for each time bin
        freqs: Array of frequency values for each frequency bin
        **kwargs: Additional arguments to pass to find_peaks
        
    Returns:
        List of Peak objects with time and frequency information
    """
    # Find peaks in the spectrogram
    peaks = find_peaks(spectrogram, **kwargs)
    
    # Add time and frequency information to each peak
    for peak in peaks:
        peak.time = times[peak.time_idx] if peak.time_idx < len(times) else None
        peak.freq = freqs[peak.freq_idx] if peak.freq_idx < len(freqs) else None
    
    return peaks
