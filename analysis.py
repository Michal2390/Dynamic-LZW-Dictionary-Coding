"""
analysis.py – obliczanie histogramów, entropii i statystyk kompresji.

Funkcje:
  histogram(data)          → dict {bajt: liczba_wystąpień}
  entropy_h1(data)         → entropia rzędu 1 [bit/symbol]
  entropy_block(data, n)   → entropia źródła blokowego rzędu n [bit/symbol]
  entropy_markov(data, k)  → entropia źródła Markowa stopnia k [bit/symbol]
  avg_code_length(orig, compressed)  → średnia długość kodu [bit/symbol]
  compression_ratio(orig, compressed)→ współczynnik kompresji
  plot_histogram(data, title, path)  → zapis histogramu do pliku PNG
"""

import math
import os
from collections import Counter
from typing import Optional

import numpy as np
import matplotlib
matplotlib.use("Agg")   # bez GUI – zapis do pliku
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

def histogram(data: bytes) -> dict:
    """Zwraca słownik {wartość_bajtu: liczba_wystąpień}."""
    return dict(Counter(data))


# ---------------------------------------------------------------------------
# Entropia rzędu 1 (H1)
# ---------------------------------------------------------------------------

def entropy_h1(data: bytes) -> float:
    """
    Oblicza entropię H1 (empiryczną entropię rzędu 1) w bit/symbol.
    H1 = -Σ p(x) * log2(p(x))
    """
    n = len(data)
    if n == 0:
        return 0.0
    counts = np.frombuffer(data, dtype=np.uint8)
    _, freqs = np.unique(counts, return_counts=True)
    probs = freqs / n
    return float(-np.sum(probs * np.log2(probs)))


# ---------------------------------------------------------------------------
# Entropia blokowa rzędu n (Hn)
# ---------------------------------------------------------------------------

def entropy_block(data: bytes, n: int) -> float:
    """
    Oblicza entropię blokową rzędu n w bit/symbol.
    Dzieli dane na bloki n-elementowe i liczy entropię bloków,
    normalizując do jednego symbolu: H_n / n.
    """
    if n < 1:
        raise ValueError("n musi być >= 1")
    if len(data) < n:
        return 0.0

    # Tworzymy bloki przesuwnym oknem (overlapping n-grams)
    blocks = [data[i:i + n] for i in range(len(data) - n + 1)]
    counter = Counter(blocks)
    total = len(blocks)
    probs = np.array([v / total for v in counter.values()])
    h_n = float(-np.sum(probs * np.log2(probs)))
    return h_n / n   # normalizacja do bit/symbol


# ---------------------------------------------------------------------------
# Entropia Markowa stopnia k
# ---------------------------------------------------------------------------

def entropy_markov(data: bytes, k: int) -> float:
    """
    Oblicza warunkową entropię Markowa stopnia k w bit/symbol.
    H_Markov(k) = -Σ_{ctx} p(ctx) * Σ_{x} p(x|ctx) * log2(p(x|ctx))
    """
    if k < 1:
        raise ValueError("k musi być >= 1")
    if len(data) <= k:
        return 0.0

    # Zlicz konteksty i przejścia
    ctx_counts: Counter = Counter()
    pair_counts: Counter = Counter()

    for i in range(len(data) - k):
        ctx = data[i:i + k]
        nxt = data[i + k]
        ctx_counts[ctx] += 1
        pair_counts[(ctx, nxt)] += 1

    total_ctx = sum(ctx_counts.values())
    h = 0.0
    for ctx, ctx_count in ctx_counts.items():
        p_ctx = ctx_count / total_ctx
        for nxt in range(256):
            pair_count = pair_counts.get((ctx, nxt), 0)
            if pair_count > 0:
                p_cond = pair_count / ctx_count
                h -= p_ctx * p_cond * math.log2(p_cond)
    return h


# ---------------------------------------------------------------------------
# Statystyki kompresji
# ---------------------------------------------------------------------------

def avg_code_length(orig_size_bytes: int, compressed_size_bytes: int) -> float:
    """Średnia długość kodu w bit/symbol (bajt wejściowy = 1 symbol)."""
    if orig_size_bytes == 0:
        return 0.0
    return (compressed_size_bytes * 8) / orig_size_bytes


def compression_ratio(orig_size_bytes: int, compressed_size_bytes: int) -> float:
    """Współczynnik kompresji: orig / compressed."""
    if compressed_size_bytes == 0:
        return float("inf")
    return orig_size_bytes / compressed_size_bytes


# ---------------------------------------------------------------------------
# Rysowanie histogramów
# ---------------------------------------------------------------------------

def plot_histogram(
    data: bytes,
    title: str = "Histogram",
    save_path: Optional[str] = None,
    show: bool = False,
) -> None:
    """
    Rysuje histogram intensywności pikseli (0–255) i opcjonalnie zapisuje do PNG.
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    counts = np.bincount(arr, minlength=256)

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(np.arange(256), counts, width=1.0, color="steelblue", edgecolor="none")
    ax.set_xlabel("Wartość bajtu")
    ax.set_ylabel("Liczba wystąpień")
    ax.set_title(title)
    ax.set_xlim(-1, 256)
    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
        fig.savefig(save_path, dpi=100)
    if show:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# Zbiorczy raport dla jednego pliku
# ---------------------------------------------------------------------------

def full_report(data: bytes, name: str = "") -> dict:
    """
    Oblicza wszystkie metryki analizy dla danych wejściowych.
    Zwraca słownik z wynikami.
    """
    return {
        "name":         name,
        "size_bytes":   len(data),
        "H1":           entropy_h1(data),
        "H2":           entropy_block(data, 2),
        "H3":           entropy_block(data, 3),
        "H_markov1":    entropy_markov(data, 1),
        "H_markov2":    entropy_markov(data, 2),
    }

