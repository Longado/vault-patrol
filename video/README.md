# Demo video build

Everything here is the *recipe*; the footage and the render are gitignored.

```
narration/*.txt   one file per shot, in order — the script the voice reads
scenes/*.sh       terminal shots, each one drives itself with explicit sleeps
slides/*.html     browser shots designed for a 1400x788 window (16:9 after crop)
record.sh         <out.mp4> <seconds> — screen capture, cropped to that window
raise.sh          keeps the recorded app frontmost for the length of a take
tts.py            narration/*.txt -> audio/*.mp3 (ElevenLabs, else macOS `say`)
assemble.py       clips/ + audio/ -> demo.mp4, each shot fitted to its own narration
```

Re-render the voiceover and the cut re-syncs itself — `assemble.py` reads the real
audio durations every run, so no timing is hand-written anywhere.

```sh
ELEVENLABS_API_KEY=... python3 tts.py && python3 assemble.py
```

The Cloud Run and GitHub shots are live: the push in `scenes/s4a.sh` plants a real
contradiction in the demo vault, and the PR on screen is the one the deployed
service opened in response to it.
