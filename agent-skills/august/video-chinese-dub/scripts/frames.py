"""Grab full frames to verify on-screen asset/folder names (Whisper mangles them).

usage: python frames.py <video> <outdir> <t1> [t2 ...]      (seconds)
writes <outdir>/frame_<t>.png (1600px wide) and prints the paths -> Read them.
"""
import os
import sys

from common import run

video, outdir, times = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(outdir, exist_ok=True)
for t in times:
    p = os.path.join(outdir, f"frame_{float(t):07.2f}.png")
    run(["ffmpeg", "-v", "error", "-y", "-ss", t, "-i", video, "-frames:v", "1",
         "-vf", "scale='min(1600,iw)':-2", p])
    print(p)
