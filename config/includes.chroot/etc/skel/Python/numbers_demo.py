#!/usr/bin/env python3
"""Number crunching with numpy (pre-installed)."""
import numpy as np

rng = np.random.default_rng(42)
rolls = rng.integers(1, 7, size=(100_000, 2)).sum(axis=1)
values, counts = np.unique(rolls, return_counts=True)
print("Rolling two dice 100,000 times:\n")
for v, c in zip(values, counts):
    print(f"{v:>2} | {'█' * (c // 400)} {c / len(rolls):.1%}")
print(f"\nAverage: {rolls.mean():.3f} (theory says 7)")
