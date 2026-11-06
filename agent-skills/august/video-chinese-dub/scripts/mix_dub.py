"""Mix the dub clips, retime English subs to the Chinese speech, and mux the dub video.

usage: python mix_dub.py <cues.json> <workdir> <out_ZH_dub.mp4> [--font "Segoe UI Semibold"]

- English subs: within each group, the clip's actual duration is split across its cues in
  proportion to Chinese character count; last cue extended +0.6s (capped before next group).
  -> <workdir>/en_dub.srt, copied to <out stem>.en.srt
- Audio: anullsrc full length + each clip adelay'd to its group start, amix normalize=0, 48k AAC 192k.
- Streams: v (English subs burnt in) | a:0 Chinese dub (default, chi) | a:1 original (copy, eng).
Refuses to overwrite existing outputs.
"""
import argparse
import json
import os
import shutil

from common import EN_FONT, NVENC, SUB_STYLE, cjk_len, groups_of, load_cues, refuse_overwrite, run, write_srt

ap = argparse.ArgumentParser()
ap.add_argument("cues")
ap.add_argument("workdir")
ap.add_argument("out")
ap.add_argument("--font", default=EN_FONT)
a = ap.parse_args()

doc = load_cues(a.cues)
cues = doc["cues"]
groups = groups_of(doc)
plan = {p["group"]: p for p in json.load(open(os.path.join(a.workdir, "dub", "plan.json"), encoding="utf-8"))["clips"]}
missing = [g["id"] for g in groups if g["id"] not in plan]
if missing:
    raise SystemExit(f"no dub clip for groups {missing}; run dub.py (groups changed since last render?)")

out = os.path.abspath(a.out)
sidecar = os.path.splitext(out)[0] + ".en.srt"
refuse_overwrite(out)
refuse_overwrite(sidecar)

# --- English subs retimed to the Chinese audio
srt = []
for n, g in enumerate(groups):
    p = plan[g["id"]]
    nxt = groups[n + 1]["start"] if n + 1 < len(groups) else doc["duration"]
    w = [cjk_len(cues[i]["zh"]) for i in g["cues"]]
    t = p["start"]
    for k, i in enumerate(g["cues"]):
        dd = p["dur"] * w[k] / sum(w)
        end = t + dd
        if k == len(g["cues"]) - 1:
            end = min(end + 0.6, nxt - 0.05)
        srt.append((t, end, cues[i]["en"]))
        t += dd
en_srt = os.path.join(a.workdir, "en_dub.srt")
write_srt(en_srt, srt)
print(f"wrote {en_srt}")

# --- mix + mux (run from workdir so the subtitles filter gets a relative path)
clips = [plan[g["id"]] for g in groups]
ins = ["-i", os.path.abspath(doc["video"]),
       "-f", "lavfi", "-t", f"{doc['duration']:.3f}", "-i", "anullsrc=r=24000:cl=mono"]
fc = []
for i, p in enumerate(clips):
    ins += ["-i", os.path.abspath(p["file"])]
    fc.append(f"[{i + 2}:a]aformat=sample_rates=24000:channel_layouts=mono,adelay={int(round(p['start'] * 1000))}:all=1[a{i}]")
fc.append("[1:a]" + "".join(f"[a{i}]" for i in range(len(clips)))
          + f"amix=inputs={len(clips) + 1}:normalize=0:duration=first,aresample=48000,aformat=channel_layouts=stereo[zh]")
style = SUB_STYLE.format(font=a.font)
fc.append(f"[0:v]subtitles=en_dub.srt:force_style='{style}'[v]")
script = os.path.join(a.workdir, "mix_filter.txt")
with open(script, "w", encoding="utf-8") as f:
    f.write(";\n".join(fc))

run(["ffmpeg", "-v", "error", "-n", *ins, "-filter_complex_script", "mix_filter.txt",
     "-map", "[v]", "-map", "[zh]", "-map", "0:a:0",
     *NVENC, "-c:a:0", "aac", "-b:a:0", "192k", "-c:a:1", "copy",
     "-metadata:s:a:0", "language=chi", "-metadata:s:a:0", "title=Chinese dub",
     "-metadata:s:a:1", "language=eng", "-metadata:s:a:1", "title=English (original)",
     "-disposition:a:0", "default", "-disposition:a:1", "0",
     out], cwd=a.workdir)
shutil.copyfile(en_srt, sidecar)
print(f"wrote {out}\nwrote {sidecar}")
