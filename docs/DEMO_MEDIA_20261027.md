# Narrated demo production — 27 October 2026

A first edited English demo has been rendered locally: **155 seconds**,
**1920 × 1080**, **25 fps**, H.264 video and AAC audio. It introduces a quantum
research software engineer, the channel-mapping pain point, and a seven-word
hook: **Two patches. Same total. One is wrong.**

The narration is the generic `af_heart` neural voice from Kokoro 82M v1.0,
executed locally through `kokoro-onnx`. It is not Windows system speech and does
not clone a person. No paid TTS service or new research inference was used.

## Files and observed validation

- Video: `LabRepair_DEMO_NeuralVoice_20261027.mp4`, **4,892,064 bytes**.
- SHA-256: `0fa62eb797aae010d4b250ac3c628104c1fb1b57cbf09003f7aeceb4a28cd1ae`.
- Independent English subtitles: `LabRepair_DEMO_20261027.en.srt`.
- Natural narration stem: `LabRepair_natural_narration_20261027.wav`.
- Narration and durations: [machine-readable source](demo_narration_20261027.json).
- Nine decoded frames were inspected at 5, 12, 25, 49, 75, 100, 118, 134 and
  150 seconds. They show the role, comparison, pair checks, proposal, real run,
  separate verdicts, hold decision, evidence handover and closing frame.
- The decoded stream reports 155.0 seconds, 1920 × 1080, 25 fps and AAC audio.
- Measured integrated audio loudness: **−16.51 LUFS**; true peak: **−1.38 dBTP**.
  These are measurements of the rendered file, not a claim of subjective voice
  quality or a customer listening study.
- All narration clips fit their allocated scenes. Subtitle timing is derived
  from the generated clip duration; it is not a forced-alignment transcript.

## Content and runtime boundaries

The video combines actual browser captures with clearly marked editorial cards.
It is an edited walkthrough, not a continuous screen recording. The browser
interactions exercised the incorrect and correct local reviews, recorded a hold
intent, and opened the saved actual execution record. No candidate program or
provider job was executed by recording these interactions.

The model repair's four passing checks and the two expected failing controls are
from the previously archived real NVIDIA/Nebius integration. The wrong control
is operator-authored. Inputs are synthetic and the original 3.40 claim remains
NOT_REPRODUCED after the correct 2.60 repair. This does not demonstrate quantum
advantage, physical quantum measurements, a production autonomous agent or
general repair accuracy.

## Reproducibility and publication

The media production bundle preserves the script, exact scene timings, source
captures, renderer, neural narration, subtitles, media verification and model
file hashes. Model weights and installed packages are not copied into the
bundle. The model is [Apache-licensed](https://huggingface.co/hexgrad/Kokoro-82M);
the [ONNX wrapper](https://github.com/thewh1teagle/kokoro-onnx) is MIT-licensed.

The underlying quantum workflow motivation is discussed in
[1-2-3 Reproducibility for Quantum Software Experiments](https://arxiv.org/abs/2201.12031)
and [Qiskit Experiments](https://joss.theoj.org/papers/10.21105/joss.05329).
These publications do not independently validate LabRepair.

The repository remains private and the existing PR remains a draft. A private
Drive upload is a delivery copy, not a public video release or a competition
submission. Drive IDs and exact readback verification are recorded in the media
delivery receipt after upload.

## Verified private delivery

The [video](https://drive.google.com/file/d/1_UvPULtKAIgH-M8qE2iJMkBUwg-yAZuv/view), [English subtitles](https://drive.google.com/file/d/1CRTdqK5BlyFsOVylKbHZtyEUT1HVUQ7J/view), [narration stem](https://drive.google.com/file/d/1CQeHn9L4FGX_ln9qnsvzXMnCAVOSqQKM/view) and [production bundle](https://drive.google.com/file/d/1C1KV0FbbPesXvjB_sep-4MzBLWoDlwRf/view) were uploaded to the existing Nebius Coding folder. All four original files were downloaded again and matched their local SHA-256 hashes. All 37 files inside the production bundle matched its manifest.

The movie sharing UI says only the owner can access it. No sharing setting changed. Drive player controls and the 2:35 duration were observed, but picture decoding in its preview was not established. The exact downloaded original is verified separately and decoded locally. See the [delivery receipt](../evidence/demo_video_20261027.json).
