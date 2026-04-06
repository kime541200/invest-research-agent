## ADDED Requirements

### Requirement: Fallback to audio transcription when native subtitles are unavailable
The system SHALL attempt an audio-to-text fallback workflow when a YouTube video does not provide usable native subtitles for the collection flow.

#### Scenario: Native subtitles are disabled
- **WHEN** the transcript fetch step returns `status=unavailable` with a reason indicating native subtitles are disabled
- **THEN** the system MUST attempt to download the video's audio and submit it to the configured STT provider

#### Scenario: Fallback result is reusable by the note pipeline
- **WHEN** the STT provider returns a successful transcription response
- **THEN** the system MUST normalize the transcription into the existing `TranscriptBundle` shape before note generation continues

### Requirement: Audio download shall support repeatable collection runs
The system SHALL download audio in a way that can be reused across reruns without requiring an interactive workflow.

#### Scenario: Collection run reaches a subtitle fallback path
- **WHEN** the fallback path is triggered for a specific video
- **THEN** the system MUST use a non-interactive download method suitable for automated pipeline execution

#### Scenario: Audio artifacts can be reused
- **WHEN** the same video is processed again and a reusable audio artifact already exists
- **THEN** the system MUST allow the fallback flow to reuse cached artifacts instead of forcing a fresh download every time

### Requirement: Failed audio transcription fallback shall degrade gracefully
The system SHALL preserve the collection flow even if the audio transcription fallback cannot complete.

#### Scenario: STT provider is unavailable during fallback
- **WHEN** the system cannot reach the configured STT provider or the provider returns an error
- **THEN** the collection flow MUST record a clear failure reason and continue using the existing degraded note path instead of crashing the whole run

#### Scenario: Audio download fails
- **WHEN** the system cannot obtain an audio artifact for a target video
- **THEN** the collection flow MUST surface the failure context in a machine-readable way for later debugging and operator follow-up
