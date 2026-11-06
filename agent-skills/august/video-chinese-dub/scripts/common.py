"""Shared helpers for the video-chinese-dub scripts."""
import json
import os
import re
import subprocess
import sys

FFBIN = r"C:\Program Files\ffmpeg\bin"
if os.path.isdir(FFBIN) and FFBIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFBIN + os.pathsep + os.environ.get("PATH", "")

# Chinese console output must not crash on cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SUB_STYLE = ("FontName={font},Fontsize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=1.2,Shadow=0.5,MarginV=14")
ZH_FONT = "Microsoft YaHei"
EN_FONT = "Segoe UI Semibold"
NVENC = ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "19"]


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd)[:400], flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)])
    return float(out.decode().strip())


def ts(t):
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(path, cues):
    """cues: list of (start, end, text)."""
    body = "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1))
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def load_cues(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def groups_of(doc):
    """Return list of groups: {id, cues:[idx...], start, end(window end), win, tts}.

    Group membership comes from each cue's "group" field (ints, ascending in time).
    Window = group's first cue start -> next group's first cue start - 0.1s
    (last group: -> video duration)."""
    cues = doc["cues"]
    order = []
    members = {}
    for i, c in enumerate(cues):
        g = c["group"]
        if g not in members:
            members[g] = []
            order.append(g)
        members[g].append(i)
    tts_over = {str(k): v for k, v in (doc.get("tts") or {}).items()}
    out = []
    for n, g in enumerate(order):
        idx = members[g]
        start = cues[idx[0]]["start"]
        if n + 1 < len(order):
            end = cues[members[order[n + 1]][0]]["start"] - 0.1
        else:
            end = max(doc.get("duration", cues[idx[-1]]["end"] + 2.0), cues[idx[-1]]["end"])
        text = tts_over.get(str(g)) or default_tts("".join(cues[i]["zh"] for i in idx))
        out.append({"id": g, "cues": idx, "start": start, "end": end, "win": end - start, "tts": text})
    return out


def default_tts(zh):
    """Make subtitle Chinese speakable: drop full-width glosses, underscores, '>' paths."""
    t = re.sub(r"（[^）]*）", "", zh)
    t = re.sub(r"\s*>\s*", "、", t)
    t = t.replace("_", " ")
    t = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", t)  # SnailFarmPCG -> Snail Farm PCG
    t = re.sub(r"\s+", " ", t).strip()
    return t


def cjk_len(s):
    n = len(re.findall(r"[\u4e00-\u9fff]", s))
    return max(n, 1) + len(re.findall(r"[A-Za-z]+", s))  # an English word ~ one syllable-ish


def unique_stem(outdir, name):
    """Never overwrite: bump trailing _NN until neither <stem>.mp4 nor <stem>_ZH_dub.mp4 exist."""
    def taken(stem):
        return any(os.path.exists(os.path.join(outdir, stem + s))
                   for s in (".mp4", "_ZH_dub.mp4", ".zh.srt", "_ZH_dub.en.srt"))
    m = re.match(r"^(.*?)_(\d+)$", name)
    if not m and not taken(name):
        return name
    base, n, width = (m.group(1), int(m.group(2)), len(m.group(2))) if m else (name, 1, 2)
    stem = f"{base}_{n:0{width}d}"
    while taken(stem):
        n += 1
        stem = f"{base}_{n:0{width}d}"
    return stem


def refuse_overwrite(path):
    if os.path.exists(path):
        sys.exit(f"REFUSING to overwrite existing file: {path}")
