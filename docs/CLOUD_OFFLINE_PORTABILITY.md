# Cloud offline portability verification

Upstream source: private `mangroveuniversemu-bot/nebius-labrepair`, commit
`3493af0667b91cb8386c81a0d32e523ce7d45102`, tree
`944665bd8d4decc5188dfe927a384dbe397290bb`.

The first Linux/Python 3.12 cloud run failed: 73 tests executed, five errors.
The handover test class did not execute its eight tests because setup failed.
Git stores the historical JSON files with LF newlines, while their frozen
historical SHA-256 pins identify the Windows CRLF representation. The standalone
exchange verifier also required an absent historical NEBIUS-010 receipt.

## Narrow repair

- Preserve all historical pins and committed fixture files unchanged.
- Accept original bytes, or reconstruct CRLF from exclusively LF bytes only
  when the result exactly matches the existing historical SHA-256 pin.
- Reject changed content, whitespace, missing terminal newline and mixed
  newline changes. No JSON canonicalization grants origin authenticity.
- Record the actual downloadable-byte digest separately from the historical
  CRLF digest. Hash matches are integrity evidence, not authenticated identity.
- A missing old NEBIUS-010 receipt is explicitly absent; it is not recreated,
  validated or included in current test claims. If present, preserve its hash.
- Use a fresh UTC/UUID run identity and separate output directory. Keep old
  receipts untouched. Record the actual Python command without Windows paths.

## Current verification boundary

The reviewed fixed test suite and synthetic HTTP fixtures run on the dot cloud
workspace. No arbitrary candidate patch is applied or executed. The Q4 adapter
regression uses a fake client. Ordinary subprocess calls are not an isolation
claim. NVIDIA model, Nebius runtime, real HTTP transport, spending permissions
and monetary enforcement remain NOT_RUN or UNVERIFIED. Provider usage, latency
and cost remain unknown. Newlines do not change those gates.

Run with Python 3.12 and `requirements.txt`:

    python -m unittest discover -s tests -v
    python scripts/verify_offline_exchange.py

The cloud environment provisioning receipt records installed packages separately
from the verifier. Repeated full-suite runs are not summed as distinct tests.
