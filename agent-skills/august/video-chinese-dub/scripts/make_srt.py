"""Write an SRT from cues.json using the ORIGINAL cue timing.

usage: python make_srt.py <cues.json> <zh|en> <out.srt>
"""
import sys

from common import load_cues, write_srt

doc = load_cues(sys.argv[1])
lang, out = sys.argv[2], sys.argv[3]
cues = [(c["start"], c["end"], c[lang]) for c in doc["cues"]]
missing = [i for i, (_, _, t) in enumerate(cues) if not t.strip()]
if missing:
    sys.exit(f"cues missing '{lang}' text: {missing}")
write_srt(out, cues)
print(f"wrote {out} ({len(cues)} cues)")
