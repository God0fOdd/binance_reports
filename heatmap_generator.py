#!/usr/bin/env python3
"""Generate grayscale heatmap patterns from Binance Futures BTCUSDT klines.

This script is designed for Windows CPU-only, non-graphics environments. It
fetches up to 3,000 klines using 3 REST requests and writes grayscale image
files to disk.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import time
import urllib.parse
import urllib.request
from typing import Iterable, List, Sequence, Tuple


BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"


def fetch_klines(
    symbol: str,
    interval: str,
    total: int = 10000,
    per_request: int = 1000,
    max_requests: int = 10,
    pause_s: float = 0.5,
) -> List[List[float]]:
    """Fetch klines from Binance Futures REST API."""
    collected: List[List[float]] = []
    end_time: int | None = None

    for _ in range(max_requests):
        remaining = total - len(collected)
        if remaining <= 0:
            break
        limit = min(per_request, remaining, 1000)
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time is not None:
            params["endTime"] = end_time
        query = urllib.parse.urlencode(params)
        url = f"{BINANCE_FAPI_BASE_URL}/fapi/v1/klines?{query}"

        with urllib.request.urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
        data = json.loads(payload)
        if not data:
            break

        collected = data + collected
        earliest_open_time = int(collected[0][0])
        end_time = earliest_open_time - 1
        time.sleep(pause_s)

    return collected[-total:]


def extract_close_prices(klines: Sequence[Sequence[float]]) -> List[float]:
    return [float(row[4]) for row in klines]


def normalize_to_uint8(values: Sequence[float]) -> List[int]:
    min_val = min(values)
    max_val = max(values)
    if math.isclose(max_val, min_val):
        return [128 for _ in values]
    scale = 255.0 / (max_val - min_val)
    return [int((val - min_val) * scale) for val in values]


def build_distance_heatmap(window: Sequence[float]) -> List[List[int]]:
    """Create a grayscale heatmap using pairwise absolute distances."""
    matrix: List[List[float]] = []
    for value_i in window:
        row = [abs(value_i - value_j) for value_j in window]
        matrix.append(row)
    flat = [value for row in matrix for value in row]
    normalized = normalize_to_uint8(flat)
    size = len(window)
    return [
        normalized[i * size : (i + 1) * size]
        for i in range(size)
    ]


def zscore(values: Sequence[float]) -> List[float]:
    mean = sum(values) / len(values)
    variance = sum((val - mean) ** 2 for val in values) / len(values)
    std = math.sqrt(variance) or 1.0
    return [(val - mean) / std for val in values]


def iter_windows(
    values: Sequence[float],
    window_size: int,
    step: int,
) -> Iterable[Tuple[int, Sequence[float]]]:
    for start in range(0, len(values) - window_size + 1, step):
        yield start, values[start : start + window_size]


def write_pgm(path: str, matrix: Sequence[Sequence[int]]) -> None:
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    header = f"P2\n{width} {height}\n255\n"
    with open(path, "w", encoding="utf-8") as file:
        file.write(header)
        for row in matrix:
            file.write(" ".join(str(pixel) for pixel in row))
            file.write("\n")


def write_png(path: str, matrix: Sequence[Sequence[int]]) -> None:
    import importlib.util

    if importlib.util.find_spec("PIL") is None:
        write_pgm(os.path.splitext(path)[0] + ".pgm", matrix)
        return

    from PIL import Image

    height = len(matrix)
    width = len(matrix[0]) if height else 0
    image = Image.new("L", (width, height))
    pixels = [pixel for row in matrix for pixel in row]
    image.putdata(pixels)
    image.save(path)


def maybe_run_transformer(
    matrices: Sequence[Sequence[Sequence[int]]],
    output_dir: str,
    token_size: int,
    heads: int,
    predict_steps: int,
) -> str | None:
    """Run a lightweight NumPy transformer encoder over heatmaps if available."""
    import importlib.util

    if importlib.util.find_spec("numpy") is None:
        return None

    import numpy as np

    os.makedirs(output_dir, exist_ok=True)
    tokens: List[np.ndarray] = []
    for matrix in matrices:
        data = np.array(matrix, dtype=np.float32)
        patches = data.reshape(-1, token_size)[:token_size]
        tokens.append(patches.mean(axis=0))

    if not tokens:
        return None

    token_matrix = np.stack(tokens, axis=0)
    d_model = token_matrix.shape[1]
    head_dim = max(1, d_model // heads)

    def split_heads(x: np.ndarray) -> np.ndarray:
        x = x[:, : heads * head_dim]
        return x.reshape(x.shape[0], heads, head_dim)

    def softmax(x: np.ndarray) -> np.ndarray:
        x = x - np.max(x, axis=-1, keepdims=True)
        exp = np.exp(x)
        return exp / np.sum(exp, axis=-1, keepdims=True)

    q = split_heads(token_matrix)
    k = split_heads(token_matrix)
    v = split_heads(token_matrix)

    scores = np.einsum("thd,Thd->htT", q, k) / math.sqrt(head_dim)
    attn = softmax(scores)
    context = np.einsum("htT,Thd->thd", attn, v)
    context = context.reshape(context.shape[0], -1)

    output_path = os.path.join(output_dir, "transformer_embeddings.csv")
    np.savetxt(output_path, context, delimiter=",")
    if predict_steps > 0:
        predictions = predict_future_steps(context, predict_steps)
        pred_path = os.path.join(output_dir, "future_predictions.csv")
        np.savetxt(pred_path, predictions, delimiter=",")
    return output_path


def predict_future_steps(embeddings: "np.ndarray", steps: int) -> "np.ndarray":
    """Predict future steps using a lightweight linear projection."""
    import numpy as np

    if embeddings.shape[0] < 2:
        return np.zeros((steps, embeddings.shape[1]), dtype=np.float32)
    x = embeddings[:-1]
    y = embeddings[1:]
    xtx = x.T @ x + 1e-3 * np.eye(x.shape[1])
    weights = np.linalg.solve(xtx, x.T @ y)
    last = embeddings[-1]
    predictions = []
    current = last
    for _ in range(steps):
        current = current @ weights
        predictions.append(current)
    return np.stack(predictions, axis=0)


def generate_heatmaps(
    prices: Sequence[float],
    window_size: int,
    step: int,
    output_dir: str,
    prefix: str,
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    written: List[str] = []
    for index, window in iter_windows(prices, window_size, step):
        matrix = build_distance_heatmap(window)
        filename = f"{prefix}_{index:04d}.png"
        path = os.path.join(output_dir, filename)
        write_png(path, matrix)
        written.append(path)
    return written


def format_timestamp(ms: int) -> str:
    return dt.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Binance Futures klines and generate grayscale heatmaps."
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Futures symbol.")
    parser.add_argument("--interval", default="1m", help="Kline interval.")
    parser.add_argument("--total", type=int, default=10000, help="Total klines.")
    parser.add_argument(
        "--per-request",
        type=int,
        default=1000,
        help="Klines per request (max 1000).",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=10,
        help="Maximum number of REST requests.",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="Seconds to sleep between REST requests.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=64,
        help="Window size for heatmap.",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=32,
        help="Step between windows.",
    )
    parser.add_argument(
        "--output",
        default="heatmaps",
        help="Output directory for images.",
    )
    parser.add_argument(
        "--prefix",
        default="pattern",
        help="Output filename prefix.",
    )
    parser.add_argument(
        "--transformer",
        action="store_true",
        help="Run a lightweight NumPy transformer encoder on heatmaps.",
    )
    parser.add_argument(
        "--transformer-dir",
        default="transformer_output",
        help="Output directory for transformer embeddings.",
    )
    parser.add_argument(
        "--token-size",
        type=int,
        default=64,
        help="Token size used for lightweight transformer encoder.",
    )
    parser.add_argument(
        "--heads",
        type=int,
        default=4,
        help="Number of attention heads for transformer encoder.",
    )
    parser.add_argument(
        "--predict-steps",
        type=int,
        default=0,
        help="Predict future steps from transformer embeddings.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    klines = fetch_klines(
        symbol=args.symbol,
        interval=args.interval,
        total=args.total,
        per_request=args.per_request,
        max_requests=args.max_requests,
        pause_s=args.pause,
    )
    if not klines:
        raise SystemExit("No data returned from Binance API.")

    prices = extract_close_prices(klines)
    prices = zscore(prices)
    outputs = generate_heatmaps(
        prices,
        window_size=args.window,
        step=args.step,
        output_dir=args.output,
        prefix=args.prefix,
    )
    transformer_output = None
    if args.transformer:
        matrices = [
            build_distance_heatmap(window)
            for _, window in iter_windows(prices, args.window, args.step)
        ]
        transformer_output = maybe_run_transformer(
            matrices,
            output_dir=args.transformer_dir,
            token_size=args.token_size,
            heads=args.heads,
            predict_steps=args.predict_steps,
        )
    start = format_timestamp(int(klines[0][0]))
    end = format_timestamp(int(klines[-1][0]))
    print(f"Fetched {len(klines)} klines from {start} to {end}.")
    print(f"Wrote {len(outputs)} heatmap images to {args.output}.")
    if args.transformer:
        if transformer_output:
            print(f"Transformer embeddings saved to {transformer_output}.")
        else:
            print("Transformer skipped (NumPy not installed).")


if __name__ == "__main__":
    main()
