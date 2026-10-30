# Current-UI demo production — 28 October 2026

This updated **160-second English demo** records the judge workbench introduced
at UI commit `4c1cc58bf244db9b3a63704a12c62068136bbd72`. It preserves the earlier
155-second movie as a separate historical delivery.

## What changed

- Actual browser interaction frames show sample selection, the valid local
  repair, the same-total wrong repair, REVIEW for incomplete evidence, a
  source-bound hold, and the downloaded evidence receipt.
- The narration explicitly names **Nebius Token Factory** and **NVIDIA Nemotron**.
  It explains that the prompt supplied the declared A1 convention; the model
  translated it into typed parameters and did not discover an unknown correction.
- The cloud section stays labeled as saved real execution from 26 October 2026 UTC:
  the earlier Token Factory generation and separate disposable Sandbox operation.
  Current local UI playback makes no new model or Sandbox request.
- Generic Kokoro `af_heart` neural narration runs locally. It is not Windows
  system speech, a human recording or a cloned voice. No paid TTS API is used.

## Recording and edit boundaries

The source session contains **514 timestamped browser screenshot frames**,
**54 distinct frame hashes** and **16 recorded actions**. These are frames from
actual operations, not redrawn interface mockups. The film edits their timing,
uses explanatory holds and crops, and interleaves labeled editorial cards.
It is not a continuous real-time desktop recording or a performance benchmark.
The raw provenance retains a roughly 953-second receipt-download action delay;
that wait is omitted from the explanatory cut. The downloaded receipt was
verified independently for its checksum, intent binding and unchanged claim.

Local samples A/B/C are curated synthetic review paths. The earlier real cloud
operation instead executed baseline/model-repair/wrong-pair variants. The local
incomplete-evidence case was not a fourth cloud execution. Twelve recorded cloud
checks include three expected control failures. A model repair passing four
checks does not reproduce the original 3.40 claim or establish a physical quantum
experiment, quantum advantage or broad repair accuracy.

## Sources and reproduction

- [Narration and exact timing](demo_narration_20261028.json)
- [Walkthrough](DEMO_WALKTHROUGH_20261028.md)
- Production source: `media/demo-20261028/`.
- Existing zero-key judge UI: `python -m labrepair.serve --port 8770`.

The production bundle contains the renderer, subtitles, neural narration clips,
source interaction frames/session, downloaded local receipt, verification and
file manifest. Model weights and installed packages are excluded. Rebuilding
requires the documented media packages and the already identified public
Kokoro weights; it never needs provider credentials. Windows fonts/FFmpeg were
used for the observed build. Media reproduction is separate from the standard-
library-only judge application.

## Private delivery

The repository stays private, and draft PR #1 stays unmerged. This Drive
delivery is private preparation, not public YouTube publication or Devpost
submission. Upload metadata, actual movie playback and the readback boundaries
are recorded below.


## Observed output and Drive readback

- Movie: **160.0 seconds**, **1920 × 1080**, **25 fps**, H.264/AAC;
  **6,332,363 bytes**, SHA-256
  `edcaa6b08ae9a348f9687c8e976e0a093ad6d056263c8ee732d22a24396cb497`.
- Local full-stream decode passed. Nine exported frames at 5, 12, 29, 55, 80, 105,
  123, 139 and 154 seconds were visually inspected. All 41 subtitle intervals are
  ordered and within the film; all 9 voice clips fit their allotted scenes.
- Measured integrated audio: **−16.50 LUFS**, true peak **−1.32 dBTP**.
- Production ZIP: **48,218,915 bytes**; all **543 entry hashes** match its manifest.
  Model weights, installed packages and credentials are excluded.
- The browser confirmed four uploads in the existing Nebius Coding folder.
  Drive played the new movie's picture and showed **2:40**. Its sharing control
  showed **owner only**. Archive contents were readable. SRT preview was
  unavailable; its actual local text and GitHub copy were independently checked.
- Original remote bytes were not downloaded for this revision. Therefore cloud-
  original SHA-256 matching is **not claimed**; the hashes above describe the
  locally decoded files. Upload metadata and actual movie playback were observed.

Private delivery: [video](https://drive.google.com/file/d/1dwH4B47FB7vdiuvMoF87zMZdShxkHzWR/view),
[English subtitles](https://drive.google.com/file/d/1X1MxSK0u3-Ji0kZJwiphHIWJjkSK0-M7/view),
[narration stem](https://drive.google.com/file/d/1NmwnK8zneHh5UnGwywePX4LgdROh-xGA/view),
[production bundle](https://drive.google.com/file/d/100rsp6TCc0u56j5mYORF3S_kDM15ULrD/view).
See the [delivery receipt](../evidence/demo_video_20261028.json) for file identities,
UI/media source commits, boundaries and pending public-submission gates.

The [Drive delivery receipt](https://drive.google.com/file/d/1vDH7O6IaWeywFbfvZI2R1VJ-JAWaj5dv/view) was read back as JSON and its parsed content exactly matched the local receipt. This semantic check is separate from raw-original byte-hash verification. See the [cloud readback record](../evidence/demo_video_drive_readback_20261028.json).
