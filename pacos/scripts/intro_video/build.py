"""Assemble scenes/NN.png + voice/NN.mp3 into the intro mp4."""
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
S = Path(sys.argv[1]); OUT = Path(sys.argv[2])
scenes = sorted((S / "scenes").glob("*.png"))
work = S / "work"; work.mkdir(exist_ok=True)
FPS, XF, LEAD, TAIL = 30, 0.6, 0.35, 0.9


def run(args):
    r = subprocess.run([FF, "-hide_banner", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-2000:])
    return r.stderr


durs = []
for i, png in enumerate(scenes):
    mp3 = S / "voice" / f"{i:02d}.mp3"
    wav = work / f"{i:02d}.wav"
    # trim leading/trailing silence, then lead-in + tail of room tone
    run(["-i", str(mp3), "-af",
         "silenceremove=start_periods=1:start_threshold=-50dB:"
         "stop_periods=-1:stop_duration=0.4:stop_threshold=-40dB:stop_silence=0.35,"
         "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
         f"adelay={int(LEAD*1000)}:all=1,apad=pad_dur={TAIL}",
         "-ar", "48000", "-ac", "2", str(wav)])
    info = run(["-i", str(wav), "-f", "null", "-"])
    t = re.findall(r"time=(\d+):(\d+):([\d.]+)", info)[-1]
    d = int(t[0]) * 3600 + int(t[1]) * 60 + float(t[2])
    if i < len(scenes) - 1:
        d += XF  # the crossfade eats XF of each clip
    durs.append(d)
    frames = int(round(d * FPS))
    run(["-loop", "1", "-i", str(png), "-vf",
         f"scale=3840:-1,zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
         f":d={frames}:s=1920x1080:fps={FPS},format=yuv420p",
         "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         str(work / f"{i:02d}.mp4")])
    # pad audio to clip length so crossfades line up
    run(["-i", str(wav), "-af", f"apad=whole_dur={d}", "-t", f"{d}", str(work / f"{i:02d}p.wav")])
    print(f"scene {i}: {d:.2f}s", flush=True)

ins, fv, fa = [], [], []
for i in range(len(scenes)):
    ins += ["-i", str(work / f"{i:02d}.mp4")]
for i in range(len(scenes)):
    ins += ["-i", str(work / f"{i:02d}p.wav")]
n = len(scenes)
off, vprev, aprev = 0.0, "[0:v]", f"[{n}:a]"
for i in range(1, n):
    off += durs[i - 1] - XF
    fv.append(f"{vprev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]")
    fa.append(f"{aprev}[{n+i}:a]acrossfade=d={XF}:c1=tri:c2=tri[a{i}]")
    vprev, aprev = f"[v{i}]", f"[a{i}]"
fa.append(f"{aprev}loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
run([*ins, "-filter_complex", ";".join(fv + fa), "-map", vprev, "-map", "[aout]",
     "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p", "-r", str(FPS),
     "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(OUT)])
print("built", OUT, f"{sum(durs) - XF*(n-1):.1f}s")
