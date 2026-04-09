#!/usr/bin/env python3
"""Process the 6 mid-episode samples: crop quadrants, slow-encode, generate plots, write JSON."""
import os, json, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "demo_mid")
SAMPLES = [
    "ep50_f80_descend",
    "ep50_f150_grasp",
    "ep50_f220_lift",
    "ep100_f80_descend",
    "ep100_f150_grasp",
    "ep100_f220_lift",
]
FF = "/opt/homebrew/bin/ffmpeg"

# Vizuara palette
BG = "#1A1915"; PANEL = "#241F1A"; INK = "#F2EAD8"; INK_DIM = "#A89C82"
ACCENT = "#D97757"; WARM = "#C4956A"; TEAL = "#7DA488"; BLUE = "#5B8CB8"; PURPLE = "#9B7EC8"
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINT_COLORS = [ACCENT, WARM, TEAL, BLUE, PURPLE, "#E8C547"]

PRED_SLOW = 4
GT_SLOW = 2


def crop_slow(in_path, out_path, x, y, w, h, slowfactor=PRED_SLOW):
    f = f"crop={w}:{h}:{x}:{y},setpts={slowfactor}*PTS,scale=480:264:flags=lanczos"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", in_path,
                    "-vf", f, "-r", "30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20", "-an", out_path],
                   check=True)


def slow(in_path, out_path, slowfactor):
    f = f"setpts={slowfactor}*PTS,scale=480:264:flags=lanczos"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", in_path,
                    "-vf", f, "-r", "30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20", "-an", out_path],
                   check=True)


def make_action_plot(meta, out_path):
    pred = np.array(meta["actions_pred"], dtype=np.float64)
    gt = np.array(meta["actions_gt"], dtype=np.float64)
    T = pred.shape[0]
    t = np.arange(T) / 30.0
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.2), facecolor=BG)
    axes = axes.flatten()
    for i, ax in enumerate(axes):
        ax.set_facecolor(PANEL)
        ax.plot(t, gt[:, i], color=INK_DIM, linewidth=2.6, linestyle="--", label="ground truth")
        ax.plot(t, pred[:, i], color=JOINT_COLORS[i], linewidth=2.6, label="predicted")
        ax.set_title(JOINT_NAMES[i], color=INK, fontsize=11, pad=6, family="serif")
        ax.set_xlabel("time (s)", color=INK_DIM, fontsize=8)
        ax.set_ylabel("angle (°)", color=INK_DIM, fontsize=8)
        ax.tick_params(colors=INK_DIM, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#3a342c")
        ax.grid(True, color="#2c2823", linewidth=0.6)
        if i == 0:
            ax.legend(facecolor=PANEL, edgecolor="#3a342c", labelcolor=INK, fontsize=8, loc="best")
    fig.suptitle(
        f'{meta["prompt"]}   ·   ep{meta["episode"]} f{meta["frame_in_ep"]}'
        f'   ·   GT motion {meta["gt_motion_magnitude_deg"]:.1f}°   ·   action RMSE {meta["action_rmse_deg"]:.2f}°',
        color=INK, fontsize=12, y=0.995, family="serif",
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, facecolor=BG, edgecolor="none", bbox_inches="tight")
    plt.close(fig)


metas = []
for tag in SAMPLES:
    d = os.path.join(DEMO, tag)
    meta = json.load(open(os.path.join(d, "meta.json")))
    pred = os.path.join(d, "predicted_video.mp4")
    gt_full = os.path.join(d, "gt_future_full.mp4")
    gt_short = os.path.join(d, "gt_future.mp4")

    crop_slow(pred, os.path.join(d, "pred_front_slow.mp4"),     0,   0, 320, 176)
    crop_slow(pred, os.path.join(d, "pred_top_slow.mp4"),     320,   0, 320, 176)
    crop_slow(pred, os.path.join(d, "pred_gripper_slow.mp4"),   0, 176, 320, 176)
    slow(gt_short, os.path.join(d, "gt_front_short_slow.mp4"), PRED_SLOW)
    slow(gt_full,  os.path.join(d, "gt_front_full_slow.mp4"),  GT_SLOW)
    make_action_plot(meta, os.path.join(d, "action_plot.png"))
    print(f"{tag}: prompt={meta['prompt']!r}  ep{meta['episode']} f{meta['frame_in_ep']}  "
          f"GTmotion={meta['gt_motion_magnitude_deg']:.1f}°  RMSE={meta['action_rmse_deg']:.2f}°")
    metas.append(meta)

with open(os.path.join(DEMO, "all_metas.json"), "w") as f:
    json.dump(metas, f, indent=2)
print("done.")
