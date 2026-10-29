"""Fetch a YouTube video's info, transcript, and optionally the video and still frames.

Usage:
  python skills/youtube/scripts/yt_fetch.py <url> [--video] [--frames N] [--lang en]

Writes to data/youtube/<video_id>/ (inside the repo):
  meta.json        title, channel, date, duration, views, description, chapters
  transcript.txt   timestamped lines, rolling auto-caption repeats removed
  transcript_plain.txt  the same words as one block of text
  thumbnail.*      the video thumbnail
  video.mp4        only with --video (720p or lower)
  frames/          only with --frames N (N stills spread across the video)
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

import yt_dlp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_BASE = os.path.join(ROOT, "data", "youtube")


def hms(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def vtt_to_lines(path):
    """Parse a VTT file into (start_seconds, text) lines, dropping the rolling repeats
    that YouTube auto-captions produce."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    cues = re.split(r"\n\s*\n", raw)
    out, seen_tail = [], ""
    for cue in cues:
        m = re.search(r"(\d+):(\d+):(\d+)\.\d+\s+-->", cue)
        if not m:
            continue
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        text_lines = [l for l in cue.splitlines()[1:] if "-->" not in l]
        for line in text_lines:
            line = re.sub(r"<[^>]+>", "", line)
            line = re.sub(r"\s+", " ", line).strip()
            if not line or line == seen_tail:
                continue
            if out and out[-1][1] == line:
                continue
            out.append((start, line))
            seen_tail = line
    return out


def pick_sub(out_dir, vid, lang):
    files = glob.glob(os.path.join(out_dir, f"{vid}*.vtt"))
    if not files:
        return None
    exact = [f for f in files if f".{lang}.vtt" in f]
    return (exact or files)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--video", action="store_true", help="also download the video (720p max)")
    ap.add_argument("--frames", type=int, default=0, help="extract N still frames (implies --video)")
    ap.add_argument("--lang", default="en")
    args = ap.parse_args()
    if args.frames:
        args.video = True

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True,
                           "noprogress": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(args.url, download=False)
    if info.get("_type") == "playlist":  # a search or playlist link: take the first video
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            print("no video found for that link")
            return 1
        info = entries[0]
    args.url = info.get("webpage_url") or args.url
    vid = info["id"]
    out_dir = os.path.join(OUT_BASE, vid)
    os.makedirs(out_dir, exist_ok=True)

    meta = {
        "id": vid,
        "url": info.get("webpage_url"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "duration": hms(info.get("duration")),
        "views": info.get("view_count"),
        "likes": info.get("like_count"),
        "description": info.get("description"),
        "chapters": [
            {"start": hms(c.get("start_time")), "title": c.get("title")}
            for c in (info.get("chapters") or [])
        ],
        "tags": info.get("tags"),
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Subtitles: prefer creator-made, fall back to auto captions. Thumbnail too.
    sub_opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [args.lang, f"{args.lang}-orig"],
        "ignoreerrors": True,
        "subtitlesformat": "vtt",
        "writethumbnail": True,
        "outtmpl": os.path.join(out_dir, f"{vid}.%(ext)s"),
    }
    sub_note = ""
    try:
        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.download([args.url])
    except Exception as e:  # subtitles failing should not lose the rest
        sub_note = f"subtitle download failed: {e}"

    for thumb in glob.glob(os.path.join(out_dir, f"{vid}.*")):
        ext = os.path.splitext(thumb)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            os.replace(thumb, os.path.join(out_dir, "thumbnail" + ext))

    sub = pick_sub(out_dir, vid, args.lang)
    words = 0
    if sub:
        lines = vtt_to_lines(sub)
        with open(os.path.join(out_dir, "transcript.txt"), "w", encoding="utf-8") as f:
            for start, text in lines:
                f.write(f"[{hms(start)}] {text}\n")
        plain = " ".join(t for _, t in lines)
        words = len(plain.split())
        with open(os.path.join(out_dir, "transcript_plain.txt"), "w", encoding="utf-8") as f:
            f.write(plain + "\n")
        kind = "manual" if info.get("subtitles", {}).get(args.lang) else "auto"
        sub_note = f"transcript: {words} words ({kind} captions)"
    elif not sub_note:
        sub_note = "no transcript available for this video"

    video_path = None
    if args.video:
        vopts = {
            "quiet": True,
            "no_warnings": True,
        "noprogress": True,
            "format": "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]/b",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(out_dir, "video.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(vopts) as ydl:
                ydl.download([args.url])
        except Exception as e:  # YouTube often 403s the stream; keep transcript + meta
            print(f"video download failed (transcript and info still saved): {str(e).splitlines()[0]}")
        found = [p for p in glob.glob(os.path.join(out_dir, "video.*")) if not p.endswith(".part")]
        video_path = found[0] if found else None

    frame_count = 0
    if args.frames and video_path and info.get("duration"):
        fdir = os.path.join(out_dir, "frames")
        os.makedirs(fdir, exist_ok=True)
        dur = info["duration"]
        for i in range(args.frames):
            t = dur * (i + 0.5) / args.frames
            dest = os.path.join(fdir, f"frame_{i + 1:02d}_{hms(t).replace(':', '-')}.jpg")
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", video_path,
                 "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "4", dest],
                capture_output=True,
            )
            if r.returncode == 0 and os.path.exists(dest):
                frame_count += 1

    print(f"TITLE: {meta['title']}")
    print(f"CHANNEL: {meta['channel']} | {meta['duration']} | uploaded {meta['upload_date']} | {meta['views']} views")
    print(sub_note)
    if video_path:
        print(f"video: {video_path} ({os.path.getsize(video_path) // (1024 * 1024)} MB)")
    if frame_count:
        print(f"frames: {frame_count} in {os.path.join(out_dir, 'frames')}")
    print(f"FOLDER: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
