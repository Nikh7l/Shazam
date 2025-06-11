import pytest
import numpy as np
import os
from backend.shazam_core.audio_utils import load_audio, load_audio_from_bytes, preprocess_audio
from pydub import AudioSegment
import io

# Path to the test audio file - assumes tests are run from project root or pytest handles paths
# Adjust if tests/data is not found relative to where pytest is run
SAMPLE_WAV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample.wav')
SAMPLE_MP3_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'test_music.MP3') # If you have an MP3 sample

@pytest.fixture
def sample_wav_file_path():
    if not os.path.exists(SAMPLE_WAV_PATH):
        pytest.skip(f"Sample WAV file not found: {SAMPLE_WAV_PATH}")
    return SAMPLE_WAV_PATH

@pytest.fixture
def sample_mp3_file_path():
    if not os.path.exists(SAMPLE_MP3_PATH):
        pytest.skip(f"Sample MP3 file not found: {SAMPLE_MP3_PATH}")
    return SAMPLE_MP3_PATH

def test_load_audio_wav(sample_wav_file_path):
    """Test loading a WAV file."""
    target_sr = 11025
    audio_data, sample_rate = load_audio(sample_wav_file_path, target_sample_rate=target_sr)

    assert isinstance(audio_data, np.ndarray), "Audio data should be a numpy array"
    assert audio_data.ndim == 1, "Audio data should be mono (1D)"
    assert sample_rate == target_sr, f"Sample rate should be {target_sr}"
    assert audio_data.dtype == np.float32, "Audio data type should be float32"
    assert np.max(np.abs(audio_data)) <= 1.0, "Audio data should be normalized to [-1, 1]"
    assert len(audio_data) > 0, "Audio data should not be empty"

def test_load_audio_mp3(sample_mp3_file_path):
    """Test loading an MP3 file."""
    target_sr = 22050
    audio_data, sample_rate = load_audio(sample_mp3_file_path, target_sample_rate=target_sr)

    assert isinstance(audio_data, np.ndarray)
    assert audio_data.ndim == 1
    assert sample_rate == target_sr
    assert audio_data.dtype == np.float32
    assert np.max(np.abs(audio_data)) <= 1.0
    assert len(audio_data) > 0

def test_load_audio_different_target_sr(sample_wav_file_path):
    """Test loading with a different target sample rate for resampling."""
    original_audio = AudioSegment.from_file(sample_wav_file_path)
    original_sr = original_audio.frame_rate
    target_sr = original_sr * 2 # Example: double the original SR

    audio_data, sample_rate = load_audio(sample_wav_file_path, target_sample_rate=target_sr)
    assert sample_rate == target_sr

    # Expected length after resampling
    expected_len = int(len(original_audio.get_array_of_samples()) * (target_sr / original_sr))
    # Allow for small differences due to resampling algorithms
    assert abs(len(audio_data) - expected_len) < target_sr * 0.01 # Allow 10ms difference

def test_load_audio_from_bytes_wav(sample_wav_file_path):
    """Test loading audio from bytes (WAV format)."""
    target_sr = 11025
    with open(sample_wav_file_path, 'rb') as f:
        wav_bytes = f.read()

    audio_data, sample_rate = load_audio_from_bytes(wav_bytes, format='wav', target_sample_rate=target_sr)

    assert isinstance(audio_data, np.ndarray)
    assert audio_data.ndim == 1
    assert sample_rate == target_sr
    assert audio_data.dtype == np.float32
    assert np.max(np.abs(audio_data)) <= 1.0
    assert len(audio_data) > 0

# To test load_audio_from_bytes for MP3, you'd need a sample MP3 byte stream
@pytest.fixture
def sample_mp3_bytes(sample_mp3_file_path):
    with open(sample_mp3_file_path, 'rb') as f:
        return f.read()

def test_load_audio_from_bytes_mp3(sample_mp3_bytes):
    """Test loading audio from bytes (MP3 format)."""
    target_sr = 22050
    audio_data, sample_rate = load_audio_from_bytes(sample_mp3_bytes, format='mp3', target_sample_rate=target_sr)

    assert isinstance(audio_data, np.ndarray)
    assert audio_data.ndim == 1
    assert sample_rate == target_sr
    assert audio_data.dtype == np.float32
    assert np.max(np.abs(audio_data)) <= 1.0
    assert len(audio_data) > 0

def test_preprocess_audio_resample():
    """Test resampling in preprocess_audio."""
    original_sr = 44100
    target_sr = 11025
    # Create a dummy audio signal (e.g., 1 second sine wave)
    t = np.linspace(0, 1, original_sr, endpoint=False)
    audio_data_orig = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    processed_audio = preprocess_audio(audio_data_orig, original_sr, target_sample_rate=target_sr, normalize=False)

    assert processed_audio.shape[0] == int(len(audio_data_orig) * target_sr / original_sr)
    assert processed_audio.dtype == np.float32

def test_preprocess_audio_normalize():
    """Test normalization in preprocess_audio."""
    sr = 11025
    audio_data_unnormalized = np.array([0.0, 0.25, 0.5, -0.25, -0.5], dtype=np.float32) * 2.0 # Max abs is 1.0

    processed_audio = preprocess_audio(audio_data_unnormalized, sr, target_sample_rate=sr, normalize=True)

    assert np.max(np.abs(processed_audio)) == pytest.approx(1.0)
    assert processed_audio.dtype == np.float32

def test_preprocess_audio_no_op():
    """Test preprocess_audio when no operation should occur."""
    sr = 11025
    audio_data_orig = np.random.rand(sr).astype(np.float32) * 0.5 # Already normalized somewhat
    audio_data_orig_copy = audio_data_orig.copy()

    # Normalize=False, and sample rates match
    processed_audio = preprocess_audio(audio_data_orig, sr, target_sample_rate=sr, normalize=False)
    np.testing.assert_array_equal(processed_audio, audio_data_orig_copy)

    # Normalize=True, but data is already effectively normalized (max_val <= 1)
    # Note: if max_val is 0, it won't divide. If max_val is very small, it might amplify noise.
    # For this test, ensure max_val > 0
    audio_already_norm = audio_data_orig / np.max(np.abs(audio_data_orig)) if np.max(np.abs(audio_data_orig)) > 0 else audio_data_orig
    processed_audio_norm = preprocess_audio(audio_already_norm.copy(), sr, target_sample_rate=sr, normalize=True)
    np.testing.assert_allclose(processed_audio_norm, audio_already_norm, atol=1e-6)
