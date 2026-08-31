#!/usr/bin/env python3
"""Render narration/*.txt to audio/*.mp3.

ElevenLabs when ELEVENLABS_API_KEY is set and the key carries text_to_speech;
otherwise macOS `say`, so a complete cut always exists.
"""
import os, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).parent
SRC, OUT = HERE / "narration", HERE / "audio"
VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")  # Brian
MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")


def elevenlabs(text: str, dest: Path, key: str) -> None:
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
        data=('{"text": %s, "model_id": "%s", "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "speed": 1.0}}'
              % (__import__("json").dumps(text), MODEL)).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def say(text: str, dest: Path) -> None:
    aiff = dest.with_suffix(".aiff")
    subprocess.run(["say", "-v", "Samantha", "-r", "168", "-o", str(aiff), text], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(aiff),
                    "-codec:a", "libmp3lame", "-b:a", "128k", "-y", str(dest)], check=True)
    aiff.unlink()


def main() -> int:
    OUT.mkdir(exist_ok=True)
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    engine = "elevenlabs" if key else "say"
    for txt in sorted(SRC.glob("*.txt")):
        dest = OUT / (txt.stem + ".mp3")
        text = txt.read_text().strip()
        if engine == "elevenlabs":
            try:
                elevenlabs(text, dest, key)
            except urllib.error.HTTPError as e:
                print(f"elevenlabs refused ({e.code}): {e.read()[:200].decode(errors='replace')}", file=sys.stderr)
                print("falling back to macOS say for every segment", file=sys.stderr)
                engine = "say"
        if engine == "say":
            say(text, dest)
        print(f"{engine:11s} {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
