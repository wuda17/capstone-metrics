/**
 * Peer-reviewed citations for every vocal biomarker and clinical alert pattern.
 * All text is verbatim from references.md.
 */

export const METRIC_REFS = {
  speech_rate_wpm: {
    description: "The total number of words spoken per minute, including pauses and silences.",
    claim: "A slower speech rate is a consistent biomarker for psychomotor retardation in depression and negative symptoms of schizophrenia. It is also commonly observed in patients with Alzheimer's Disease and Mild Cognitive Impairment.",
    citation: "Larsen et al. (2024)",
    doi: "https://doi.org/10.3389/fpsyt.2024.1342835",
  },
  phonation_to_time_ratio: {
    description: "The proportion of total time spent in voiced speech versus silence.",
    claim: "Reductions in the phonation-to-time ratio can identify frequent voice breaks or alogia (poverty of speech). Significant differences in phonation time are documented in patients with cognitive decline.",
    citation: "Huang et al. (2024)",
    doi: "https://doi.org/10.3389/fpubh.2024.1417966",
  },
  mean_pause_duration_sec: {
    description: "The average length of silent intervals, typically gaps exceeding 0.5 seconds.",
    claim: "Increased pause frequency and duration are primary indicators of word-retrieval difficulty and increased cognitive load in Alzheimer's and depression. Switching pauses correlate significantly with depressive symptom severity.",
    citation: "Larsen et al. (2024)",
    doi: "https://doi.org/10.3389/fpsyt.2024.1342835",
  },
  type_token_ratio: {
    description: "The ratio of unique words used to the total number of words spoken.",
    claim: "A decline in the Type-Token Ratio serves as a critical longitudinal marker for semantic memory deterioration and early-stage cognitive decline. It reflects reduced cognitive reserve and vocabulary richness.",
    citation: "Shankar et al. (2025)",
    doi: "https://doi.org/10.1038/s41746-025-02105-z",
  },
  emotion_score: {
    description: "A composite measure of emotional valence (pleasantness) and activation (energy levels).",
    claim: "Multitask deep learning models can estimate valence and activation from speech to accurately track mood symptom severity in Bipolar Disorder. Mood oscillations are consistently linked to rate of speech and intonation.",
    citation: "Mower Provost et al. (2024)",
    doi: "https://doi.org/10.1109/taffc.2024.3407683",
  },
  jitter_local: {
    description: "The cycle-to-cycle variation in the frequency (pitch) of the voice.",
    claim: "Elevated jitter values indicate reduced precision in laryngeal control and are highly sensitive markers for neuromotor coordination deficits in psychiatric populations. It is predictive of future cognitive decline.",
    citation: "Larsen et al. (2024)",
    doi: "https://doi.org/10.3389/fpsyt.2024.1342835",
  },
  articulation_rate_wpm: {
    description: "Speaking speed calculated by excluding silent pauses from the total duration.",
    claim: "Articulation rate provides a measure of pure motor and cognitive processing speed. Reductions in this rate are hallmark indicators of alogia and motor slowing in neurodegeneration.",
    citation: "Huang et al. (2024)",
    doi: "https://doi.org/10.3389/fpubh.2024.1417966",
  },
  f0_mean_hz: {
    description: "The average fundamental frequency of vocal fold vibration.",
    claim: "Elevations in mean F₀ are robust indicators of acute psychological stress and autonomic arousal. Conversely, reduced pitch variability (monotony) is a classic biomarker for depression and schizophrenia.",
    citation: "Veiga et al. (2025)",
    doi: "https://doi.org/10.1002/smi.70112",
  },
  shimmer_local_db: {
    description: "The cycle-to-cycle variation in the amplitude (intensity) of the voice.",
    claim: "Increased shimmer values are associated with vocal instability and tremors, which are common manifestations of aging and neurodegenerative decline. Shimmer is highly sensitive to cycle-to-cycle amplitude perturbation.",
    citation: "Larsen et al. (2024)",
    doi: "https://doi.org/10.3389/fpsyt.2024.1342835",
  },
  self_pronoun_ratio: {
    description: "The frequency of first-person singular pronouns (e.g. \"I\", \"me\", \"my\") used in speech.",
    claim: "Increased use of first-person singular pronouns is a robust, validated biomarker for depression, reflecting inward-focused self-referential rumination. It relates to the social engagement and disengagement model of depressive states.",
    citation: "Amorese et al. (2025)",
    doi: "https://doi.org/10.3389/fpsyg.2025.1514918",
  },
}

export const ALERT_REFS = [
  {
    name: "Poverty of Speech (Alogia)",
    description: "A significant reduction in total word count and spontaneous speech production.",
    claim: "Patients with psychotic and major depressive disorders exhibit significantly lower total talking time and higher mean pause durations. This reflects a disruption in the mental system underlying language.",
    citation: "Low et al. (2020)",
    doi: "https://doi.org/10.1002/lio2.354",
  },
  {
    name: "Affective Flattening",
    description: "A \"flat\" or monotonous voice with reduced pitch and loudness variability.",
    claim: "A reduction in fundamental frequency variability and intensity modulation is a robust indicator of negative symptoms in schizophrenia and chronic depression. It manifests as melodically flatter speech.",
    citation: "Low et al. (2020)",
    doi: "https://doi.org/10.1002/lio2.354",
  },
  {
    name: "Apathy Signature",
    description: "A specific vocal profile characterised by reduced spectral range and articulatory precision.",
    claim: "The vocal features contributing most to the classification of late-life depression are more strongly associated with apathy than with dysphoric mood or cognitive impairment. It relates to unique voice characteristics reflecting blunted vocal affect.",
    citation: "Harlev et al. (2025)",
    doi: "https://doi.org/10.1002/dad2.70055",
  },
  {
    name: "Stress Response Peak",
    description: "Detection of vocal features correlating with a surge in the stress hormone cortisol.",
    claim: "Speech acoustic features can robustly predict peak salivary cortisol levels approximately 10–20 minutes following a stressor. Peak correlation typically occurs between 10 and 20 minutes after initial stress stimulus.",
    citation: "Baird et al. (2021)",
    doi: "https://doi.org/10.3389/fcomp.2021.750284",
  },
  {
    name: "Suicide Risk Marker",
    description: "Vocal and spectral patterns indicating high risk, including lower energy variability.",
    claim: "Individuals with suicidal ideation exhibit flatter energy contours and lower energy variability in voiced segments. These markers often accompany reduced lexical diversity and simplified syntactic structures.",
    citation: "Jordan et al. (2025)",
    doi: "https://doi.org/10.2196/74260",
  },
  {
    name: "Longitudinal Deviation",
    description: "A percentage deviation from the user's established personal baseline over time.",
    claim: "Monitoring individual deviations from a \"Personal Mean\" (e.g. a 15% increase in pauses) is more predictive of mood shifts than comparison to population norms. This identifies decline trajectories rather than static differences.",
    citation: "Mower Provost et al. (2024)",
    doi: "https://doi.org/10.1109/taffc.2024.3407683",
  },
]
