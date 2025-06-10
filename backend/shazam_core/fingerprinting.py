import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import logging
from collections import defaultdict
from .audio_utils import load_audio

# We will use the original Peak and Fingerprint dataclasses
@dataclass
class Peak:
    time_idx: int
    freq_idx: int
    time: float
    freq: float

@dataclass
class Fingerprint:
    hash: int
    song_id: int
    offset: int # Time offset in STFT frames

class Fingerprinter:
    """
    Generates audio fingerprints using a noise-resistant peak-pairing method,
    inspired by the original Shazam algorithm.
    """
    def __init__(
        self,
        sample_rate: int = 11025,
        window_size: int = 4096,
        hop_size: int = 1024,
        # --- Parameters Tuned for Robustness ---
        peak_neighborhood_size: int = 20, # How many pixels around a peak to check for max
        min_amplitude: float = -70.0,    # dB threshold for peak detection
        fan_value: int = 15,             # Number of peaks to pair with each anchor
        target_zone_t_start: int = 1,    # Target zone starts 1 frame after anchor
        target_zone_t_len: int = 100,    # Target zone is 100 frames long
        target_zone_f_len: int = 200     # Target zone is 200 freq bins wide
    ):
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.hop_size = hop_size
        self.peak_neighborhood_size = peak_neighborhood_size
        self.min_amplitude = min_amplitude
        self.fan_value = fan_value
        self.target_zone_t_start = target_zone_t_start
        self.target_zone_t_len = target_zone_t_len
        self.target_zone_f_len = target_zone_f_len

    def _find_peaks(self, spectrogram: np.ndarray, freqs: np.ndarray, times: np.ndarray) -> List[Peak]:
        """Finds local maxima in the spectrogram."""
        from scipy.ndimage import maximum_filter

        struct = np.ones((self.peak_neighborhood_size, self.peak_neighborhood_size), dtype=bool)
        local_max = maximum_filter(spectrogram, footprint=struct) == spectrogram
        
        # Filter out everything below the minimum amplitude
        local_max[spectrogram < self.min_amplitude] = False
        
        # Get coordinates of peaks
        freq_idxs, time_idxs = np.where(local_max)
        
        peaks = [
            Peak(time_idx, freq_idx, times[time_idx], freqs[freq_idx])
            for freq_idx, time_idx in zip(freq_idxs, time_idxs)
        ]
        return peaks

    def _create_hash(self, freq1: float, freq2: float, time_delta: int) -> int:
        """Creates a hash from two frequency points and their time difference."""
        # Pack three values into a 32-bit integer
        # We use bit shifting for efficient packing
        # [ time_delta (10 bits) | freq2 (10 bits) | freq1 (12 bits) ]
        f1_binned = int(freq1) & 0xFFF  # 12 bits for freq1
        f2_binned = int(freq2) & 0x3FF  # 10 bits for freq2
        dt_binned = int(time_delta) & 0x3FF  # 10 bits for time delta
        
        return (f1_binned << 20) | (f2_binned << 10) | dt_binned

    def generate_fingerprints(self, audio_data: np.ndarray, song_id: int = 0) -> List[Fingerprint]:
        from .spectrogram import generate_spectrogram

        # Generate a dB-scaled spectrogram, which is better for peak finding
        spectrogram, freqs, times = generate_spectrogram(
            audio_data, self.sample_rate, self.window_size, self.hop_size, db_scale=True
        )
        
        peaks = self._find_peaks(spectrogram, freqs, times)
        
        fingerprints = []
        # Sort peaks by time index first
        peaks.sort(key=lambda p: p.time_idx)

        for i, anchor_peak in enumerate(peaks):
            # Define the start and end of the target zone in time
            t_min = anchor_peak.time_idx + self.target_zone_t_start
            t_max = t_min + self.target_zone_t_len
            
            # Look ahead for target peaks
            for target_peak in peaks[i+1 : i + self.fan_value + 50]: # Optimized search window
                if target_peak.time_idx > t_max:
                    break
                
                # Check if the peak is within the time and frequency bounds of the target zone
                if t_min <= target_peak.time_idx < t_max:
                    time_delta = target_peak.time_idx - anchor_peak.time_idx
                    h = self._create_hash(anchor_peak.freq, target_peak.freq, time_delta)
                    fingerprints.append(Fingerprint(hash=h, song_id=song_id, offset=anchor_peak.time_idx))
            
            # Limit to fan_value hashes per anchor
            if len(fingerprints) > (i + 1) * self.fan_value:
                fingerprints = fingerprints[:(i+1) * self.fan_value]

        return fingerprints

    def fingerprint_file(self, file_path: str, song_id: int = 0) -> List[Fingerprint]:
        logging.info(f"[FINGERPRINTER] fingerprint_file: Attempting to read audio from {file_path}, target_sr={self.sample_rate}, song_id={song_id}")
        samples, sr = load_audio(file_path, target_sample_rate=self.sample_rate)
        if samples is None:
            logging.error(f"[FINGERPRINTER] fingerprint_file: Could not read audio from {file_path}")
            return []
        logging.info(f"[FINGERPRINTER] fingerprint_file: Read audio from {file_path}, song_id={song_id}. Actual sample rate: {sr}, Num samples: {len(samples)}")
        fingerprints = self.generate_fingerprints(samples, song_id=song_id)
        logging.info(f"[FINGERPRINTER] fingerprint_file: Generated {len(fingerprints)} Fingerprint objects for {file_path}, song_id={song_id}.")
        if fingerprints: 
            logging.info(f"[FINGERPRINTER] fingerprint_file: First 3 Fingerprints [(hash, offset)]: {[(fp.hash, fp.offset) for fp in fingerprints[:3]]}")
        return fingerprints


class FingerprintMatcher:
    """Matches fingerprints using a time-offset histogram."""
    def __init__(self, db_handler=None, fingerprinter_instance=None):
        self.db_handler = db_handler
        self.fingerprinter = fingerprinter_instance or Fingerprinter()

    def match_file(self, query_audio_path: str, top_n: int = 1, min_absolute_matches: int = 2) -> List[Dict[str, Any]]:
        logging.info(f"[MATCHER] match_file: Generating fingerprints for query file: {query_audio_path}")
        query_fingerprints = self.fingerprinter.fingerprint_file(query_audio_path) # List[Fingerprint]
        if not query_fingerprints:
            logging.warning(f"[MATCHER] match_file: No fingerprints generated for query file: {query_audio_path}")
            return [] # Return empty list

        logging.info(f"[MATCHER] match_file: Generated {len(query_fingerprints)} query Fingerprints for {query_audio_path}.")
        if query_fingerprints:
            logging.info(f"[MATCHER] match_file: First 3 query Fingerprints [(hash, offset)]: {[(fp.hash, fp.offset) for fp in query_fingerprints[:3]]}")

        query_hashes_for_db = [fp.hash for fp in query_fingerprints]
        # Create a dictionary for fast lookup of query offsets by hash
        query_fingerprint_map: Dict[int, int] = {fp.hash: fp.offset for fp in query_fingerprints}
        
        logging.info(f"[MATCHER] match_file: Querying DB with {len(query_hashes_for_db)} unique hashes. First 3: {query_hashes_for_db[:3] if query_hashes_for_db else 'N/A'}")
        # db_matches is List[Tuple[int, int, int]] -> (hash, song_id, db_offset/timestamp)
        db_matches = self.db_handler.get_matches_by_hashes(query_hashes_for_db)
        
        logging.info(f"[MATCHER] match_file: DB returned {len(db_matches)} raw matches. First 3: {db_matches[:3] if db_matches else 'N/A'}")
        if not db_matches:
            logging.info("[MATCHER] match_file: No raw matches returned from DB for any query hashes.")
            return []

        song_offset_histograms: Dict[int, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        processed_db_matches = 0

        for db_hash, song_id, db_offset_from_db in db_matches: # db_offset_from_db is the timestamp stored in DB
            # Ensure song_id is an integer (defensive coding)
            song_id = int(song_id)

            # song_id is already an int from db_matches if schema is correct, but ensure
            song_id = int(song_id)
            
            if db_hash in query_fingerprint_map:
                query_offset = query_fingerprint_map[db_hash]
                
                try:
                    offset_delta = int(db_offset_from_db) - int(query_offset)
                except (ValueError, TypeError) as e:
                    logging.warning(f"[MATCHER] match_file: Skipping match due to invalid offset types. db_hash={db_hash}, db_offset={db_offset_from_db}, query_offset={query_offset}. Error: {e}")
                    continue
                
                song_offset_histograms[song_id][offset_delta] += 1
                processed_db_matches += 1

        logging.info(f"[MATCHER] match_file: Processed {processed_db_matches} db_matches into offset histograms for {len(song_offset_histograms)} songs.")
        if not song_offset_histograms:
            logging.info("[MATCHER] MATCH FAILED: No songs had any offset matches after processing DB results.")
            return []

        results = []
        for song_id, histogram in song_offset_histograms.items():
            if not histogram: continue
            
            best_offset, score = max(histogram.items(), key=lambda item: item[1])
            
            if score < min_absolute_matches: continue

            match_time_in_seconds = (best_offset * self.fingerprinter.hop_size) / self.fingerprinter.sample_rate

            results.append({
                'song_id': song_id,
                'score': score,
                'offset_seconds': max(0, match_time_in_seconds)
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]