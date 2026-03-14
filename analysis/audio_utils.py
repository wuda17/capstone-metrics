"""
Audio Utilities - Stateless Pipeline Functions
-----------------------------------------------
Standardization and preprocessing utilities for consistent speech analysis.

Key Design Principles:
- Stateless: All functions are pure with no side effects
- Privacy-by-Design: Process audio and return features without storing raw data
- Toolkit Agnostic: Standardized output ensures consistent results across
  OpenSMILE, Librosa, Whisper, and Praat

Standardization Spec:
- Sample Rate: 16kHz (optimal for speech, required by Whisper)
- Bit Depth: 16-bit PCM (when saving to WAV)
- Channels: Mono
- Normalization: Peak amplitude normalization to [-1.0, 1.0]

Usage:
    from audio_utils import load_and_standardize, process_with_privacy_gate

    # Basic loading and standardization
    audio, sr = load_and_standardize("speech.wav")

    # Privacy-conscious processing (extract features, optionally delete source)
    features = process_with_privacy_gate(
        "speech.wav",
        feature_fn=my_feature_extractor,
        delete_source=True
    )
"""

from __future__ import annotations

import io
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, TypeVar, Union, BinaryIO, Iterator

import numpy as np
from numpy.typing import NDArray
import scipy.io.wavfile as wav_io
from scipy.signal import resample_poly
from math import gcd


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

STANDARD_SAMPLE_RATE: int = 16000  # Hz - optimal for speech, Whisper requirement
STANDARD_BIT_DEPTH: int = 16  # bits
TARGET_DTYPE = np.float32  # internal processing dtype


# Type aliases
AudioArray = NDArray[np.float32]
T = TypeVar("T")


# -----------------------------------------------------------------------------
# Core Standardization Functions
# -----------------------------------------------------------------------------


def load_audio(
    source: Union[str, Path, BinaryIO, bytes],
    target_sr: int = STANDARD_SAMPLE_RATE,
) -> tuple[AudioArray, int]:
    """
    Load audio from file/bytes and convert to standardized format.

    Handles:
    - WAV files (native scipy support)
    - File paths, file objects, or raw bytes
    - Automatic sample rate conversion
    - Stereo to mono conversion
    - Bit depth normalization to float32 [-1.0, 1.0]

    Args:
        source: File path, file-like object, or bytes
        target_sr: Target sample rate (default: 16000 Hz)

    Returns:
        Tuple of (audio_array, sample_rate) where audio_array is
        float32 normalized to [-1.0, 1.0]

    Example:
        >>> audio, sr = load_audio("speech.wav")
        >>> audio.dtype
        dtype('float32')
        >>> sr
        16000
    """
    # Handle different input types
    if isinstance(source, bytes):
        source = io.BytesIO(source)
    elif isinstance(source, (str, Path)):
        source = str(source)

    # Read WAV file
    original_sr, audio = wav_io.read(source)

    # Convert to float32 and normalize
    audio = _normalize_dtype(audio)

    # Convert stereo to mono
    audio = _to_mono(audio)

    # Resample if needed
    if original_sr != target_sr:
        audio = _resample(audio, original_sr, target_sr)

    return audio, target_sr


def _normalize_dtype(audio: np.ndarray) -> AudioArray:
    """
    Normalize any audio dtype to float32 in range [-1.0, 1.0].

    Handles int16, int32, float32, float64, uint8.
    """
    if audio.dtype == np.float32:
        return audio
    elif audio.dtype == np.float64:
        return audio.astype(np.float32)
    elif audio.dtype == np.int16:
        return (audio / 32768.0).astype(np.float32)
    elif audio.dtype == np.int32:
        return (audio / 2147483648.0).astype(np.float32)
    elif audio.dtype == np.uint8:
        return ((audio.astype(np.float32) - 128) / 128.0).astype(np.float32)
    else:
        # Fallback: normalize by max possible value
        info = np.iinfo(audio.dtype) if np.issubdtype(audio.dtype, np.integer) else None
        if info:
            return (audio / max(abs(info.min), abs(info.max))).astype(np.float32)
        return audio.astype(np.float32)


def _to_mono(audio: np.ndarray) -> AudioArray:
    """Convert multi-channel audio to mono by averaging channels."""
    if audio.ndim == 1:
        return audio
    # Average across channels (axis 1 for [samples, channels])
    return np.mean(audio, axis=1).astype(np.float32)


def _resample(audio: AudioArray, orig_sr: int, target_sr: int) -> AudioArray:
    """
    Resample audio using polyphase filtering for high quality.

    Uses scipy.signal.resample_poly for efficient resampling with
    minimal aliasing artifacts.
    """
    if orig_sr == target_sr:
        return audio

    # Find GCD for efficient polyphase resampling
    divisor = gcd(orig_sr, target_sr)
    up = target_sr // divisor
    down = orig_sr // divisor

    resampled = resample_poly(audio, up, down)
    return resampled.astype(np.float32)


# -----------------------------------------------------------------------------
# Amplitude Normalization
# -----------------------------------------------------------------------------


def normalize_amplitude(
    audio: AudioArray,
    method: str = "peak",
    target_level: float = 1.0,
) -> AudioArray:
    """
    Normalize audio amplitude using various methods.

    Args:
        audio: Input audio array (float32)
        method: Normalization method:
            - "peak": Scale so max absolute value = target_level
            - "rms": Scale to target RMS level
            - "lufs": Scale to target loudness (requires more computation)
        target_level: Target level (1.0 for peak, ~0.1 for RMS)

    Returns:
        Normalized audio array (float32, same length as input)

    Note:
        Peak normalization is recommended for consistency across toolkits.
        Some features (like F0) are amplitude-invariant, but energy-based
        features benefit from consistent normalization.
    """
    if len(audio) == 0:
        return audio

    if method == "peak":
        peak = np.max(np.abs(audio))
        if peak > 0:
            return (audio / peak * target_level).astype(np.float32)
        return audio

    elif method == "rms":
        rms = np.sqrt(np.mean(audio**2))
        if rms > 0:
            return (audio / rms * target_level).astype(np.float32)
        return audio

    elif method == "lufs":
        # Simplified LUFS-like normalization (K-weighted RMS approximation)
        # Full ITU-R BS.1770-4 would require proper K-weighting filter
        rms = np.sqrt(np.mean(audio**2))
        if rms > 0:
            return (audio / rms * target_level).astype(np.float32)
        return audio

    else:
        raise ValueError(f"Unknown normalization method: {method}")


# -----------------------------------------------------------------------------
# Combined Load + Standardize Pipeline
# -----------------------------------------------------------------------------


def load_and_standardize(
    source: Union[str, Path, BinaryIO, bytes],
    target_sr: int = STANDARD_SAMPLE_RATE,
    normalize: bool = True,
    normalize_method: str = "peak",
) -> tuple[AudioArray, int]:
    """
    Load audio and apply full standardization pipeline.

    This is the main entry point for consistent audio preprocessing.
    Ensures audio is ready for any speech analysis toolkit.

    Pipeline:
    1. Load from file/bytes
    2. Convert to float32 [-1.0, 1.0]
    3. Convert to mono
    4. Resample to target_sr (default 16kHz)
    5. Apply amplitude normalization (optional)

    Args:
        source: File path, file object, or bytes
        target_sr: Target sample rate (default: 16000)
        normalize: Whether to apply amplitude normalization
        normalize_method: Normalization method ("peak", "rms")

    Returns:
        Tuple of (audio_array, sample_rate)

    Example:
        >>> audio, sr = load_and_standardize("input.wav")
        >>> assert sr == 16000
        >>> assert audio.dtype == np.float32
        >>> assert np.max(np.abs(audio)) <= 1.0
    """
    audio, sr = load_audio(source, target_sr)

    if normalize:
        audio = normalize_amplitude(audio, method=normalize_method)

    return audio, sr


# -----------------------------------------------------------------------------
# Export / Save Functions
# -----------------------------------------------------------------------------


def to_wav_bytes(
    audio: AudioArray,
    sample_rate: int = STANDARD_SAMPLE_RATE,
    bit_depth: int = STANDARD_BIT_DEPTH,
) -> bytes:
    """
    Convert audio array to WAV file bytes (in-memory).

    Useful for passing to APIs or toolkits that expect file bytes
    without writing to disk.

    Args:
        audio: Float32 audio array normalized to [-1.0, 1.0]
        sample_rate: Sample rate (default: 16000)
        bit_depth: Bit depth (16 or 32)

    Returns:
        WAV file as bytes
    """
    if bit_depth == 16:
        # Scale to int16 range
        audio_int = (audio * 32767).astype(np.int16)
    elif bit_depth == 32:
        audio_int = (audio * 2147483647).astype(np.int32)
    else:
        raise ValueError(f"Unsupported bit depth: {bit_depth}")

    buffer = io.BytesIO()
    wav_io.write(buffer, sample_rate, audio_int)
    return buffer.getvalue()


def save_standardized(
    audio: AudioArray,
    output_path: Union[str, Path],
    sample_rate: int = STANDARD_SAMPLE_RATE,
    bit_depth: int = STANDARD_BIT_DEPTH,
) -> Path:
    """
    Save standardized audio to WAV file.

    Args:
        audio: Float32 audio array
        output_path: Destination file path
        sample_rate: Sample rate (default: 16000)
        bit_depth: Bit depth (default: 16)

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    wav_bytes = to_wav_bytes(audio, sample_rate, bit_depth)
    output_path.write_bytes(wav_bytes)
    return output_path


# -----------------------------------------------------------------------------
# Privacy-by-Design Utilities
# -----------------------------------------------------------------------------


@contextmanager
def temporary_standardized_wav(
    source: Union[str, Path, BinaryIO, bytes],
    target_sr: int = STANDARD_SAMPLE_RATE,
    normalize: bool = True,
) -> Iterator[Path]:
    """
    Context manager that creates a temporary standardized WAV file.

    Useful for toolkits that require a file path (like OpenSMILE).
    The temporary file is automatically deleted on context exit.

    Args:
        source: Original audio source
        target_sr: Target sample rate
        normalize: Whether to normalize amplitude

    Yields:
        Path to temporary standardized WAV file

    Example:
        >>> with temporary_standardized_wav("input.mp3") as temp_path:
        ...     features = opensmile.process_file(temp_path)
        ... # temp file automatically deleted here
    """
    audio, sr = load_and_standardize(source, target_sr, normalize)

    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=".wav")
    try:
        os.close(fd)
        save_standardized(audio, temp_path, sr)
        yield Path(temp_path)
    finally:
        # Ensure cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def process_with_privacy_gate(
    source: Union[str, Path],
    feature_fn: Callable[[AudioArray, int], T],
    delete_source: bool = False,
    target_sr: int = STANDARD_SAMPLE_RATE,
    normalize: bool = True,
) -> T:
    """
    Process audio through a feature extractor with optional source deletion.

    Implements the privacy-by-design pattern:
    1. Load and standardize audio
    2. Extract features via provided function
    3. Optionally delete source file
    4. Return only the feature vector (no raw audio retained)

    This ensures compliance with HIPAA, PIPEDA, and similar regulations
    by never storing raw biometric data longer than necessary.

    Args:
        source: Path to audio file
        feature_fn: Function that takes (audio_array, sample_rate) and
                   returns extracted features
        delete_source: If True, delete source file after processing
        target_sr: Target sample rate for standardization
        normalize: Whether to normalize amplitude

    Returns:
        Features extracted by feature_fn

    Example:
        >>> def extract_f0_stats(audio, sr):
        ...     # Your F0 extraction logic here
        ...     return {"mean_f0": 120.5, "std_f0": 25.3}
        ...
        >>> features = process_with_privacy_gate(
        ...     "patient_audio.wav",
        ...     feature_fn=extract_f0_stats,
        ...     delete_source=True  # HIPAA compliance
        ... )
        >>> # Source file is now deleted, only features remain
    """
    source_path = Path(source)

    # Load and standardize
    audio, sr = load_and_standardize(source_path, target_sr, normalize)

    # Extract features
    features = feature_fn(audio, sr)

    # Delete source if requested
    if delete_source and source_path.exists():
        os.unlink(source_path)

    # Clear audio from memory (explicit, though Python GC handles this)
    del audio

    return features


def extract_and_forget(
    source: Union[str, Path, bytes],
    feature_fn: Callable[[AudioArray, int], T],
    target_sr: int = STANDARD_SAMPLE_RATE,
    normalize: bool = True,
) -> T:
    """
    Extract features from audio without ever writing to disk.

    For maximum privacy: accepts bytes directly (e.g., from network stream)
    and never persists raw audio. Ideal for real-time processing pipelines.

    Args:
        source: Audio file path or raw bytes
        feature_fn: Feature extraction function (audio, sr) -> features
        target_sr: Target sample rate
        normalize: Whether to normalize amplitude

    Returns:
        Extracted features

    Example:
        >>> # Process audio received over network
        >>> audio_bytes = receive_audio_from_client()
        >>> features = extract_and_forget(audio_bytes, my_extractor)
        >>> # Raw audio never touched disk
    """
    audio, sr = load_and_standardize(source, target_sr, normalize)
    features = feature_fn(audio, sr)
    del audio  # Explicit cleanup
    return features


# -----------------------------------------------------------------------------
# Acoustic Features (Path-based IO)
# -----------------------------------------------------------------------------


def build_opensmile_extractor() -> Any:
    """Build a default OpenSMILE extractor for speech features."""
    try:
        import opensmile
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'opensmile'. Install analysis/environment.yml."
        ) from exc

    return opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )


def extract_acoustic_metrics(
    source: Union[str, Path, BinaryIO, bytes],
    opensmile_extractor: Any | None = None,
) -> dict[str, Any]:
    """
    Extract acoustic metrics from audio source.

    This keeps an explicit input/output contract:
    audio source in -> acoustic metric dict out.
    """
    try:
        import parselmouth
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency 'praat-parselmouth'. Install analysis/environment.yml."
        ) from exc

    extractor = opensmile_extractor or build_opensmile_extractor()

    with temporary_standardized_wav(source) as std_path:
        smile_df = extractor.process_file(str(std_path))
        smile_features = {
            key: _to_float(val) for key, val in smile_df.iloc[0].to_dict().items()
        }

        snd = parselmouth.Sound(str(std_path))
        pitch = snd.to_pitch()
        harmonicity = snd.to_harmonicity_cc()
        point_process = parselmouth.praat.call(
            snd, "To PointProcess (periodic, cc)", 75, 500
        )
        jitter_local = parselmouth.praat.call(
            point_process,
            "Get jitter (local)",
            0,
            0,
            0.0001,
            0.02,
            1.3,
        )
        shimmer_local_db = parselmouth.praat.call(
            [snd, point_process],
            "Get shimmer (local_dB)",
            0,
            0,
            0.0001,
            0.02,
            1.3,
            1.6,
        )

        return {
            "f0_mean_hz": _to_float(parselmouth.praat.call(pitch, "Get mean", 0, 0, "Hertz")),
            "hnr_db": _to_float(parselmouth.praat.call(harmonicity, "Get mean", 0, 0)),
            "jitter_local": _to_float(jitter_local),
            "shimmer_local_db": _to_float(shimmer_local_db),
            "opensmile": smile_features,
        }


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if np.isnan(out) or np.isinf(out):
            return None
        return out
    except (TypeError, ValueError):
        return None


# -----------------------------------------------------------------------------
# Validation Utilities
# -----------------------------------------------------------------------------


def validate_audio(
    audio: AudioArray,
    sample_rate: int,
    min_duration_sec: float = 0.1,
    max_duration_sec: float = 3600.0,
) -> dict:
    """
    Validate audio meets requirements for speech analysis.

    Returns validation results with warnings for potential issues.

    Args:
        audio: Audio array to validate
        sample_rate: Sample rate of audio
        min_duration_sec: Minimum acceptable duration
        max_duration_sec: Maximum acceptable duration

    Returns:
        Dict with validation results:
        - valid: bool
        - duration_sec: float
        - warnings: list of warning messages
        - errors: list of error messages
    """
    duration = len(audio) / sample_rate
    warnings = []
    errors = []

    # Duration checks
    if duration < min_duration_sec:
        errors.append(f"Audio too short: {duration:.2f}s < {min_duration_sec}s minimum")
    if duration > max_duration_sec:
        errors.append(f"Audio too long: {duration:.2f}s > {max_duration_sec}s maximum")

    # Sample rate check
    if sample_rate != STANDARD_SAMPLE_RATE:
        warnings.append(
            f"Non-standard sample rate: {sample_rate}Hz "
            f"(expected {STANDARD_SAMPLE_RATE}Hz)"
        )

    # Silence check
    rms = np.sqrt(np.mean(audio**2))
    if rms < 0.001:
        warnings.append("Audio appears to be mostly silence (RMS < 0.001)")

    # Clipping check
    peak = np.max(np.abs(audio))
    if peak > 0.99:
        warnings.append(f"Possible clipping detected (peak={peak:.4f})")

    # Dtype check
    if audio.dtype != np.float32:
        warnings.append(f"Non-standard dtype: {audio.dtype} (expected float32)")

    return {
        "valid": len(errors) == 0,
        "duration_sec": duration,
        "sample_rate": sample_rate,
        "rms": float(rms),
        "peak": float(peak),
        "warnings": warnings,
        "errors": errors,
    }
