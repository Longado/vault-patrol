#!/usr/bin/env python3
"""Cut clips/ + audio/ into demo.mp4.

Each segment is fitted to its own narration: TRIM takes a window, SPEED time-scales
the whole clip, PAD freezes the last frame. Durations are recomputed from the real
audio every run, so re-rendering the voiceover re-syncs the cut without hand edits.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
CLIPS, AUDIO, WORK = HERE / "clips", HERE / "audio", HERE / "work"
OUT = HERE / "demo.mp4"
LEAD = 0.4   # silence before narration starts inside a segment
TAIL = 2.0   # picture held after narration ends

# segment -> (clip, fit mode, start offset for TRIM / max speed-up for SPEED)
PLAN = [
    ("01_s1",  "s1.mp4",  "SPEED", 1.6),
    ("02_s2",  "s2.mp4",  "TRIM",  0.0),
    ("03_s3",  "s3.mp4",  "TRIM",  1.5),
    ("04_s4a", "s4a.mp4", "SPEED", 2.2),
    ("05_s4b", "s4b.mp4", "TRIM",  2.0),
    ("06_s4c", "s4c.mp4", "TRIM",  0.0),
    ("07_s5a", "s5a.mp4", "PAD",   0.0),
    ("08_s5b", "s5b.mp4", "TRIM",  5.0),
]


def dur(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(p)], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", *args], check=True)


def main() -> int:
    WORK.mkdir(exist_ok=True)
    parts, total = [], 0.0
    for name, clip_name, mode, param in PLAN:
        clip, voice = CLIPS / clip_name, AUDIO / f"{name}.mp3"
        for f in (clip, voice):
            if not f.exists():
                print(f"missing {f}", file=sys.stderr); return 1
        target = LEAD + dur(voice) + TAIL
        cd = dur(clip)

        if mode == "SPEED":
            factor = min(max(cd / target, 1.0), param)
            vf = f"setpts=PTS/{factor:.4f}"
            src = ["-i", str(clip)]
        elif mode == "TRIM":
            start = min(param, max(cd - target, 0.0))
            vf = "setpts=PTS-STARTPTS"
            src = ["-ss", f"{start:.2f}", "-i", str(clip)]
        else:  # PAD — freeze the final frame out to target
            vf = f"tpad=stop_mode=clone:stop_duration={max(target - cd, 0) + 1:.2f}"
            src = ["-i", str(clip)]

        seg = WORK / f"{name}.mp4"
        run([*src, "-i", str(voice),
             "-filter_complex",
             f"[0:v]{vf},fps=30,trim=0:{target:.3f},setpts=PTS-STARTPTS[v];"
             f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad,atrim=0:{target:.3f},asetpts=PTS-STARTPTS[a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", "-y", str(seg)])
        parts.append(seg); total += target
        print(f"{name:8s} clip {cd:5.1f}s  voice {dur(voice):5.1f}s  ->  {target:5.1f}s  [{mode}]")

    listing = WORK / "concat.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    run(["-f", "concat", "-safe", "0", "-i", str(listing),
         "-vf", f"fade=t=in:st=0:d=0.6,fade=t=out:st={total-1.2:.2f}:d=1.0",
         "-af", f"afade=t=in:st=0:d=0.6,afade=t=out:st={total-1.2:.2f}:d=1.0",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-y", str(OUT)])
    print(f"\n{OUT}  {dur(OUT):.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
