# Media reproduction

This folder preserves the 160-second demo renderer, local natural-voice generator,
subtitles and verification script. The actual source interaction frames, WAV clips,
provider response and production manifest live in the private Drive production
bundle linked from docs/DEMO_MEDIA_20261028.md. The Git repository intentionally
contains no model weights or installed packages.

For the observed Windows build, install requirements.txt in a separate local
Python environment. Put the publicly identified Kokoro weights under models/
next to synthesize_narration.py, and extract the production bundle at that same
root with its recording/, audio/, docs/ and evidence/ layout. Follow the bundle's
PRODUCTION_README.txt. No API key or paid service is required.

The zero-key judge application itself needs only Python's standard library;
media tooling is a separate optional authoring workflow. Do not install media
dependencies merely to run python -m labrepair.serve.

