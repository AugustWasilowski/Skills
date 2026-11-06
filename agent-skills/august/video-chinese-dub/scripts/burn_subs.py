"""Burn an SRT into a video (audio copied), and copy the SRT beside the output as a sidecar.

usage: python burn_subs.py <video> <srt> <out.mp4> [--font "Microsoft YaHei"] [--sidecar-lang zh]
Runs ffmpeg from the SRT's directory with a relative filename (avoids Windows filter escaping).
Refuses to overwrite existing outputs.
"""
import argparse
import os
import shutil

from common import NVENC, SUB_STYLE, ZH_FONT, refuse_overwrite, run

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("srt")
ap.add_argument("out")
ap.add_argument("--font", default=ZH_FONT)
ap.add_argument("--sidecar-lang", default="zh")
a = ap.parse_args()

out = os.path.abspath(a.out)
sidecar = os.path.splitext(out)[0] + f".{a.sidecar_lang}.srt"
refuse_overwrite(out)
refuse_overwrite(sidecar)
os.makedirs(os.path.dirname(out), exist_ok=True)
srt_dir, srt_name = os.path.split(os.path.abspath(a.srt))
style = SUB_STYLE.format(font=a.font)
run(["ffmpeg", "-v", "error", "-n", "-i", os.path.abspath(a.video),
     "-vf", f"subtitles={srt_name}:force_style='{style}'",
     *NVENC, "-c:a", "copy", out], cwd=srt_dir)
shutil.copyfile(a.srt, sidecar)
print(f"wrote {out}\nwrote {sidecar}")
