"""Transcribe a video with word timestamps and draft subtitle cues + dub groups.

usage: python transcribe.py <video> <workdir> [--model large-v3] [--lang en]

writes <workdir>/words.json   flat list of {w, s, e}
       <workdir>/cues.json    draft: {video, duration, cues:[{start,end,src,en,zh,group}], tts:{}}
Prints the draft cues so the model can translate them.
Cue rules: 2-7s, break at sentence punctuation / pauses; groups = 1-3 cues, sentence-sized.
"""
import argparse
import os
import re

from common import duration, save_json

SENT_END = re.compile(r"[.?!]$")
CLAUSE_END = re.compile(r"[,;:]$")


def split_cues(words, min_d=2.0, max_d=7.0, pause=0.6, hard_gap=1.0):
    cues, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        d = w["e"] - cur[0]["s"]
        gap = (nxt["s"] - w["e"]) if nxt else 99
        would_exceed = nxt is not None and (nxt["e"] - cur[0]["s"]) > max_d
        close = (
            nxt is None
            or gap >= hard_gap
            or (d >= min_d and (SENT_END.search(w["w"]) or gap >= pause))
            or (d >= 4.0 and CLAUSE_END.search(w["w"]))
            or would_exceed
        )
        if close:
            cues.append(cur)
            cur = []
    out = []
    for k, c in enumerate(cues):
        start = c[0]["s"]
        end = c[-1]["e"] + 0.3
        if k + 1 < len(cues):
            end = min(end, cues[k + 1][0]["s"] - 0.05)
        text = " ".join(w["w"] for w in c).strip()
        out.append({"start": round(start, 2), "end": round(end, 2), "src": text, "en": text, "zh": ""})
    return out


def assign_groups(cues, max_n=3, max_win=15.0, gap_break=1.2):
    g, n, gstart = 0, 0, None
    for i, c in enumerate(cues):
        if gstart is None:
            gstart = c["start"]
        c["group"] = g
        n += 1
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        if nxt is None:
            break
        if (SENT_END.search(c["src"]) or n >= max_n or nxt["start"] - c["end"] > gap_break
                or nxt["end"] - gstart > max_win):
            g, n, gstart = g + 1, 0, None
    return cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("workdir")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)

    from faster_whisper import WhisperModel
    m = WhisperModel(a.model, device="cuda", compute_type="float16")
    segs, _ = m.transcribe(a.video, language=a.lang, vad_filter=True, beam_size=5, word_timestamps=True)
    words = []
    for s in segs:
        for w in s.words:
            t = w.word.strip()
            if t:
                words.append({"w": t, "s": round(w.start, 3), "e": round(w.end, 3)})
    del m
    save_json(os.path.join(a.workdir, "words.json"), words)

    cues = assign_groups(split_cues(words))
    doc = {"video": os.path.abspath(a.video), "duration": round(duration(a.video), 3), "cues": cues, "tts": {}}
    save_json(os.path.join(a.workdir, "cues.json"), doc)

    print(f"\n{len(words)} words, {len(cues)} cues, {cues[-1]['group'] + 1 if cues else 0} groups, "
          f"video {doc['duration']:.1f}s -> {os.path.join(a.workdir, 'cues.json')}")
    for i, c in enumerate(cues):
        print(f"[{i:3}] g{c['group']:<3} {c['start']:7.2f}-{c['end']:7.2f}  {c['src']}")


if __name__ == "__main__":
    main()
