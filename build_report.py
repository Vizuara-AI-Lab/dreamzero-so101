#!/usr/bin/env python3
"""Build the WAM report: crop predicted videos into views, make plots, write HTML."""
import os, json, subprocess, math
import numpy as np
import imageio.v3 as iio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(ROOT, "demo")
EPS = ["train_ep0", "heldout_ep50", "heldout_ep100"]

# ---- Vizuara warm dark palette ----
BG       = "#1A1915"
PANEL    = "#241F1A"
INK      = "#F2EAD8"
INK_DIM  = "#A89C82"
ACCENT   = "#D97757"
TEAL     = "#7DA488"
BLUE     = "#5B8CB8"
WARM     = "#C4956A"
PURPLE   = "#9B7EC8"

JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
JOINT_COLORS = [ACCENT, WARM, TEAL, BLUE, PURPLE, "#E8C547"]


def ffmpeg(*args):
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def crop_quadrant(in_path, out_path, x, y, w, h):
    """Crop a quadrant of the predicted mosaic and resize to consistent display size."""
    ffmpeg(
        "-i", in_path,
        "-vf", f"crop={w}:{h}:{x}:{y},scale=480:264:flags=lanczos",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        out_path,
    )


def resize_video(in_path, out_path, w, h):
    ffmpeg("-i", in_path, "-vf", f"scale={w}:{h}:flags=lanczos",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20", out_path)


def compute_front_psnr(pred_path, gt_path):
    """Compute PSNR between predicted front view and GT front view (both already cropped/resized)."""
    pred = np.stack(list(iio.imiter(pred_path))).astype(np.float32)
    gt = np.stack(list(iio.imiter(gt_path))).astype(np.float32)
    n = min(len(pred), len(gt))
    pred = pred[:n]; gt = gt[:n]
    if pred.shape[1:] != gt.shape[1:]:
        # resize pred to gt
        pred = np.stack([
            np.array(Image.fromarray(p.astype(np.uint8)).resize((gt.shape[2], gt.shape[1]), Image.LANCZOS))
            for p in pred
        ]).astype(np.float32)
    mse = float(((pred - gt) ** 2).mean())
    psnr = float(20 * np.log10(255.0) - 10 * np.log10(mse + 1e-8))
    return mse, psnr, n


def make_action_plot(meta, out_path):
    pred = np.array(meta["actions_pred"], dtype=np.float64)  # (24, 6)
    gt = np.array(meta["actions_gt"], dtype=np.float64)
    T = pred.shape[0]
    t = np.arange(T) / 30.0  # seconds at 30 FPS

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
        f"{meta['prompt']}   ·   action RMSE {meta['action_rmse_deg']:.2f}°   ·   episode {meta['episode']}",
        color=INK, fontsize=13, y=0.995, family="serif",
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, facecolor=BG, edgecolor="none", bbox_inches="tight")
    plt.close(fig)


def make_per_step_plot(metas, out_path):
    fig, ax = plt.subplots(figsize=(11, 4.4), facecolor=BG)
    ax.set_facecolor(PANEL)
    colors = [TEAL, ACCENT, BLUE]
    for m, c in zip(metas, colors):
        steps = np.arange(len(m["per_step_mse"])) / 30.0
        ax.plot(steps, m["per_step_mse"], color=c, linewidth=2.4,
                label=f'{m["tag"]} — "{m["prompt"]}"  (RMSE {m["action_rmse_deg"]:.2f}°)')
    ax.set_xlabel("prediction horizon (s)", color=INK_DIM, fontsize=10)
    ax.set_ylabel("per-step MSE  (deg²)", color=INK_DIM, fontsize=10)
    ax.set_title("Action error grows with horizon — model is sharp early, drifts late",
                 color=INK, fontsize=12, family="serif")
    ax.tick_params(colors=INK_DIM)
    for spine in ax.spines.values():
        spine.set_color("#3a342c")
    ax.grid(True, color="#2c2823", linewidth=0.6)
    ax.legend(facecolor=PANEL, edgecolor="#3a342c", labelcolor=INK, fontsize=9, loc="upper left")
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, facecolor=BG, edgecolor="none", bbox_inches="tight")
    plt.close(fig)


# ---- main ----
metas = []
for tag in EPS:
    d = os.path.join(DEMO, tag)
    meta = json.load(open(os.path.join(d, "meta.json")))
    pred = os.path.join(d, "predicted_video.mp4")

    # Predicted is 640x352 mosaic. Quadrants are 320x176.
    crop_quadrant(pred, os.path.join(d, "pred_front.mp4"),   0,   0, 320, 176)
    crop_quadrant(pred, os.path.join(d, "pred_top.mp4"),   320,   0, 320, 176)
    crop_quadrant(pred, os.path.join(d, "pred_gripper.mp4"), 0, 176, 320, 176)

    # Resize GT front to match display size
    resize_video(os.path.join(d, "gt_future.mp4"), os.path.join(d, "gt_front_display.mp4"), 480, 264)
    resize_video(os.path.join(d, "gt_future_full.mp4"), os.path.join(d, "gt_front_full_display.mp4"), 480, 264)

    # Compute per-view PSNR (front only — only view we have GT for)
    mse, psnr, n_compared = compute_front_psnr(
        os.path.join(d, "pred_front.mp4"),
        os.path.join(d, "gt_future.mp4"),
    )
    meta["front_pixel_mse"] = mse
    meta["front_psnr_db"] = psnr
    meta["front_frames_compared"] = n_compared

    # Make action plot
    make_action_plot(meta, os.path.join(d, "action_plot.png"))
    metas.append(meta)
    print(f"{tag}: front PSNR {psnr:.2f} dB ({n_compared} frames)  action RMSE {meta['action_rmse_deg']:.2f}°")

make_per_step_plot(metas, os.path.join(DEMO, "per_step_horizon.png"))
print("done.")

# Save consolidated meta
with open(os.path.join(DEMO, "all_metas.json"), "w") as f:
    json.dump(metas, f, indent=2)
