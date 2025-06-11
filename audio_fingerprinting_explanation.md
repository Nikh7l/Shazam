# Audio Fingerprinting and Matching: The Implementation Details

## 1. Introduction
Audio fingerprinting is a technology that allows for the identification of audio samples. Just like a human fingerprint uniquely identifies an individual, an audio fingerprint uniquely identifies a piece of audio. This technology is famously used by apps like Shazam to recognize songs, but it also has applications in copyright detection, broadcast monitoring, and duplicate content detection.

The core idea is to extract a condensed digital summary (the "fingerprint") from an audio signal, which can then be used to quickly find a match within a large database of fingerprints. This document describes the specific implementation used in this project.

## 2. Generating Audio Fingerprints: The `Fingerprinter` Service

The process of generating an audio fingerprint is handled by the `Fingerprinter` class located in `backend/shazam_core/fingerprinting.py`. It transforms raw audio into a robust and compact representation.

### 2.1. Audio Preprocessing (`backend/shazam_core/audio_utils.py`)
Before fingerprinting, audio undergoes several preprocessing steps using functions in `audio_utils.py`:
- **Loading:** Audio files are loaded using `pydub` (via `load_audio`), which supports various formats.
- **Mono Conversion:** Stereo audio is converted to a single (mono) channel.
- **Resampling:** The audio is resampled to a `target_sample_rate` of **11025 Hz**, as defined in the `Fingerprinter` class.
- **Normalization:** Samples are converted to `np.float32` and normalized to the range [-1, 1].

### 2.2. Spectrogram Generation (`backend/shazam_core/spectrogram.py`)
The `Fingerprinter` uses the `generate_spectrogram` function to create a spectrogram:
- **STFT (Short-Time Fourier Transform):** Applied with a `window_size` of **4096 samples** and a `hop_size` of **1024 samples**. A Hann window (`window_type='hann'`) is used.
- **Magnitude Spectrum:** The absolute values of the STFT result are taken.
- **dB Scaling:** The magnitude spectrum is converted to a decibel (dB) scale using the `amplitude_to_db` function. This dB-scaled spectrogram is used for peak finding, as it better reflects human perception of loudness and helps in identifying prominent acoustic features.

### 2.3. Peak Finding (Landmarking) (`Fingerprinter._find_peaks` method)
Prominent peaks (landmarks) are identified directly from the dB-scaled spectrogram:
- **Local Maxima:** `scipy.ndimage.maximum_filter` is used to find local maxima within a `peak_neighborhood_size` of **20x20** (frames x frequency bins).
- **Amplitude Thresholding:** Peaks below a `min_amplitude` of **-70 dB** are discarded.
- **Output:** A list of `Peak` objects, where each peak stores its time index (`time_idx`), frequency index (`freq_idx`), actual time (`time`), and frequency (`freq`).

## 3. Hashing Fingerprints (`Fingerprinter._create_hash` and `generate_fingerprints` methods)

Once peaks are identified, they are combined into hashes. This system uses a combinatorial hashing approach:

### 3.1. Peak Pairing (Combinatorial Hashing)
- **Anchor and Target Peaks:** Peaks are sorted by time. Each peak serves as an "anchor peak."
- **Target Zone:** For each anchor peak, the algorithm searches for subsequent "target peaks" within a defined "target zone." This zone starts `target_zone_t_start=1` frame after the anchor and spans `target_zone_t_len=100` frames in time and `target_zone_f_len=200` frequency bins in width (though the actual implementation detail for frequency width in `generate_fingerprints` is implicitly handled by iterating through subsequent peaks rather than a strict frequency bin difference for target selection).
- **Fan-out:** Each anchor peak is paired with up to `fan_value=15` target peaks that fall within this zone.

### 3.2. Hash Generation (`_create_hash` method)
For each valid (anchor_peak, target_peak) pair, a single integer hash is generated using:
- `anchor_peak.freq` (frequency of the anchor peak)
- `target_peak.freq` (frequency of the target peak)
- `time_delta = target_peak.time_idx - anchor_peak.time_idx` (difference in STFT frame indices)

These three values are packed into a 32-bit integer hash using bit shifting:
- `freq1` (anchor frequency): 12 bits (`int(anchor_peak.freq) & 0xFFF`)
- `freq2` (target frequency): 10 bits (`int(target_peak.freq) & 0x3FF`)
- `time_delta`: 10 bits (`int(time_delta) & 0x3FF`)
The formula is: `(f1_binned << 20) | (f2_binned << 10) | dt_binned`.

### 3.3. Fingerprint Objects
Each generated hash is stored as a `Fingerprint` object (dataclass defined in `fingerprinting.py`) containing:
- `hash`: The integer hash value.
- `song_id`: The ID of the song (set during ingestion or matching).
- `offset`: The time index (`time_idx`) of the **anchor peak** in STFT frames. This `offset` is crucial for temporal alignment during matching.

## 4. Database Storage and Retrieval (`backend/database/db_handler.py` and `schema.sql`)

The generated fingerprints and song metadata are managed by `DatabaseHandler` using an SQLite database.

### 4.1. Database Schema (`schema.sql`)
- **`songs` table:** Stores song metadata like `id` (PK), `title`, `artist`, `album`, `duration_ms`, `source_type` (e.g., 'spotify', 'youtube'), `source_id`, `cover_url`, `youtube_id`, etc. It has a UNIQUE constraint on `(source_type, source_id)`.
- **`fingerprints` table:** Stores the individual fingerprint entries:
    - `hash` (INTEGER): The generated hash value.
    - `song_id` (INTEGER): Foreign key to `songs.id`.
    - `timestamp` (INTEGER): This is the `offset` (time index of the anchor peak in STFT frames) from the `Fingerprint` object.
- **Indexes:**
    - An index on `fingerprints.hash` (`idx_fingerprints_hash`) is critical for fast lookups during matching.
    - An index on `fingerprints.song_id` (`idx_fingerprints_song_id`) aids in managing fingerprints per song.

### 4.2. Song Ingestion (`backend/services/song_ingester.py`)
The `SongIngester` service handles adding new songs:
1.  Downloads audio (e.g., from YouTube, potentially found via Spotify metadata).
2.  Preprocesses the audio (mono, 11025 Hz, normalized) using `audio_utils.load_audio`.
3.  Generates fingerprints using `Fingerprinter.generate_fingerprints()`.
4.  Adds song metadata to the `songs` table via `db_handler.add_song()`.
5.  Adds the list of `Fingerprint` objects to the `fingerprints` table via `db_handler.add_fingerprints()`, storing each `(hash, song_id, offset)`.

## 5. Matching an Unknown Audio Sample (`backend/shazam_core/fingerprinting.py::FingerprintMatcher`)

The `FingerprintMatcher` class identifies unknown audio samples:

### 5.1. Query Fingerprinting
The unknown audio sample is processed through the exact same fingerprint generation pipeline (Sections 2 & 3) to get a list of query `Fingerprint` objects (with their hashes and offsets relative to the start of the query sample).

### 5.2. Database Lookup (`db_handler.get_matches_by_hashes`)
- The hashes from the query fingerprints are extracted.
- The `get_matches_by_hashes` method in `db_handler` is called. This method efficiently retrieves all entries from the `fingerprints` table in the database that have a hash matching one of the query hashes.
- This returns a list of `(db_hash, song_id, db_timestamp)` tuples, where `db_timestamp` is the offset of the anchor peak stored for that hash in the database.

### 5.3. Alignment and Scoring (Histogramming - `FingerprintMatcher.match_file` method)
This is the core matching logic:
- A `query_fingerprint_map` is created to quickly find the `offset` of a query hash.
- For each `(db_hash, song_id, db_timestamp)` returned from the database that has a corresponding `db_hash` in the query's fingerprints:
    - The system calculates an `offset_delta = db_timestamp - query_fingerprint_offset`. This `offset_delta` represents the difference in time (in STFT frames) between the start of the database song and the start of the query sample, assuming this particular hash pair is a true match.
- **Histogramming:** A histogram of these `offset_delta` values is built for each candidate `song_id`. The keys of the histogram are the `offset_delta` values, and the values are the number of hash pairs that support that specific time difference for that song.
    - `song_offset_histograms: Dict[int, Dict[int, int]]` stores these.
- **Identifying a Match:**
    - For each song, the `offset_delta` with the highest count (score) in its histogram is found. This is the most likely alignment.
    - If this `score` is below a `min_absolute_matches` threshold (defaulting to 2), the match is discarded.
    - The final result includes the `song_id`, the `score` (number of aligned hashes), and the `offset_seconds` (calculated from the best `offset_delta`, hop size, and sample rate).
- The results are sorted by score in descending order, and the top N (default 1) matches are returned.

## 6. Summary
The system implements an audio fingerprinting and matching pipeline based on:
1.  **Standardized Audio Input:** Mono, 11025 Hz, normalized audio.
2.  **Spectrogram Analysis:** dB-scaled spectrogram using STFT with specific windowing parameters.
3.  **Peak Finding:** Identifying prominent time-frequency points from the spectrogram.
4.  **Combinatorial Hashing:** Creating robust hashes from pairs of (anchor, target) peaks based on their frequencies and time delta, packed into a 32-bit integer.
5.  **Efficient Database:** SQLite database storing song metadata and fingerprints (`(hash, song_id, anchor_peak_offset)`), with indexing on hashes for fast lookups.
6.  **Histogram-based Matching:** Aligning query fingerprints against database fingerprints by finding consistent time offsets (`offset_delta`) between them.

This approach provides a good balance of robustness to noise and speed for identifying music within a large database.

### Advantages:
- **Speed:** Hashing allows for very fast lookups, and indexed database queries are efficient.
- **Robustness:** The peak-pairing method is designed to be resistant to some levels of noise, compression artifacts, and minor distortions.
- **Scalability:** The technique can scale to reasonably large databases of songs.

### Disadvantages/Challenges:
- **Sensitivity to extreme modifications:** Significant changes in tempo, pitch, or extensive edits can still break the fingerprint.
- **Cover versions/Live versions:** These may not match the studio version unless their specific fingerprints are also in the database.
- **Computational cost of fingerprinting:** While matching is fast, generating fingerprints for a massive library can be computationally intensive.
