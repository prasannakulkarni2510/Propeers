"""Voice each scene sentence by sentence, then join with short gaps
(edge voices otherwise pause ~1s after every sentence)."""
import asyncio
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).parent))
from script import SCENES  # noqa: E402

import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
VOICE = sys.argv[2] if len(sys.argv) > 2 else "en-IN-NeerjaNeural"
GAP = 0.3
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB,areverse")


def ff(*args):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


async def main():
    for i, (_, _, text) in enumerate(SCENES):
        parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]
        wavs = []
        for k, sent in enumerate(parts):
            mp3 = OUT / f"{i:02d}_{k}.mp3"
            await edge_tts.Communicate(sent, VOICE, rate="-4%").save(str(mp3))
            wav = OUT / f"{i:02d}_{k}.wav"
            pad = f",apad=pad_dur={GAP}" if k < len(parts) - 1 else ""
            ff("-i", str(mp3), "-af", TRIM + pad, "-ar", "48000", "-ac", "2", str(wav))
            wavs.append(wav)
        lst = OUT / f"{i:02d}.txt"
        lst.write_text("".join(f"file '{w.as_posix()}'\n" for w in wavs))
        ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "2",
           str(OUT / f"{i:02d}.mp3"))
        print("voiced", i, len(parts), "sentences", flush=True)

asyncio.run(main())
