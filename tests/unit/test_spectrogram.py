import pytest
import numpy as np
from backend.shazam_core.spectrogram import generate_spectrogram, amplitude_to_db

# Helper function to generate a simple sine wave
def generate_sine_wave(frequency, duration, sample_rate, amplitude=0.5):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * frequency * t)

def test_generate_spectrogram_basic():
    """Test basic spectrogram generation."""
    sample_rate = 11025
    audio_data = generate_sine_wave(440, 1.0, sample_rate) # 1 second A4 note

    spec, freqs, times = generate_spectrogram(audio_data, sample_rate)

    assert isinstance(spec, np.ndarray), "Spectrogram should be a numpy array"
    assert isinstance(freqs, np.ndarray), "Frequencies should be a numpy array"
    assert isinstance(times, np.ndarray), "Times should be a numpy array"

    assert spec.ndim == 2, "Spectrogram should be 2D"
    assert freqs.ndim == 1, "Frequencies should be 1D"
    assert times.ndim == 1, "Times should be 1D"

    assert spec.shape[0] == freqs.shape[0], "Spectrogram frequency bins should match freqs length"
    assert spec.shape[1] == times.shape[0], "Spectrogram time frames should match times length"
    assert spec.dtype == np.float64 or spec.dtype == np.float32 # Depending on db_scale usage

def test_generate_spectrogram_output_values():
    """Test spectrogram values for a known input (e.g., dominant frequency)."""
    sample_rate = 11025
    window_size = 1024 # Smaller window for better frequency resolution in test
    hop_size = 512
    frequency = 440  # A4 note
    audio_data = generate_sine_wave(frequency, 1.0, sample_rate)

    spec, freqs, times = generate_spectrogram(
        audio_data,
        sample_rate,
        window_size=window_size,
        hop_size=hop_size,
        db_scale=False, # Test raw magnitude first
        log_scale=False
    )

    # Find the frequency bin closest to the input frequency
    target_freq_idx = np.argmin(np.abs(freqs - frequency))

    # The energy should be concentrated around this frequency bin
    # Check a few time slices
    for i in range(times.shape[0] // 2, times.shape[0] // 2 + 3): # Check some middle frames
        assert np.argmax(spec[:, i]) == target_freq_idx, \
            f"Peak energy not at target frequency {frequency}Hz (bin {target_freq_idx}) in time slice {i}"
    assert np.all(spec >= 0), "Spectrogram magnitudes should be non-negative"


def test_generate_spectrogram_db_scale():
    """Test spectrogram generation with dB scaling."""
    sample_rate = 11025
    audio_data = generate_sine_wave(440, 1.0, sample_rate)

    spec_db, _, _ = generate_spectrogram(audio_data, sample_rate, db_scale=True)
    spec_mag, _, _ = generate_spectrogram(audio_data, sample_rate, db_scale=False, log_scale=False)

    assert spec_db.shape == spec_mag.shape
    assert not np.allclose(spec_db, spec_mag), "dB scaled spectrogram should differ from magnitude spectrogram"

def test_generate_spectrogram_log_scale():
    """Test spectrogram generation with log scaling (but not dB)."""
    sample_rate = 11025
    audio_data = generate_sine_wave(440, 1.0, sample_rate)

    spec_log, _, _ = generate_spectrogram(audio_data, sample_rate, log_scale=True, db_scale=False)
    spec_mag, _, _ = generate_spectrogram(audio_data, sample_rate, log_scale=False, db_scale=False)

    assert spec_log.shape == spec_mag.shape
    assert not np.allclose(spec_log, spec_mag), "Log scaled spectrogram should differ from magnitude spectrogram"
    assert np.all(spec_log >= 0) # log(1+x) for x>=0 is >=0

def test_generate_spectrogram_empty_input():
    """Test spectrogram generation with empty audio data."""
    sample_rate = 11025
    audio_data = np.array([])
    with pytest.raises(ValueError, match="Input audio data is empty"):
        generate_spectrogram(audio_data, sample_rate)

def test_amplitude_to_db_basic():
    """Test basic amplitude to dB conversion."""
    amplitudes = np.array([1.0, 0.5, 0.1, 1e-5])
    expected_db = np.array([0.0, -6.0206, -20.0, -100.0]) # Theoretical values

    db_values = amplitude_to_db(amplitudes, ref=1.0, top_db=None)

    assert isinstance(db_values, np.ndarray)
    assert db_values.shape == amplitudes.shape
    np.testing.assert_allclose(db_values, expected_db, rtol=1e-2, atol=1e-2)

def test_amplitude_to_db_ref_value():
    """Test amplitude to dB conversion with a different reference value."""
    amplitudes = np.array([2.0, 1.0, 0.5])
    expected_db = np.array([0.0, -6.0206, -12.0412])

    db_values = amplitude_to_db(amplitudes, ref=2.0, top_db=None)
    np.testing.assert_allclose(db_values, expected_db, rtol=1e-2, atol=1e-2)

def test_amplitude_to_db_top_db():
    """Test amplitude to dB conversion with top_db clamping."""
    data = np.array([[0.1, 0.5, 1.0],
                     [0.01, 0.2, 0.05]])
    expected_top_db_10 = np.array([[-10.0, -6.0206, 0.0],
                                   [-10.0, -10.0, -10.0]])

    db_values_top_db_10 = amplitude_to_db(data, ref=1.0, top_db=10.0)
    np.testing.assert_allclose(db_values_top_db_10, expected_top_db_10, rtol=1e-2, atol=1e-2)

    expected_top_db_30 = np.array([[-20.0, -6.0206, 0.0],
                                   [-30.0, -13.9794, -26.0206]])
    db_values_top_db_30 = amplitude_to_db(data, ref=1.0, top_db=30.0)
    np.testing.assert_allclose(db_values_top_db_30, expected_top_db_30, rtol=1e-2, atol=1e-2)
