---
name: video-chinese-dub
description: Turn an English screen-recording / tool-explainer video into Chinese versions - (1) Chinese subtitles burnt in, and (2) a Chinese voice dub cloned from the speaker's own voice with English subs burnt in and the original English as a second audio track. Use when August says "give me a chinese dub", "dub this video", "translate this video to chinese", "chinese subtitles for this video", "make a chinese version", or hands over a video path for his Chinese counterparts.
---

# Video -> Chinese subs + Chinese voice dub

Outputs (default dir `F:\Snail\TechArt\Videos` unless told otherwise):
1. `<Name>.mp4` - original English audio, Chinese subs burnt in, + `<Name>.zh.srt`
2. `<Name>_ZH_dub.mp4` - a:0 Chinese dub (default), a:1 English original, English subs burnt in timed to the Chinese speech, + `<Name>_ZH_dub.en.srt`

`S=%USERPROFILE%\.claude\skills\video-chinese-dub\scripts`. Work in a scratch workdir (session scratchpad). Set `PYTHONIOENCODING=utf-8` on every python call that prints Chinese.

## Steps

1. **Name.** Use the name August gives; otherwise derive a descriptive PascalCase_Underscore name from the content after transcribing (e.g. `Snail_PCG_Farm_QuickStart_00`) and state it. Resolve a free stem: `python $S/next_name.py <outdir> <Name_00>` (bumps `_NN`; scripts also refuse to overwrite).
2. **Transcribe + draft cues:** `python $S/transcribe.py <video> <work>` -> `words.json`, `cues.json` (cues 2-7s, each with `start,end,src,en,zh,group`; groups of 1-3 cues). Takes ~1 min per 2 min of video.
3. **Check names on screen:** `python $S/frames.py <video> <work>/frames <t1> <t2> ...` at moments where assets/folders/UI are mentioned, then Read the PNGs. Whisper mangles names ("BP snail PCG farm field" -> `BP_SnailPCGFarmField`; "old blueprint toolkit" was really "whole").
4. **Translate - edit `cues.json` yourself** (no external MT):
   - `zh`: natural Simplified Chinese, filler smoothed. Keep UE asset names, folder paths, tech terms in English exactly as shown in the editor, optionally with a gloss: `样条线（Spline）`, `BP_SnailPCGFarmField（蜗牛 PCG 农田蓝图）`, `Art > Environment > SnailFarmPCG 目录`.
   - `en`: cleaned-up English (fillers removed, names corrected).
   - Fix `start`/`end`/`group` if the auto split is bad (group ids must ascend in time; a group ~ one sentence, 1-3 cues). You may merge/split cues.
   - `tts` (optional, `{"<group>": "text"}`): only when the auto-speakable text is wrong. Auto rule drops full-width `（glosses）`, turns `_`/CamelCase into spaced words and `>` into `、`. TTS text must never contain `_` or `>`.
5. **Chinese-sub video:** `python $S/make_srt.py <work>/cues.json zh <work>/zh.srt` then `python $S/burn_subs.py <video> <work>/zh.srt <outdir>/<Name>.mp4`
6. **Dub:** `python $S/dub.py <work>/cues.json <work> [--ref-start S --ref-end E --ref-text "..."]`
   - Starts the `omnivoice` docker container, renders one clip per group (natural; if longer than its window, re-rendered with `duration=window*0.97`), and always stops the container.
   - Without `--ref-*` it auto-picks the first ~8-12s of continuous speech; pass explicit values if that stretch is noisy/music/mumbled.
   - `OVER` in the log = still too long even when squeezed -> shorten that group's `tts` and re-run with `--groups <ids>`.
7. **Mix:** `python $S/mix_dub.py <work>/cues.json <work> <outdir>/<Name>_ZH_dub.mp4`
8. **Verify (mandatory):** `python $S/verify.py <work>/cues.json <work> <Name>.mp4 <Name>_ZH_dub.mp4 [--times a,b]`
   - Read the bottom-strip PNGs it prints (subs legible, not clipped, correct font).
   - Compare `want`/`got` per group from the zh back-transcription; re-render mismatched groups (`dub.py --groups`), then delete the old dub output and re-run mix.
   - Check stream layout: v, a:0 aac chi "Chinese dub" default, a:1 eng "English (original)".
   - Report honestly: output paths, name chosen, any groups that were squeezed/over or mis-heard.

## Gotchas
- Windows console is cp1252: printing Chinese crashes without `PYTHONIOENCODING=utf-8` (scripts reconfigure stdout themselves, inline python does not).
- ffmpeg `subtitles=` paths on Windows: scripts run ffmpeg from the SRT's folder with a relative filename; don't pass `C:\...` into the filter.
- OmniVoice (:3900) hogs the GPU - always `docker stop omnivoice` when done, including after a failure (`dub.py` does this in `finally`; check `docker ps` if something was killed).
- Subtitle text and TTS text differ: subs show `BP_SnailPCGFarmField`, `Art > Environment`; speech must be "BP Snail PCG Farm Field", "Art、Environment".
- Chinese runs longer than English for tech explanations - keep translations tight or the `duration` squeeze makes speech rushed.
- Don't touch previously delivered outputs in `F:\Snail\TechArt\Videos`; always bump the suffix.
- Docs for OmniVoice params (speed, guidance_scale, ...): `F:\MACU\macu-pipeline\docs\_common\OmniVoice_Voice_Tips.md`.
