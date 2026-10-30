"""CURRENT public-film end-card derivative renderer, not a full-film generator.

The original 123-second film is an external, hash-pinned input. This program
changes only the 116-123 second picture, copies AAC and the supplied SRT, and
requires explicit FFmpeg/font/output paths. It installs nothing and calls no
TTS, model, website or other network service. See README.md for prerequisites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PAGES_URL = "https://mangroveuniversemu-bot.github.io/nebius-labrepair-submission/"
REPO_URL = "https://github.com/mangroveuniversemu-bot/nebius-labrepair-submission"
SOURCE_SHA256 = "9ab36becebe9b4061e9ecc62e607cff88f0b84bc6c9065079d3df4ced56e531a"
SOURCE_ASS_SHA256 = "3343c953f0e77fc009b90ae6ea6ea885b375427e847ec8287108bb37c9a762ba"
SRT_SHA256 = "bc5628c9bbbf6e83eba6fafe1c9678787419a1f6e1c53deebd9be20f0aa4dae3"
CURRENT_FILM_SHA256 = "df520bcf87b50d80e34805783462f030f18d386a1009ed4c1696609267e3b887"
W, H = 1920, 1080


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def allowed_url(value):
    url = urlparse(value)
    require(url.scheme == "https" and url.netloc == "mangroveuniversemu-bot.github.io"
            and url.path == "/nebius-labrepair-submission/" and not url.params
            and not url.query and not url.fragment, "Only the reviewed public Pages URL is allowed")
    return value


def run(ffmpeg, output_dir, args):
    return subprocess.run([str(ffmpeg), "-hide_banner", *map(str, args)],
                          cwd=output_dir, check=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def audio_hash(ffmpeg, output_dir, movie):
    return run(ffmpeg, output_dir, ["-loglevel", "error", "-i", movie,
               "-map", "0:a:0", "-c:a", "copy", "-f", "hash", "-hash", "sha256", "-"]).stdout.strip()


def inspect_movie(ffmpeg, output_dir, movie, expected_hash=None):
    actual_hash = sha(movie)
    require(expected_hash is None or actual_hash == expected_hash, "Movie hash does not match the current reviewed film")
    decoded = run(ffmpeg, output_dir, ["-i", movie, "-f", "null", "-"])
    duration = re.search(r"Duration: (\d+):(\d+):([\d.]+)", decoded.stderr)
    require(duration is not None, "No duration reported by FFmpeg")
    h, m, s = duration.groups()
    seconds = int(h)*3600 + int(m)*60 + float(s)
    require(abs(seconds-123) < .06, "Unexpected film duration")
    require("1920x1080" in decoded.stderr and "25 fps" in decoded.stderr,
            "Expected 1920x1080 at 25 fps")
    # Logs intentionally omit local paths; the public receipt stores only names.
    qa = output_dir / "qa"
    qa.mkdir(exist_ok=True)
    for second in (116, 118, 122):
        run(ffmpeg, output_dir, ["-v", "error", "-y", "-ss", second, "-i", movie,
                                "-frames:v", "1", qa / f"actual-{second:03d}.jpg"])
    return {"movie": movie.name, "bytes": movie.stat().st_size,
            "sha256": actual_hash, "duration_seconds": seconds,
            "width": 1920, "height": 1080, "fps": 25,
            "full_decode_exit_code": decoded.returncode,
            "aac_payload_hash": audio_hash(ffmpeg, output_dir, movie),
            "sampled_actual_end_frame_seconds": [116, 118, 122]}


def draw_endcard(output_dir, pages_url, fonts):
    # Pillow is required only for rendering. Readback mode needs the standard
    # library plus an explicitly supplied FFmpeg executable.
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), "#0B151A")
    d = ImageDraw.Draw(im)
    for x in range(0, W, 3):
        f = x/W
        d.rectangle((x, 0, x+2, H), fill=(round(11+6*f), round(21+12*f), round(26+12*f)))

    def text(xy, value, size, color="#F1F5F0", bold=False, mono=False):
        face = fonts["mono" if mono else "semibold" if bold else "regular"]
        font = ImageFont.truetype(str(face), size)
        require(d.textlength(value, font=font) <= W-220, "Text exceeds the safe end-card width")
        d.text(xy, value, font=font, fill=color)

    text((110, 68), "LABREPAIR / PUBLIC JUDGE DEMO", 24, "#72D6BD", True, True)
    text((104, 190), "Try the wrong-pair case.", 91, bold=True)
    text((109, 318), "Inspect the evidence. Then decide.", 60, "#72D6BD", True)
    text((113, 473), "OPEN THE INTERACTIVE DEMO", 25, "#9BAFAE", True, True)
    text((110, 522), pages_url.removeprefix("https://"), 46, bold=True, mono=True)
    text((113, 621), "OPEN SOURCE / MIT", 25, "#9BAFAE", True, True)
    text((110, 670), REPO_URL.removeprefix("https://"), 38, bold=True, mono=True)
    text((113, 814), "No login. No key. No model charge to try the demo.", 33, "#72D6BD")
    for y in range(890, H):
        alpha = min(1, (y-890)/95)*.80
        base = im.getpixel((0, y))
        d.line((0, y, W, y), fill=tuple(round(v*(1-alpha)) for v in base))
    target = output_dir / "public-endcard.png"
    im.save(target)
    return target


def render(args, ffmpeg, output_dir):
    for name in ("source_movie", "font_regular", "font_semibold", "font_mono", "verified_at_utc"):
        require(getattr(args, name) is not None, "Rendering requires --" + name.replace("_", "-"))
    source = args.source_movie.resolve(strict=True)
    source_ass = args.source_ass.resolve(strict=True)
    source_srt = args.source_srt.resolve(strict=True)
    require(sha(source) == SOURCE_SHA256, "Predecessor movie hash mismatch")
    require(sha(source_ass) == SOURCE_ASS_SHA256, "Predecessor ASS hash mismatch")
    require(sha(source_srt) == SRT_SHA256, "Source subtitle hash mismatch")
    pages_url = allowed_url(args.pages_url)
    stamp = datetime.fromisoformat(args.verified_at_utc.replace("Z", "+00:00"))
    require(stamp.tzinfo is not None, "Verification timestamp must include a timezone")
    fonts = {"regular": args.font_regular.resolve(strict=True),
             "semibold": args.font_semibold.resolve(strict=True),
             "mono": args.font_mono.resolve(strict=True)}
    final = output_dir / "LabRepair_DEMO_Public_20261030.mp4"
    require(final != source and not final.exists(), "Refusing to overwrite a source or existing output movie")
    temp = output_dir / "temp"
    temp.mkdir(exist_ok=True)
    font_dir = temp / "fonts"
    font_dir.mkdir(exist_ok=True)
    for name, path in fonts.items():
        shutil.copyfile(path, font_dir / (name + path.suffix))
    card = draw_endcard(output_dir, pages_url, fonts)
    header = source_ass.read_text(encoding="utf-8").split("Dialogue:", 1)[0]
    events = ("Dialogue: 0,0:00:00.18,0:00:01.87,Default,,0,0,0,,Try the wrong-pair case.\n"
              "Dialogue: 0,0:00:01.87,0:00:05.24,Default,,0,0,0,,Leave a decision the next reviewer can inspect.\n")
    (temp / "endcard.ass").write_text(header + events, encoding="utf-8")
    card_clip = temp / "public-endcard.mp4"
    run(ffmpeg, output_dir, ["-loglevel", "error", "-y", "-loop", "1", "-i", card,
        "-vf", "fps=25,subtitles=temp/endcard.ass:fontsdir=temp/fonts", "-c:v", "libx264", "-threads", "4",
        "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-t", "7", "-an", card_clip])
    run(ffmpeg, output_dir, ["-loglevel", "error", "-y", "-i", source, "-i", card_clip,
        "-filter_complex", "[1:v]setpts=PTS+116/TB[end];[0:v][end]overlay=0:0:eof_action=pass:enable='gte(t,116)'[out]",
        "-map", "[out]", "-map", "0:a:0", "-c:v", "libx264", "-threads", "4", "-preset", "veryfast",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-t", "123", "-movflags", "+faststart", final])
    target_srt = output_dir / "LabRepair_DEMO_Public_20261030.en.srt"
    if target_srt.resolve() != source_srt:
        shutil.copyfile(source_srt, target_srt)
    receipt = inspect_movie(ffmpeg, output_dir, final)
    require(receipt["aac_payload_hash"] == audio_hash(ffmpeg, output_dir, source), "Original AAC payload changed")
    receipt.update({"source_movie_sha256": SOURCE_SHA256,
                    "source_ass_sha256": SOURCE_ASS_SHA256,
                    "subtitle_sha256": sha(target_srt), "subtitles_unchanged": True,
                    "aac_payload_bit_identical": True, "editorial_change_seconds": [116, 123],
                    "picture_encoding": "One additional H.264 encode; earlier picture content retained",
                    "public_pages_url": pages_url, "repository_url": REPO_URL,
                    "pages_verified_at_utc_from_operator": args.verified_at_utc,
                    "font_inputs": {k: {"name": p.name, "sha256": sha(p)} for k, p in fonts.items()},
                    "rebuild_byte_identity": "Not guaranteed across FFmpeg/font versions",
                    "new_provider_or_tts_calls": 0, "publication": "PREPARED_NOT_UPLOADED"})
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", required=True, type=Path, help="Existing executable; no installer is run")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify-existing", type=Path, help="Decode/hash current reviewed film without rendering")
    parser.add_argument("--source-movie", type=Path)
    parser.add_argument("--source-ass", type=Path, default=HERE / "predecessor-captions.ass")
    parser.add_argument("--source-srt", type=Path, default=HERE / "LabRepair_DEMO_Public_20261030.en.srt")
    parser.add_argument("--font-regular", type=Path)
    parser.add_argument("--font-semibold", type=Path)
    parser.add_argument("--font-mono", type=Path)
    parser.add_argument("--pages-url", default=PAGES_URL, type=allowed_url)
    parser.add_argument("--verified-at-utc")
    args = parser.parse_args()
    ffmpeg = args.ffmpeg.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.verify_existing:
        receipt = inspect_movie(ffmpeg, output_dir, args.verify_existing.resolve(strict=True), CURRENT_FILM_SHA256)
        subtitle = args.source_srt.resolve(strict=True)
        require(sha(subtitle) == SRT_SHA256, "Current subtitle hash mismatch")
        intervals = re.findall(r"\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+", subtitle.read_text(encoding="utf-8"))
        require(len(intervals) == 35, "Expected 35 subtitle intervals")
        receipt.update({"subtitle_sha256": sha(subtitle), "subtitle_intervals": len(intervals)})
        name = "current_movie_readback.json"
    else:
        receipt = render(args, ffmpeg, output_dir)
        name = "render_readback.json"
    receipt.update({"schema": "LABREPAIR_PUBLIC_ENDCARD_PORTABLE_READBACK_V1",
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                    "new_provider_or_tts_calls": 0, "new_paid_resources": False})
    (output_dir / name).write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
