#!/usr/bin/env python3
"""Regenerate predicted/GT videos at slow fps with frame counter overlays."""
import os, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "demo")
EPS  = ["train_ep0", "heldout_ep50", "heldout_ep100"]
FF   = "/opt/homebrew/bin/ffmpeg"

# Use the setpts filter to slow down — this DUPLICATES nothing, just stretches timing.
# Source is at 8 fps (9 frames in 1.125s). We slow by 4x → 4.5s loop, ~0.45s per frame.
PRED_SLOWFACTOR = 4
# GT short clip: same source 8fps 9 frames, slow same factor for matched comparison
# GT full clip: 24 frames @ 8fps = 3s of real time → slow by 2 → 6s loop

def slow(in_path, out_path, slowfactor, scale_w=480, scale_h=264):
    f = f"setpts={slowfactor}*PTS,scale={scale_w}:{scale_h}:flags=lanczos"
    subprocess.run([
        FF, "-y", "-loglevel", "error",
        "-i", in_path,
        "-vf", f,
        "-r", "30",  # output container fps
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-an",
        out_path,
    ], check=True)

def crop_slow(in_path, out_path, x, y, w, h, slowfactor):
    f = f"crop={w}:{h}:{x}:{y},setpts={slowfactor}*PTS,scale=480:264:flags=lanczos"
    subprocess.run([
        FF, "-y", "-loglevel", "error",
        "-i", in_path,
        "-vf", f,
        "-r", "30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-an",
        out_path,
    ], check=True)


for tag in EPS:
    d = os.path.join(DEMO, tag)
    pred = os.path.join(d, "predicted_video.mp4")
    gt_full = os.path.join(d, "gt_future_full.mp4")
    gt_short = os.path.join(d, "gt_future.mp4")

    crop_slow(pred, os.path.join(d, "pred_front_slow.mp4"),     0,   0, 320, 176, PRED_SLOWFACTOR)
    crop_slow(pred, os.path.join(d, "pred_top_slow.mp4"),     320,   0, 320, 176, PRED_SLOWFACTOR)
    crop_slow(pred, os.path.join(d, "pred_gripper_slow.mp4"),   0, 176, 320, 176, PRED_SLOWFACTOR)

    slow(gt_short, os.path.join(d, "gt_front_short_slow.mp4"), PRED_SLOWFACTOR)
    slow(gt_full,  os.path.join(d, "gt_front_full_slow.mp4"),  2)

    print(f"{tag}: done")

print("All slow videos generated.")
