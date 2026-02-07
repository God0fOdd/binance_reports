# Binance Futures Heatmap + Transformer CLI

CPU-friendly Python tool that fetches Binance Futures BTCUSDT klines and
generates grayscale heatmap patterns. Optional lightweight transformer
embeddings and multi-step predictions run on CPU (NumPy only).

## Features
- Fetch up to 10,000 klines with rate-limit friendly batching.
- Grayscale heatmap pattern images (PNG with PGM fallback).
- Z-score normalization for stable patterns across market regimes.
- Optional lightweight transformer encoder + multi-step prediction output.

## Requirements
- Python 3.10+
- Optional: `numpy` (for transformer embeddings/prediction)
- Optional: `Pillow` (for PNG output)

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install numpy pillow
```

## Usage
Generate heatmaps from BTCUSDT futures klines:
```bash
python heatmap_generator.py --symbol BTCUSDT --interval 1m --total 10000 --output heatmaps
```

Enable transformer embeddings and future prediction:
```bash
python heatmap_generator.py --transformer --predict-steps 5
```

## Outputs
- `heatmaps/`: grayscale pattern images (`.png` or `.pgm`).
- `transformer_output/transformer_embeddings.csv`: transformer embeddings.
- `transformer_output/future_predictions.csv`: multi-step predictions (optional).

## Notes
- The script respects Binance per-request limits (max 1000 klines per call).
- Use `--pause` to increase delay between requests if you hit rate limits.

## License
MIT
