# Plan: Localhost Real-Time Speech-Health Monitoring Demo

## 1. Project Goal

Develop a bimodal (acoustic + linguistic) monitoring system that polls for new audio recordings, extracts "Anchor Metrics" (Temporal, Lexical, Prosodic), aggregates them to show longitudinal trends, and displays them on a real-time dashboard.

## 2. Infrastructure & Technologies

- **Data Source:** Raspberry Pi capturing audio and transferring via SSH. Assume all audio files are normalized and convertedto the same format
- **Service Trigger:** Local directory polling for new `.wav` files.
- **Analysis Engines:**
  - `openSMILE`: eGeMAPS feature set for clinical standardized features.
  - `Parselmouth` (Praat): Precise voice quality (Jitter/Shimmer/HNR).
  - `Librosa`: Spectral centroid, flatness, and intensity.
  - `OpenAI Whisper`: Transcription for lexical analysis and pause timestamping.

## 3. Implementation Steps

### Step 1: Real-Time Ingestion Service (The Poller)

Your service must monitor the incoming directory and immediately tag files with metadata to ensure the dashboard remains "real-time."

- **Metadata Annotation:** Every `.wav` file must be linked to its creation `timestamp` and `day`. This is critical for the Aggregator to calculate windowed averages and for the Dashboard to display a sequence-accurate conversation log.

### Step 2: Metrics Service (Snapshot Analysis)

For every new file, run a "Snapshot" script that outputs a numerical feature vector.

- **Temporal & Fluency:** Calculate **Pause Rate** and **Speech Rate** using Whisper timestamps. These are the most effective markers for word-retrieval difficulty and cognitive load.
- **Prosody & Voice Quality:** Use Parselmouth to extract **Jitter**, **Shimmer**, and **Fundamental Frequency ($F_0$)**. High jitter is a sensitive indicator of neuromotor control issues.
- **Lexical Extraction:** Calculate the **Type-Token Ratio (TTR)** from the Whisper transcript to track vocabulary richness.

### Step 3: Aggregator Service (Longitudinal Comparison)

This service bridges the gap between a single recording and a health trend.

- **Windowed Aggregation:** For the demo, aggregate metrics across **seconds and minutes** to show immediate shifts (e.g., during a stress task).
- **Personal Baseline:** Store a rolling mean of the user's "normal" metrics. The aggregator should output the **percentage deviation** from this baseline (e.g., "15% increase in pause duration detected").

### Step 4: Localhost Dashboard

A real-time interface to visualize the "window into the mind".

- **Real-Time Tracking:** Use line graphs to show $F_0$ and Pause Duration shifting over the current conversation.
- **Conversation Log:** Display the Whisper transcript alongside a link to the `.wav` file.
- **Visual Attribution:** Show the user/caregiver how the conversation is analyzed using simple flags like "Poverty of Speech Detected" or "High Vocal Instability".

## 4. Privacy-by-Design Guardrail

To comply with HIPAA/PIPEDA, the Metrics Service must follow the **"Extract and Delete"** principle:

- Process the `.wav` file to extract numerical features and the transcript.
- **Immediately delete the raw audio file**.
- Store only the derived JSON feature vectors for the Aggregator and Dashboard.

---

## Claude Instruction Prompt:

> "Please help me implement two Python services and a basic dashboard.
>
> 1. **Metrics Service:** Use `watchdog` to poll a folder for `.wav` files. On discovery, use `openSMILE` (eGeMAPS), `Parselmouth`, and `Whisper` to extract Jitter, Shimmer, $F_0$ mean, Speech Rate, and TTR.
> 2. **Aggregator:** A script that reads the JSON outputs from the Metrics Service and calculates a rolling average for each feature over the last 5 minutes.
> 3. **Dashboard:** A simple Flask or Streamlit app that displays a live line chart of these metrics and a text log of the most recent transcriptions.
>
> Ensure the Metrics Service deletes the `.wav` file immediately after analysis to satisfy privacy requirements. Tag all data with timestamps for real-time tracking."
