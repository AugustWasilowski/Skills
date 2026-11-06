"""Verify the two outputs: stream layout, bottom-strip subtitle frames, and a zh back-transcription.

usage: python verify.py <cues.json> <workdir> <sub.mp4> <dub.mp4> [--times 5,40] [--no-asr]

writes <workdir>/verify/*.png (cropped bottom third) -> Read them to eyeball the subtitles.
Back-transcribes the dub's default audio (Whisper zh) per group and prints it next to the
intended TTS text so mismatches/garbled lines stand out.
"""
import argparse
import json
import os
import subprocess

from common import groups_of, load_cues, run

ap = argparse.ArgumentParser()
ap.add_argument("cues")
ap.add_argument("workdir")
ap.add_argument("sub_mp4")
ap.add_argument("dub_mp4")
ap.add_argument("--times", help="comma list of seconds for frame grabs (default: mid of 2 cues)")
ap.add_argument("--no-asr", action="store_true")
a = ap.parse_args()

doc = load_cues(a.cues)
groups = groups_of(doc)
vd = os.path.join(a.workdir, "verify")
os.makedirs(vd, exist_ok=True)

print("== streams")
for f in (a.sub_mp4, a.dub_mp4):
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=index,codec_type,codec_name,channels,sample_rate:stream_tags=language,title:stream_disposition=default:format=duration",
         "-of", "json", f]))
    print(os.path.basename(f), f"{float(info['format']['duration']):.2f}s")
    for s in info["streams"]:
        print("  ", s["index"], s["codec_type"], s["codec_name"], s.get("channels", ""),
              s.get("tags", {}).get("language", ""), s.get("tags", {}).get("title", ""),
              "default" if s.get("disposition", {}).get("default") else "")

if a.times:
    times = [float(t) for t in a.times.split(",")]
else:
    c = doc["cues"]
    times = [(c[0]["start"] + c[0]["end"]) / 2]
    if len(c) > 2:
        m = c[len(c) // 2]
        times.append((m["start"] + m["end"]) / 2)
print("== frames (Read these)")
for f, tag in ((a.sub_mp4, "zhsub"), (a.dub_mp4, "dub")):
    for t in times:
        p = os.path.join(vd, f"{tag}_{t:07.2f}.png")
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1",
             "-vf", "crop=iw:ih/3:0:ih*2/3,scale='min(1600,iw)':-2", p])
        print(p)

if not a.no_asr:
    print("== back-transcription of dub (a:0), per group")
    wav = os.path.join(vd, "dub_a0.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", a.dub_mp4, "-map", "0:a:0", "-ac", "1", "-ar", "16000", wav])
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segs, _ = m.transcribe(wav, language="zh", vad_filter=True, beam_size=5,
                           initial_prompt="以下是普通话的句子，使用简体中文。")
    segs = list(segs)
    for g in groups:
        heard = "".join(s.text.strip() for s in segs if g["start"] - 0.3 <= (s.start + s.end) / 2 < g["end"])
        print(f"g{g['id']:<3} {g['start']:7.2f}\n   want: {g['tts']}\n   got : {heard}")
