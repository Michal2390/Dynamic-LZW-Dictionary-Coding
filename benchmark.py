"""
benchmark.py – automatyczne testy wszystkich plików i generowanie raportów.

Uruchomienie:
  python benchmark.py [--output-dir wyniki] [--no-plots]

Testuje:
  - 10 plików z rozklady_testowe/
  - 6 plików z obrazy_testowe/
  - plik data_text/pan_tadeusz.txt
  
  Dla każdego pliku:
    - LZW (max_bits=12 i 16)
    - LZ78 (max_bits=12 i 16)
    - LZW + post-Huffman
    - Entropia H1, H2, H3, H_Markov1, H_Markov2

Wyjście:
  - wyniki/tabela_wyniki.txt    (tabela Markdown)
  - wyniki/tabela_wyniki.csv    (CSV)
  - wyniki/wykresy/*.png        (histogramy + wykresy porównawcze)
"""

import argparse
import csv
import struct
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import analysis
import lzw_core
import lz78_core
import huffman
from pgm_io import pixel_bytes_from_file


# ---------------------------------------------------------------------------
# Konfiguracja plików testowych
# ---------------------------------------------------------------------------

BASE = Path(__file__).parent

ROZKLADY = sorted(BASE.glob("rozklady_testowe/*.pgm"))
OBRAZY   = sorted(BASE.glob("obrazy_testowe/*.pgm"))
TEXT_FILES = [BASE / "data_text" / "pan_tadeusz.txt"]

ALL_FILES = list(ROZKLADY) + list(OBRAZY) + [f for f in TEXT_FILES if f.exists()]


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------

def load_file_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def load_pixel_bytes(path: Path) -> bytes:
    """Bajty pikseli (bez nagłówka PGM) – do analizy entropii."""
    if path.suffix.lower() == ".pgm":
        return pixel_bytes_from_file(str(path))
    else:
        return load_file_bytes(path)


def compress_lzw(data: bytes, max_bits: int) -> tuple[bytes, float]:
    t0 = time.perf_counter()
    compressed = lzw_core.encode(data, max_bits=max_bits)
    # dodaj nagłówek (16 bajtów)
    header = b"LZW\x00" + struct.pack("BBBBq", 1, 0, 0, max_bits, len(data))
    return header + compressed, time.perf_counter() - t0


def compress_lz78(data: bytes, max_bits: int) -> tuple[bytes, float]:
    t0 = time.perf_counter()
    compressed = lz78_core.encode(data, max_bits=max_bits)
    header = b"LZ78" + struct.pack("BBBBq", 1, 1, 0, max_bits, len(data))
    return header + compressed, time.perf_counter() - t0


def compress_lzw_huffman(data: bytes, max_bits: int) -> tuple[bytes, float]:
    t0 = time.perf_counter()
    lzw_bytes = lzw_core.encode(data, max_bits=max_bits)
    huff_bytes = huffman.encode(lzw_bytes)
    header = b"LZW\x00" + struct.pack("BBBBq", 1, 0, 1, max_bits, len(data))
    return header + huff_bytes, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Benchmark pojedynczego pliku
# ---------------------------------------------------------------------------

def benchmark_file(path: Path) -> dict:
    file_bytes = load_file_bytes(path)
    pixel_bytes = load_pixel_bytes(path)   # do analizy entropii
    orig_size = len(file_bytes)
    name = path.name

    print(f"  → {name} ({orig_size / 1024:.1f} KB)", flush=True)

    # --- Analiza entropii ---
    print("     Entropia...", end=" ", flush=True)
    h1 = analysis.entropy_h1(pixel_bytes)
    h2 = analysis.entropy_block(pixel_bytes, 2)
    h3 = analysis.entropy_block(pixel_bytes, 3)

    # Markow – tylko dla plików < 1 MB (kosztowna operacja)
    if len(pixel_bytes) <= 1_000_000:
        hm1 = analysis.entropy_markov(pixel_bytes, 1)
        hm2 = analysis.entropy_markov(pixel_bytes, 2)
    else:
        # dla dużych plików użyj próbki
        sample = pixel_bytes[:500_000]
        hm1 = analysis.entropy_markov(sample, 1)
        hm2 = analysis.entropy_markov(sample, 2)
    print("OK")

    results = {
        "name":        name,
        "group":       _group(path),
        "orig_bytes":  orig_size,
        "H1":          h1,
        "H2":          h2,
        "H3":          h3,
        "H_markov1":   hm1,
        "H_markov2":   hm2,
    }

    # --- Kompresja ---
    for label, fn, mb in [
        ("LZW-12",       compress_lzw,         12),
        ("LZW-16",       compress_lzw,         16),
        ("LZ78-12",      compress_lz78,        12),
        ("LZ78-16",      compress_lz78,        16),
        ("LZW16+Huff",   compress_lzw_huffman, 16),
    ]:
        print(f"     {label}...", end=" ", flush=True)
        try:
            comp_data, elapsed = fn(file_bytes, mb)
            comp_size = len(comp_data)
            cr  = analysis.compression_ratio(orig_size, comp_size)
            bpp = analysis.avg_code_length(orig_size, comp_size)
            results[f"{label}_bytes"] = comp_size
            results[f"{label}_CR"]    = cr
            results[f"{label}_bpp"]   = bpp
            results[f"{label}_time"]  = elapsed
            print(f"CR={cr:.3f}x  bpp={bpp:.3f}")
        except Exception as e:
            print(f"BŁĄD: {e}")
            results[f"{label}_bytes"] = None
            results[f"{label}_CR"]    = None
            results[f"{label}_bpp"]   = None
            results[f"{label}_time"]  = None

    return results


def _group(path: Path) -> str:
    p = str(path)
    if "rozklady" in p:
        return "rozklady"
    elif "obrazy" in p:
        return "obrazy"
    else:
        return "tekst"


# ---------------------------------------------------------------------------
# Wykresy
# ---------------------------------------------------------------------------

def save_histograms(all_results, output_dir: Path):
    """Zapisuje histogramy dla wszystkich plików."""
    hist_dir = output_dir / "histogramy"
    hist_dir.mkdir(parents=True, exist_ok=True)
    for path in ALL_FILES:
        try:
            pixel_bytes = load_pixel_bytes(path)
            title = f"Histogram – {path.name}"
            save_path = str(hist_dir / (path.stem + "_hist.png"))
            analysis.plot_histogram(pixel_bytes, title=title, save_path=save_path)
        except Exception as e:
            print(f"  Błąd histogramu {path.name}: {e}")


def save_comparison_plots(all_results: list, output_dir: Path):
    """Wykresy porównawcze CR i bpp vs entropia."""
    plots_dir = output_dir / "wykresy"
    plots_dir.mkdir(parents=True, exist_ok=True)

    algos = ["LZW-12", "LZW-16", "LZ78-12", "LZ78-16", "LZW16+Huff"]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for group_name, group_label in [("rozklady", "Rozkłady syntetyczne"),
                                     ("obrazy",   "Obrazy naturalne"),
                                     ("tekst",    "Dane tekstowe")]:
        group = [r for r in all_results if r.get("group") == group_name]
        if not group:
            continue
        names = [r["name"] for r in group]
        x = np.arange(len(names))

        # --- Wykres CR ---
        fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 5))
        w = 0.15
        for i, (algo, color) in enumerate(zip(algos, colors)):
            vals = [r.get(f"{algo}_CR") or 0 for r in group]
            ax.bar(x + i * w, vals, w, label=algo, color=color)
        ax.set_xticks(x + w * 2)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Współczynnik kompresji (CR)")
        ax.set_title(f"Porównanie CR – {group_label}")
        ax.legend(fontsize=8)
        ax.axhline(1.0, color="k", linewidth=0.8, linestyle="--", label="CR=1")
        fig.tight_layout()
        fig.savefig(str(plots_dir / f"CR_{group_name}.png"), dpi=100)
        plt.close(fig)

        # --- Wykres bpp vs H1 ---
        fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 5))
        h1_vals = [r["H1"] for r in group]
        ax.plot(names, h1_vals, "k--o", label="H1 (entropia)", linewidth=1.5)
        for i, (algo, color) in enumerate(zip(algos, colors)):
            vals = [r.get(f"{algo}_bpp") or 0 for r in group]
            ax.plot(names, vals, "o-", label=algo, color=color, markersize=4)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Średnia długość kodu [bit/symbol]")
        ax.set_title(f"bpp vs entropia H1 – {group_label}")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(str(plots_dir / f"bpp_vs_H1_{group_name}.png"), dpi=100)
        plt.close(fig)

        # --- Wykres bpp vs H1/H2/H3 (tylko LZW-16) ---
        fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.2), 5))
        for metric, color, ls in [("H1", "#1f77b4", "-"),
                                    ("H2", "#ff7f0e", "--"),
                                    ("H3", "#2ca02c", ":")]:
            vals = [r[metric] for r in group]
            ax.plot(names, vals, ls + "o", label=metric, color=color, linewidth=1.5)
        bpp_lzw16 = [r.get("LZW-16_bpp") or 0 for r in group]
        ax.plot(names, bpp_lzw16, "s-", label="LZW-16 bpp", color="#d62728", linewidth=2)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("bit/symbol")
        ax.set_title(f"Entropie H1/H2/H3 vs LZW-16 – {group_label}")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(str(plots_dir / f"entropie_{group_name}.png"), dpi=100)
        plt.close(fig)

    print(f"  Wykresy zapisane w: {plots_dir}")


# ---------------------------------------------------------------------------
# Zapis tabel
# ---------------------------------------------------------------------------

CODEC_COLS = ["LZW-12", "LZW-16", "LZ78-12", "LZ78-16", "LZW16+Huff"]


def save_csv(all_results: list, path: Path):
    fieldnames = ["name", "group", "orig_bytes", "H1", "H2", "H3", "H_markov1", "H_markov2"]
    for algo in CODEC_COLS:
        fieldnames += [f"{algo}_bytes", f"{algo}_CR", f"{algo}_bpp", f"{algo}_time"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)
    print(f"  CSV zapisany: {path}")


def save_markdown(all_results: list, path: Path):
    lines = []
    lines.append("# Wyniki benchmarku LZW / LZ78\n")

    for group_name, group_label in [("rozklady", "Rozkłady syntetyczne"),
                                     ("obrazy",   "Obrazy naturalne"),
                                     ("tekst",    "Dane tekstowe")]:
        group = [r for r in all_results if r.get("group") == group_name]
        if not group:
            continue
        lines.append(f"\n## {group_label}\n")

        # tabela entropii
        lines.append("### Entropie\n")
        lines.append("| Plik | Rozmiar [B] | H1 | H2 | H3 | H_Markov1 | H_Markov2 |")
        lines.append("|------|------------|----|----|----|-----------| -----------|")
        for r in group:
            lines.append(
                f"| {r['name']} | {r['orig_bytes']} "
                f"| {r['H1']:.4f} | {r['H2']:.4f} | {r['H3']:.4f} "
                f"| {r['H_markov1']:.4f} | {r['H_markov2']:.4f} |"
            )

        # tabela kompresji
        lines.append("\n### Kompresja\n")
        header = "| Plik | " + " | ".join(
            [f"{a} CR | {a} bpp" for a in CODEC_COLS]
        ) + " |"
        sep = "|------|" + "|".join(["---|---" for _ in CODEC_COLS]) + "|"
        lines.append(header)
        lines.append(sep)
        for r in group:
            row = f"| {r['name']} |"
            for algo in CODEC_COLS:
                cr  = r.get(f"{algo}_CR")
                bpp = r.get(f"{algo}_bpp")
                cr_s  = f"{cr:.3f}" if cr is not None else "N/A"
                bpp_s = f"{bpp:.3f}" if bpp is not None else "N/A"
                row += f" {cr_s} | {bpp_s} |"
            lines.append(row)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Markdown zapisany: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Benchmark LZW/LZ78")
    parser.add_argument("--output-dir", default="wyniki", help="Katalog wyjściowy")
    parser.add_argument("--no-plots", action="store_true", help="Pomiń generowanie wykresów")
    parser.add_argument("--no-histograms", action="store_true", help="Pomiń histogramy")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ALL_FILES:
        print("Nie znaleziono żadnych plików testowych!", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  BENCHMARK LZW/LZ78 – {len(ALL_FILES)} plików")
    print(f"{'='*60}\n")

    all_results = []
    for path in ALL_FILES:
        print(f"\n[{ALL_FILES.index(path)+1}/{len(ALL_FILES)}] {path.name}")
        try:
            result = benchmark_file(path)
            all_results.append(result)
        except Exception as e:
            print(f"  BŁĄD: {e}")

    print(f"\n{'='*60}")
    print("  Zapisywanie wyników...")
    print(f"{'='*60}")

    save_csv(all_results, out_dir / "tabela_wyniki.csv")
    save_markdown(all_results, out_dir / "tabela_wyniki.md")

    if not args.no_histograms:
        print("  Histogramy...")
        save_histograms(all_results, out_dir)

    if not args.no_plots:
        print("  Wykresy porównawcze...")
        save_comparison_plots(all_results, out_dir)

    print(f"\n✓ Wszystko zapisane w: {out_dir.resolve()}\n")


if __name__ == "__main__":
    main()


