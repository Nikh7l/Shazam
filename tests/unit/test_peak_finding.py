import pytest
import numpy as np
from backend.shazam_core.peak_finding import find_peaks, Peak, find_peaks_with_time_freq
# find_peaks_in_bands might be more complex to unit test without a full spectrogram context,
# so we'll focus on find_peaks and find_peaks_with_time_freq for now.

@pytest.fixture
def sample_spectrogram_simple():
    """A simple spectrogram with a clear peak."""
    spec = np.array([
        [0, 0, 0, 0, 0],
        [0, 5, 1, 0, 0], # Peak at (1,1) with magnitude 5
        [0, 1, 0, 0, 0],
        [0, 0, 0, 3, 0], # Peak at (3,3) with magnitude 3
        [0, 0, 0, 0, 0]
    ])
    return spec

@pytest.fixture
def sample_spectrogram_flat():
    """A flat spectrogram where no distinct peaks should be found by some criteria."""
    return np.ones((5, 5))

@pytest.fixture
def sample_times_freqs():
    """Sample time and frequency arrays."""
    times = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    freqs = np.array([0, 100, 200, 300, 400])
    return times, freqs

def test_find_peaks_basic(sample_spectrogram_simple):
    """Test basic peak finding."""
    peaks = find_peaks(sample_spectrogram_simple)

    assert len(peaks) == 2, "Should find 2 peaks in the simple spectrogram"

    # Convert to list of tuples for easier comparison, sort by magnitude then by loc
    peak_tuples = sorted([(p.freq_idx, p.time_idx, p.magnitude) for p in peaks], key=lambda x: (-x[2], x[0], x[1]))

    expected_peaks = sorted([(1, 1, 5.0), (3, 3, 3.0)], key=lambda x: (-x[2], x[0], x[1]))
    assert peak_tuples == expected_peaks

def test_find_peaks_amp_min(sample_spectrogram_simple):
    """Test peak finding with an amplitude minimum."""
    peaks = find_peaks(sample_spectrogram_simple, amp_min=4.0)
    assert len(peaks) == 1
    assert peaks[0].freq_idx == 1
    assert peaks[0].time_idx == 1
    assert peaks[0].magnitude == 5.0

    peaks_none = find_peaks(sample_spectrogram_simple, amp_min=6.0)
    assert len(peaks_none) == 0

def test_find_peaks_num_peaks(sample_spectrogram_simple):
    """Test limiting the number of peaks returned."""
    peaks = find_peaks(sample_spectrogram_simple, num_peaks=1)
    assert len(peaks) == 1
    # Should return the peak with the highest magnitude
    assert peaks[0].magnitude == 5.0
    assert peaks[0].freq_idx == 1
    assert peaks[0].time_idx == 1

def test_find_peaks_flat_spectrogram(sample_spectrogram_flat):
    """Test peak finding on a flat spectrogram (no local maxima)."""
    # In a perfectly flat spectrogram, every point is a local maximum if neighborhood includes self.
    # The ndimage.maximum_filter behavior implies all points will be marked if they are part of a plateau.
    # If the footprint is strictly >1 in size, it correctly identifies no unique peaks.
    # The current implementation `neighborhood = np.ones((3, 3), bool)` means `maximum_filter` result will be same as input.
    # `local_max = ndimage.maximum_filter(spectrogram, footprint=neighborhood) == spectrogram` will be all True.
    # This means it will return all points as peaks, which might not be desired for a truly flat input.
    # However, this is how the current algorithm is written.
    peaks = find_peaks(sample_spectrogram_flat)
    assert len(peaks) == sample_spectrogram_flat.size, "Should find all points as peaks in a flat spectrogram with current logic"

def test_find_peaks_empty_spectrogram():
    """Test peak finding with an empty spectrogram."""
    spec = np.array([[]])
    with pytest.raises(ValueError, match="Expected 2D spectrogram"):
         find_peaks(spec) # Will fail earlier due to ndim check

    spec_empty_rows = np.empty((0, 5))
    with pytest.raises(ValueError, match="Expected 2D spectrogram"):
        find_peaks(spec_empty_rows) # Will fail earlier if ndim check is specific

    # If it passes initial checks, should return no peaks
    # spec_valid_empty = np.array([[],[]]) # This is not possible with numpy directly for 2D
    # For a (0,N) or (N,0) array, it should ideally return 0 peaks or handle gracefully.
    # Current ndimage.maximum_filter might raise error or return empty based on exact empty shape.
    # Let's test a (2,0) shape
    spec_2_0 = np.empty((2,0))
    peaks = find_peaks(spec_2_0)
    assert len(peaks) == 0

def test_find_peaks_with_time_freq_basic(sample_spectrogram_simple, sample_times_freqs):
    """Test find_peaks_with_time_freq adds time and freq correctly."""
    times, freqs = sample_times_freqs
    peaks = find_peaks_with_time_freq(sample_spectrogram_simple, times, freqs)

    assert len(peaks) == 2

    peak_details = []
    for p in peaks:
        assert p.time is not None, "Time should be populated"
        assert p.freq is not None, "Frequency should be populated"
        peak_details.append((p.freq_idx, p.time_idx, p.magnitude, p.freq, p.time))

    # Sort by magnitude then original indices for consistent comparison
    peak_details_sorted = sorted(peak_details, key=lambda x: (-x[2], x[0], x[1]))

    expected_details = [
        (1, 1, 5.0, freqs[1], times[1]), # freq_idx=1, time_idx=1, mag=5.0
        (3, 3, 3.0, freqs[3], times[3])  # freq_idx=3, time_idx=3, mag=3.0
    ]
    expected_details_sorted = sorted(expected_details, key=lambda x: (-x[2], x[0], x[1]))

    for found, expected in zip(peak_details_sorted, expected_details_sorted):
        assert found[0] == expected[0] # freq_idx
        assert found[1] == expected[1] # time_idx
        assert found[2] == expected[2] # magnitude
        assert found[3] == expected[3] # freq (actual value)
        assert found[4] == expected[4] # time (actual value)

def test_peak_dataclass():
    """Test the Peak dataclass."""
    peak = Peak(time_idx=1, freq_idx=2, magnitude=3.0, time=0.1, freq=200.0)
    assert peak.to_tuple() == (1, 2, 3.0)
    assert peak.time == 0.1
    assert peak.freq == 200.0
