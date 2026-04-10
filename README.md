# DreamZero-SO101: World Action Model for SO-101 Arms

Fine-tuned [DreamZero](https://github.com/dreamzero0/dreamzero) (Wan2.1-I2V-14B + joint action heads) on aggregated SO-101 LeRobot datasets. Predicts **both future video and robot actions** in a single forward pass using flow matching.

> **Status:** LoRA released at 72K training steps. Loss converged (action 0.249 → **0.0015**, dynamics 0.176 → **0.0298**). See [`Vizuara/dreamzero-so101-lora`](https://huggingface.co/Vizuara/dreamzero-so101-lora) for weights and training curve.

## What This Does

Given an SO-101 camera observation + task description, the model jointly predicts:
- **24 future action steps** (6-DOF: shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper)
- **33 future video frames** showing the predicted task execution

Built on DreamZero's architecture: a 14B-parameter DiT (Wan2.1-I2V) with action tokens injected via blockwise causal attention and denoised jointly with video using flow matching.

## Quick Start

```bash
# Clone this repo
git clone https://github.com/Vizuara-AI-Lab/dreamzero-so101.git
cd dreamzero-so101

# Clone DreamZero (Apache 2.0)
git clone https://github.com/dreamzero0/dreamzero.git
cd dreamzero && pip install -e . && cd ..

# Apply SO-101 patch
cd dreamzero && git apply ../patches/so101_embodiment.patch && cd ..

# Download model weights
pip install huggingface_hub
huggingface-cli download Wan-AI/Wan2.1-I2V-14B-480P --local-dir ./checkpoints/Wan2.1-I2V-14B-480P
huggingface-cli download Vizuara/dreamzero-so101-lora --local-dir ./checkpoints/dreamzero-so101-lora
```

## Training Recipe

### 1. Aggregate SO-101 Data

```bash
# Discover all SO-101 datasets on HuggingFace
python scripts/enumerate_so101.py --output so101_manifest.json

# Download and convert to GEAR format
python scripts/download_and_convert.py \
    --manifest so101_manifest.json \
    --output-dir ./data/so101_gear \
    --dreamzero-dir ./dreamzero
```

### 2. Train (LoRA — recommended start)

```bash
# 2× H100, ~127 hours for ~72K steps where loss converges
export WAN_CKPT_DIR=./checkpoints/Wan2.1-I2V-14B-480P
export SO101_DATA_DIR=./data/so101_gear
export TOKENIZER_DIR=./checkpoints/umt5-xxl

bash scripts/train_lora.sh 2 100000   # converges around 70K
```

### 3. Train (Full Fine-Tune — best quality)

```bash
# 4× H100, ~28 hours, ~$336
bash scripts/train_full.sh 4 100000
```

### 4. Evaluate

```bash
python scripts/evaluate.py \
    --model-path ./checkpoints/dreamzero-so101-lora \
    --data-dir ./data/so101_gear \
    --base-model-path ./checkpoints/Wan2.1-I2V-14B-480P
```

### 5. Inference Demo

```bash
python scripts/infer_demo.py \
    --model-path ./checkpoints/dreamzero-so101-lora \
    --image ./sample_obs.jpg \
    --prompt "Pick up the red block and place it in the bin" \
    --base-model-path ./checkpoints/Wan2.1-I2V-14B-480P
```

## Architecture

```
Backbone:      Wan2.1-I2V-14B (40 layers, d=5120, 40 heads, 14B params)
VAE:           WanVAE (4× temporal, 8×8 spatial, 16 latent channels)
Text encoder:  UMT5-XXL (4096-dim → projected to 5120)
Image encoder: CLIP ViT-H/14 (1280-dim → cross-attention)

Action integration:
  ActionEncoder MLP: action_dim → 5120 (with sinusoidal timestep embedding)
  Blockwise causal attention: video + action tokens denoised jointly
  Flow matching: single DiT pass predicts velocity for both video & action
  Inference: 4 Euler steps (~600ms on H100)
```

## Training Details

| Parameter | LoRA | Full FT |
|-----------|------|---------|
| Trainable params | ~50M (LoRA) + action heads | 14B (all DiT) + action heads |
| Learning rate | 1e-4 | 1e-5 |
| Batch size | 1 per GPU | 1 per GPU |
| GPUs | 2× H100 | 4× H100 |
| DeepSpeed | ZeRO-2 | ZeRO-2 + CPU offload |
| Resolution | 320×176 | 320×176 |
| Video frames | 33 (→ 9 latent) | 33 (→ 9 latent) |
| Action horizon | 24 steps | 24 steps |
| LoRA rank | 4 | N/A |
| LoRA targets | q, k, v, o, ffn.0, ffn.2 | N/A |

## SO-101 Datasets Used

| Dataset | Episodes | Tasks | Cameras |
|---------|----------|-------|---------|
| `whosricky/so101-megamix-v1` | 400 | 8 | 3 |
| `lipsop/so101-block-in-bin-100ep` | 100 | 1 | 2 |
| `youliangtan/so101-table-cleanup` | 80 | 4 | 2 |
| `G3ND3K/so101_picking_up_green_lego_big` | 60 | 1 | 2 |
| `lerobot/svla_so101_pickplace` | 50 | 1 | 2 |
| `observabot/so101_cloth_folding1` | 25 | 1 | 3 |
| + additional from Hub search | | | |

All share 6-DOF actions, 30 FPS, LeRobot v2+.

## HuggingFace Releases

- **LoRA (released):** [`Vizuara/dreamzero-so101-lora`](https://huggingface.co/Vizuara/dreamzero-so101-lora) — release weights (~217 MB safetensors), README, training curve
- **Raw checkpoints:** [`Vizuara/dreamzero-so101-checkpoints`](https://huggingface.co/Vizuara/dreamzero-so101-checkpoints) — full intermediate checkpoints (10K, 20K, 30K, 40K, 50K, 60K, 70K) + DeepSpeed state for 20K
- **Full FT:** *(planned)* `Vizuara/dreamzero-so101-14b` — full 14B checkpoint

## Project Structure

```
dreamzero-so101/
  README.md
  setup.py
  requirements.txt
  LICENSE
  configs/
    so101_lora.yaml           # LoRA training config
    so101_full_ft.yaml        # Full fine-tune config
    so101_inference.yaml      # Inference config
    so101_relative.yaml       # GEAR data config (installed via patch)
  scripts/
    enumerate_so101.py        # Find SO-101 datasets on HuggingFace
    download_and_convert.py   # Download + GEAR conversion
    train_lora.sh             # LoRA training launch
    train_full.sh             # Full FT launch
    evaluate.py               # Offline evaluation
    infer_demo.py             # Single-shot inference demo
  patches/
    so101_embodiment.patch    # Add SO-101 to DreamZero's registry
  notebooks/
    quickstart.ipynb          # Colab notebook
```

## Acknowledgments

- [DreamZero](https://github.com/dreamzero0/dreamzero) by GEAR Lab — Apache 2.0 codebase
- [Wan2.1](https://github.com/Wan-Video/Wan2.1) — video generation backbone
- [LeRobot](https://github.com/huggingface/lerobot) — dataset format and community
- SO-101 dataset contributors on HuggingFace Hub

## License

Apache 2.0 (same as DreamZero)
