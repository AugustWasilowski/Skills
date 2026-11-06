"""Render the Chinese voice-clone dub, one clip per dub group, via the OmniVoice container.

usage: python dub.py <cues.json> <workdir> [--ref-start S --ref-end E --ref-text "..."]
                     [--groups 3,7] [--seed 42] [--keep-running]

- Reference clip: if --ref-* not given, auto-picks the first ~8-12s run of continuous speech
  from <workdir>/words.json and uses its Whisper words as ref_text (printed; check it).
- Each group's TTS text = cues.json "tts"[group] if set, else the group's zh text made speakable
  (glosses/underscores/'>' stripped). Rendered natural first; if longer than the window it is
  re-rendered with duration=window*0.97.
- --groups re-renders only those group ids (others kept from the existing plan.json).
- Starts `docker start omnivoice` and ALWAYS stops it at the end (unless --keep-running).
writes <workdir>/dub/ref.wav, dub/gNNN.wav, dub/plan.json
"""
import argparse
import json
import os
import subprocess
import sys
import time

import requests

from common import duration, groups_of, load_cues, run, save_json

URL = "http://127.0.0.1:3900"


def pick_ref(words, lo=8.0, hi=12.0, gap=0.8):
    for i in range(len(words)):
        j = i
        while j + 1 < len(words) and words[j + 1]["s"] - words[j]["e"] < gap and words[j + 1]["e"] - words[i]["s"] <= hi:
            j += 1
        if words[j]["e"] - words[i]["s"] >= lo:
            return words[i]["s"], words[j]["e"], " ".join(w["w"] for w in words[i:j + 1])
    # fallback: longest stretch from the start
    j = max(k for k in range(len(words)) if words[k]["e"] - words[0]["s"] <= hi)
    return words[0]["s"], words[j]["e"], " ".join(w["w"] for w in words[:j + 1])


def start_server():
    subprocess.run(["docker", "start", "omnivoice"], check=True, stdout=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 180:
        try:
            if requests.get(URL + "/docs", timeout=3).status_code == 200:
                print(f"omnivoice up after {time.time() - t0:.0f}s", flush=True)
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("omnivoice did not come up within 180s")


def stop_server():
    subprocess.run(["docker", "stop", "omnivoice"], stdout=subprocess.DEVNULL)
    print("omnivoice stopped", flush=True)


def gen(text, ref_wav, ref_text, out, seed, dur=None):
    data = {"text": text, "ref_text": ref_text, "language": "Chinese", "seed": str(seed)}
    if dur:
        data["duration"] = f"{dur:.2f}"
    with open(ref_wav, "rb") as f:
        r = requests.post(URL + "/generate", data=data,
                          files={"ref_audio": ("ref.wav", f, "audio/wav")}, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"/generate {r.status_code}: {r.text[:300]}")
    with open(out, "wb") as f:
        f.write(r.content)
    return duration(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cues")
    ap.add_argument("workdir")
    ap.add_argument("--ref-start", type=float)
    ap.add_argument("--ref-end", type=float)
    ap.add_argument("--ref-text")
    ap.add_argument("--groups", help="comma list of group ids to (re)render")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--keep-running", action="store_true")
    a = ap.parse_args()

    doc = load_cues(a.cues)
    groups = groups_of(doc)
    d = os.path.join(a.workdir, "dub")
    os.makedirs(d, exist_ok=True)
    ref_wav = os.path.join(d, "ref.wav")
    plan_path = os.path.join(d, "plan.json")

    if a.ref_start is not None and a.ref_end is not None and a.ref_text:
        rs, re_, rt = a.ref_start, a.ref_end, a.ref_text
    else:
        with open(os.path.join(a.workdir, "words.json"), encoding="utf-8") as f:
            rs, re_, rt = pick_ref(json.load(f))
    print(f"ref {rs:.2f}-{re_:.2f}s: {rt}")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(rs - 0.1, 0):.2f}", "-to", f"{re_ + 0.15:.2f}",
         "-i", doc["video"], "-vn", "-ac", "1", "-ar", "24000", ref_wav])

    old = {}
    if a.groups and os.path.exists(plan_path):
        old = {p["group"]: p for p in json.load(open(plan_path, encoding="utf-8"))["clips"]}
    only = {int(x) for x in a.groups.split(",")} if a.groups else None

    plan = []
    start_server()
    try:
        for g in groups:
            if only is not None and g["id"] not in only and g["id"] in old:
                plan.append(old[g["id"]])
                continue
            out = os.path.join(d, f"g{g['id']:03}.wav")
            dur = gen(g["tts"], ref_wav, rt, out, a.seed)
            note = "natural"
            if dur > g["win"]:
                dur = gen(g["tts"], ref_wav, rt, out, a.seed, dur=g["win"] * 0.97)
                note = "fit"
                if dur > g["win"]:
                    note = "OVER"
            plan.append({"group": g["id"], "file": out, "start": g["start"], "win": round(g["win"], 3),
                         "dur": round(dur, 3), "note": note, "tts": g["tts"]})
            print(f"g{g['id']:<3} start {g['start']:7.2f} win {g['win']:5.2f} dur {dur:5.2f} {note:7} {g['tts']}",
                  flush=True)
    finally:
        if not a.keep_running:
            stop_server()
    save_json(plan_path, {"ref": {"start": rs, "end": re_, "text": rt}, "clips": plan})
    over = [p["group"] for p in plan if p["note"] == "OVER"]
    print(f"wrote {plan_path}" + (f"  WARNING groups still over window: {over} (shorten tts text)" if over else ""))


if __name__ == "__main__":
    sys.exit(main())
