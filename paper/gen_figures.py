"""
Generate 6 PaperBanana figures for DreamZero-SO101 paper page.
Run with: /tmp/pb_venv/bin/python3 paper/gen_figures.py
"""

import asyncio
import os
import shutil
from pathlib import Path

os.environ["GOOGLE_API_KEY"] = "AIzaSyDa00OYmSGImGNpTojokgM5SKynMIbBv3Q"

from paperbanana import PaperBananaPipeline
from paperbanana.core.config import Settings
from paperbanana.core.types import DiagramType, GenerationInput

OUTPUT_DIR = Path(__file__).parent / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIGURES = [
    {
        "name": "fig1_architecture",
        "input": GenerationInput(
            source_context="""
DreamZero-SO101 is built on top of the Wan2.1-I2V-14B video diffusion transformer (14B parameters,
40 transformer layers, d=5120, 40 attention heads). The video backbone uses a WanVAE encoder to
compress 33 video frames (RGB, 320×176) into a 3D latent grid of 9×44×80 tokens with 16 channels.
Text conditioning is provided by a UMT5-XXL encoder (4096-dim, projected to 5120). Image conditioning
uses CLIP ViT-H/14 cross-attention (1280-dim). The SO-101 robot arm has 6 degrees of freedom:
shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper.

The key innovation is the action head: a small MLP ActionEncoder that takes a 6-DOF joint state plus
a sinusoidal flow-matching timestep embedding and projects it to 5120-dim action tokens. These action
tokens are concatenated to the video token sequence and denoised jointly using blockwise causal attention —
video tokens can attend to action tokens but not vice versa (one-way cross-attention). A single forward
pass through the 14B DiT predicts the velocity field for both video and action simultaneously via flow
matching with 4 Euler steps at inference time (~600ms on H100).

The LoRA adapts Q, K, V, O, and FFN layers with rank=4, adding ~108M trainable parameters to the 14B
backbone. Total model: 14B + 108M LoRA. Checkpoint: 72K training steps, loss converged.
""",
            communicative_intent="""Figure 1: Architecture of DreamZero-SO101. A clean, publication-quality architecture diagram
showing: (left) the input side — a single RGB camera frame going into WanVAE to produce video latent
tokens, the UMT5 text encoder processing a language instruction, and an ActionEncoder MLP processing
the 6-DOF joint state; (center) the 14B Wan2.1 DiT backbone with blockwise causal attention where
video tokens attend to action tokens (shown with dashed arrows); (right) the output side — the decoded
video prediction (imagined next 33 frames) and the predicted 24-step action chunk. The LoRA adapters
(rank 4) should be shown as thin overlay arrows on the DiT layers. Use a clean, academic style with
warm tones, clear labels, and no photorealistic elements.""",
            diagram_type=DiagramType.METHODOLOGY,
        ),
    },
    {
        "name": "fig2_training_pipeline",
        "input": GenerationInput(
            source_context="""
Training pipeline for DreamZero-SO101:

Data collection: 715 episodes aggregated from 6 HuggingFace SO-101 community datasets.
The largest source is whosricky/so101-megamix-v1 (400 episodes, 8 tasks, 3-camera rig).
All datasets share 6-DOF actions, 30 FPS, LeRobot v2+ format.

Data preprocessing (GEAR format conversion):
1. enumerate_so101.py — discovers SO-101 datasets on HF Hub
2. download_and_convert.py — converts LeRobot parquet + video → GEAR format
   (aligned triplets of: camera frame, joint state, action chunk)
3. Result: ~715 episodes × ~400 frames avg × 3 cameras = ~860K training triplets

Training:
- Hardware: 2× NVIDIA H100 80GB SXM5 on RunPod
- Duration: ~127 hours for 72K steps (~1.4 it/s)
- Optimizer: AdamW, lr=1e-4, LoRA rank=4 on Q/K/V/O/FFN
- Batch size: 1 per GPU, gradient accumulation 4
- DeepSpeed ZeRO-2
- Loss: flow matching on video + action jointly, converges to action_loss=0.0015, dynamics_loss=0.0298

Evaluation:
- Single-chunk policy mode: 0.57° RMSE (train), 2.3° RMSE (held-out)
- Zero-shot: 11.9° mean RMSE on unseen dataset
- DreamGen rollout: 71-94° best-match drift over 60 autoregressive chunks
""",
            communicative_intent="""Figure 2: Training pipeline. A horizontal left-to-right flow diagram showing:
(1) HuggingFace datasets (icons for 6 repos) → (2) GEAR format conversion (enumerate + download script)
→ (3) 715 episodes / 860K training triplets → (4) LoRA fine-tuning on 2× H100 (training loss curve
inset showing action_loss dropping from ~0.42 to 0.0015 over 72K steps) → (5) DreamZero-SO101 checkpoint
(217 MB LoRA + 14B backbone) → (6) evaluation with three modes (policy, zero-shot, DreamGen).
Clean academic pipeline figure, horizontal flow, warm neutral palette.""",
            diagram_type=DiagramType.METHODOLOGY,
        ),
    },
    {
        "name": "fig3_eval_framework",
        "input": GenerationInput(
            source_context="""
Three evaluation protocols, in increasing difficulty:

Protocol 1 — Single-chunk policy mode (offline):
Input: one real camera frame + real joint state + language instruction
Output: 24 predicted action steps
Metric: RMSE between predicted and ground-truth actions (degrees)
Results: 0.57° on training ep 0, 1.6–2.3° on held-out eps 50/100, mean 11.9° on zero-shot dataset

Protocol 2 — Zero-shot single-chunk:
Same as Protocol 1 but on a completely unseen dataset (RajatDandekar/so101_box_to_bowl_v2),
different camera rig, objects, table, and task prompt.
8 sample frames evenly spaced across a 604-frame episode.
Best sample: 1.57°, worst: 26.7°, mean: 11.9°

Protocol 3 — DreamGen autoregressive rollout (hardest):
Input: ONE single initial frame + starting joint state
Process: 60 consecutive chunks, each chunk feeds its own predicted video as next input
Output: 540 imagined frames (18 seconds) + 1440 joint commands
No real observations after frame 0.
Three episodes tested (0 pick, 245 pick-and-place, 206 stack), each with training + novel prompt.
Metric: best-match drift (speed-invariant) = 71–94° mean, time-aligned drift = 90–111°
""",
            communicative_intent="""Figure 3: Evaluation framework showing the three protocols in a stacked/layered diagram.
Top row (easiest): single-chunk policy mode — single real frame → model → predicted 24 actions → compare to GT.
Middle row: zero-shot generalization — same protocol on a different dataset, different scene.
Bottom row (hardest): DreamGen autoregressive — single frame feeds 60 consecutive model calls, each
feeding its own output back. Show the feedback loop explicitly with a cycle arrow. Include example RMSE
values next to each protocol. Clean academic style, use color coding (green for easiest, orange for
medium, red for hardest) to indicate difficulty.""",
            diagram_type=DiagramType.METHODOLOGY,
        ),
    },
    {
        "name": "fig4_autoregressive",
        "input": GenerationInput(
            source_context="""
The DreamGen autoregressive loop works as follows:

At each step t:
1. Take the last imagined video frame (or real frame at t=0) + current imagined joint state
2. Encode with WanVAE → latent tokens
3. Run the full 14B DiT forward pass (4 Euler steps)
4. Decode latent → predicted video chunk (9 frames)
5. Extract predicted action chunk (24 joint commands)
6. Execute 1 control step worth of the action chunk on a virtual robot
7. Advance by 1 chunk (the next chunk's input frame = last frame of current predicted video)
8. Repeat for 60 chunks

Post-task degradation failure mode:
After the real episode ends (e.g. at 10.9s for episode 0, 17.9s for episode 245), the model has
never been trained to emit a "task complete" signal. It continues imagining, but with no real ground
truth to compare against. The imagined video starts to drift — the arm hallucinates re-grasps, random
motions, and eventually settles into a looping or stationary dream. This is the main failure mode.

Key numbers: each chunk = 7.6s wall-clock inference, 60 chunks = ~7.5 minutes total for one rollout.
At inference, 4 Euler steps = ~600ms on a single H100.
""",
            communicative_intent="""Figure 4: The autoregressive DreamGen loop and its key failure mode. Left half: a clean circular
diagram showing the 60-chunk feedback loop — initial frame → DiT → (video chunk + action chunk) →
next frame → DiT → ... with a counter showing step 1 through step 60. Right half: the post-task
degradation failure mode — a timeline showing a 60-chunk rollout for episode 0 (10.9s real episode).
Mark the 'task completion zone' (green) up to chunk 11 (~10.9s), then the 'degradation zone' (red)
after that where the arm keeps moving after the task is done. Include a small inset sketch of the arm
completing the pick (success) then hallucinating random motion (failure). Warm academic style.""",
            diagram_type=DiagramType.METHODOLOGY,
        ),
    },
    {
        "name": "fig5_results",
        "input": GenerationInput(
            source_context="""
Summary of all quantitative results for DreamZero-SO101:

Single-chunk policy mode results (action RMSE in degrees):
- Episode 0 (training, frame 0): 0.57°
- Episode 50 (held-out, frame 0): 2.29°
- Episode 100 (held-out, frame 0): 1.60°
- ep50 frame 80 (descend phase): 11.97°
- ep100 frame 150 (grasp phase): 8.40°

Zero-shot (RajatDandekar/so101_box_to_bowl_v2):
- Mean: 11.9°
- Median: 13.4°
- Best: 1.57°
- Worst: 26.7°
- Mean video PSNR: 18.5 dB

DreamGen rollout honest drift metrics:
Episode 0, training prompt: best-match 93.7°, time-aligned 96.8°
Episode 0, novel prompt: best-match 90.1°, time-aligned 97.3°
Episode 245, training: best-match 74.0°, time-aligned 109.0°
Episode 245, novel: best-match 85.3°, time-aligned 111.1°
Episode 206, training: best-match 71.0°, time-aligned 90.1°
Episode 206, novel: best-match 83.4°, time-aligned 102.5°

Key interpretation: single-chunk policy mode is in the deployable range (1-12° RMSE).
DreamGen drift of 71-94° best-match sounds large but includes speed-mismatch penalty.
All 6 rollouts visually complete the intended task in the imagined video.
""",
            communicative_intent="""Figure 5: Results summary. A clean multi-panel figure with three panels:
Panel A (bar chart): single-chunk RMSE for all 5 evaluation points — ep0/50/100 cruise frames (green bars,
0.57-2.29°) and mid-episode frames (orange bars, 8-12°) and zero-shot mean (red bar, 11.9°).
Panel B (horizontal grouped bar chart): DreamGen best-match drift (dark bar) vs time-aligned drift
(light bar) for all 6 rollouts (ep000_train, ep000_novel, ep245_train, ep245_novel, ep206_train,
ep206_novel). Best-match in teal/green, time-aligned in orange, dashed line at 90°.
Panel C (small text box): key findings summary — 'task executed in imagination: yes', '1K LoRA
checkpoint', '217 MB adapter'. Clean, academic, publication-quality bar charts with Inter font labels.""",
            diagram_type=DiagramType.STATISTICAL_PLOT,
        ),
    },
    {
        "name": "fig6_contribution",
        "input": GenerationInput(
            source_context="""
Community contribution flow for DreamZero-SO101:

Anyone with an SO-101 arm can contribute data and improve the model. The process:

Step 1 — Record episodes:
Use LeRobot v0.4+ with the 3-camera SO-101 rig (front, top, gripper)
Record 30+ episodes of any manipulation task
Required: 6-DOF actions, 30 FPS, RGB cameras

Step 2 — Format as LeRobot:
push_dataset_to_hub() with standard LeRobot schema
Meta: {robot_type: so101, cameras: [front, top, gripper], task_description: "..."}
Upload to HuggingFace Hub under any handle

Step 3 — Submit:
Open a PR on github.com/vizuara/dreamzero-so101 adding your dataset to the manifest
Or email team@vizuara.ai with the HF dataset URL

Step 4 — Vizuara retrains:
We run download_and_convert.py on the new dataset
Retrain from the latest checkpoint (continue LoRA from 72K steps)
Community data accumulates: 715 → 900 → 1200 → ... episodes

Step 5 — Release:
New DreamZero-SO101 checkpoint released to Vizuara/dreamzero-so101-lora
Contributor credited in README and HF model card
Model gets incrementally better with each contribution wave

Future plans: HuggingFace data partnership, automated retraining pipeline, leaderboard
""",
            communicative_intent="""Figure 6: Community contribution flow. A clean 5-step numbered vertical or circular flow diagram
showing: (1) SO-101 arm recording episodes (camera icon + robot sketch), (2) LeRobot formatting and HF
Hub upload (HuggingFace logo style icon), (3) GitHub PR submission (PR icon), (4) Vizuara retraining
on 2× H100 (GPU icon + training curve growing), (5) new checkpoint released back to community (download
icon + version bump 72K → 100K → 200K). Include a small data flywheel annotation showing that each
release attracts more contributors. Warm, inviting academic style, community-friendly feel.""",
            diagram_type=DiagramType.METHODOLOGY,
        ),
    },
]


async def main():
    settings = Settings(
        vlm_model="gemini-2.0-flash",
        image_model="gemini-3-pro-image-preview",
        refinement_iterations=2,
        output_dir=str(OUTPUT_DIR / "_runs"),
    )

    pipeline = PaperBananaPipeline(settings=settings)

    for spec in FIGURES:
        name = spec["name"]
        out_path = OUTPUT_DIR / f"{name}.png"
        if out_path.exists():
            print(f"  [skip] {name}.png already exists")
            continue

        print(f"  [gen]  {name} ...")
        try:
            result = await pipeline.generate(spec["input"])
            shutil.copy(result.image_path, out_path)
            print(f"  [ok]   {name}.png → {out_path}")
        except Exception as e:
            print(f"  [err]  {name}: {e}")

    print("\nDone. Figures in:", OUTPUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())
