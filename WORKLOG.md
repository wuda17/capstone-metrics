# Capstone Work Log

**Project:** Speech-Based Cognitive Health Monitoring System  
**Term:** Winter 2026

---

## Project Goal

Develop a speech analysis system that extracts clinically-relevant cognitive markers from spoken language, designed for longitudinal monitoring of cognitive health in elderly populations. The system prioritizes privacy-by-design principles to ensure compliance with healthcare data regulations.

---

## Work Completed

### 1. Audio Preprocessing Pipeline

Designed and implemented a standardized audio preprocessing system to ensure consistent input across all analysis components.

**Key decisions:**
- Standardized on 16kHz sample rate (optimal for speech, required by Whisper ASR)
- Mono channel with peak amplitude normalization
- Supports multiple input formats (files, byte streams, file objects)

**Privacy considerations:**
- Built "privacy gate" pattern that extracts features then optionally deletes source audio
- Enables processing of streaming audio without ever writing to disk
- Designed for HIPAA and PIPEDA compliance in healthcare settings

---

### 2. Speech Metrics Implementation

Implemented core speech metrics identified in cognitive health literature as markers for decline:

**Type-Token Ratio (TTR)** - Lexical diversity measure
- Calculated as unique words / total words
- Decline in TTR indicates word-finding difficulties or simplified vocabulary
- Key longitudinal marker for early cognitive changes

**Speech Rate** - Temporal fluency measure
- Words per minute calculation
- Normal range: 75-125 wpm
- Slower rates may indicate cognitive slowing; faster rates may indicate pressured speech

**Pause Analysis** - Silence pattern detection
- Research suggests "the sound of silence" is more clinically significant than speech itself
- Implemented three-tier classification:
  - Short pauses (0.1-0.5s): Normal conversational
  - Medium pauses (0.5-1.0s): Notable hesitations
  - Long pauses (>1.0s): Clinically significant, may indicate word-finding difficulty

---

### 3. Transcription System

Integrated OpenAI Whisper for automatic speech recognition with word-level timestamps.

**Features:**
- Extracts precise timing for each spoken word
- Enables accurate pause detection between words
- Confidence scores for transcription quality assessment
- Async support for integration with real-time pipelines

**Model selection:** Configurable model sizes (tiny → large) to balance accuracy vs. processing speed depending on deployment context.

---

### 4. Data Structures for Cognitive Tracking

Designed data models for two levels of analysis:

**Utterance-level metrics:**
- Individual speech segments with computed cognitive markers
- Word timing and confidence data
- Pause locations and classifications
- Exportable to JSON for storage/analysis

**Session-level aggregation:**
- Combines multiple utterances into session summary
- Computes averages and totals across a conversation
- Separates user speech from other speakers
- Designed for longitudinal tracking across multiple sessions

---

### 5. Voice Activity Detection (VAD) Recording

Built a recording system that automatically segments continuous audio into individual utterances.

**Approach:**
- Uses WebRTC VAD for robust speech/silence detection
- Configurable sensitivity levels
- Pre-buffering ensures utterance beginnings aren't clipped
- Outputs separate audio files per utterance for downstream processing

**Use case:** Enables passive monitoring where the system continuously listens and processes only when speech is detected.

---

### 6. End-to-End Demo Pipeline

Created a complete demonstration of the analysis workflow:

1. Load and validate audio
2. Transcribe with word-level timestamps
3. Compute cognitive markers
4. Generate clinical interpretation
5. Optionally delete source audio (privacy mode)
6. Export metrics to JSON

**Clinical interpretation output** provides human-readable assessments of each metric against established norms.

---

### 7. Acoustic Feature Exploration

Explored OpenSMILE toolkit for additional acoustic features beyond transcription-based metrics.

**Feature sets evaluated:**
- **eGeMAPSv02** (88 features): Prosodic features including pitch, loudness, voice quality
- **ComParE_2016** (6373 features): Comprehensive set used in depression/anxiety detection research

**Finding:** ComParE features are better suited for mental health applications because conditions like depression manifest as subtle, distributed acoustic changes rather than discrete emotions.

---

## Technical Environment

- Python 3.11
- Core libraries: NumPy, SciPy, PyTorch
- Speech processing: OpenAI Whisper, WebRTC VAD, OpenSMILE
- Audio handling: PyAudio, FFmpeg

---

## Clinical Metrics Reference

| Metric | Normal Range | Clinical Significance |
|--------|--------------|----------------------|
| Type-Token Ratio | 0.5 - 0.7 | Lower values suggest reduced vocabulary diversity |
| Speech Rate | 75 - 125 wpm | Outside range may indicate cognitive or emotional changes |
| Long Pauses (>1s) | Minimal | Frequent long pauses suggest word-finding difficulty |
| Pause Ratio | < 20% | High silence percentage may indicate processing delays |

---

## Design Principles

1. **Privacy-by-design:** Raw audio is processed and can be immediately deleted; only extracted features are retained
2. **Clinical grounding:** Metrics selected based on cognitive health research literature
3. **Longitudinal focus:** Data structures designed for tracking changes over time
4. **Modularity:** Components can be used independently or as integrated pipeline
5. **Async-ready:** Supports integration with real-time applications

---

## Next Steps

- Integrate acoustic features (pitch variability, voice quality) with transcription-based metrics
- Build persistent storage for longitudinal tracking
- Develop visualization dashboard for cognitive trends
- Conduct validation with sample recordings
- Explore real-time streaming analysis
