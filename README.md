# Dynamic LZW Dictionary Coding

Python implementation of **LZW** and **LZ78** dynamic dictionary compression algorithms with entropy analysis, benchmarking, and optional Huffman post-compression.

> Warsaw University of Technology – Data Compression (KODA) course project, 2025/2026

---

## Features

- **LZW encoder/decoder** – variable-width codes (9 → `max_bits`), dictionary reset on overflow
- **LZ78 encoder/decoder** – empty dictionary initialization, `(index, byte)` output pairs
- **Huffman post-compression** – optional second pass on LZW output (`--post-huffman`)
- **Entropy analysis** – H1, H2, H3 (block entropy), H_Markov order 1 & 2
- **Benchmarking** – automated tests on all provided datasets with CSV/Markdown reports and PNG plots
- **PGM support** – reads binary PGM (P5) test files directly

---

## Project Structure

```
├── encoder.py          # CLI encoder (LZW / LZ78)
├── decoder.py          # CLI decoder (LZW / LZ78)
├── lzw_core.py         # LZW algorithm core (BitWriter / BitReader)
├── lz78_core.py        # LZ78 algorithm core
├── huffman.py          # Huffman entropy coder (post-compression)
├── pgm_io.py           # PGM file parser (analysis only)
├── analysis.py         # Entropy, histogram, compression stats
├── benchmark.py        # Full benchmark runner
├── requirements.txt
├── obrazy_testowe/     # 6 natural test images (512×512 PGM)
├── rozklady_testowe/   # 10 synthetic distribution files (512×512 PGM)
└── data_text/          # Text test data (Pan Tadeusz)
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

### Encoding
```bash
# LZW (default)
python encoder.py -i obrazy_testowe/lena.pgm -o lena.lzw

# LZ78
python encoder.py -i obrazy_testowe/lena.pgm -o lena.lz78 --codec lz78

# LZW + Huffman post-compression
python encoder.py -i obrazy_testowe/lena.pgm -o lena.lzw --post-huffman

# Custom max dictionary bits (default: 16)
python encoder.py -i input.bin -o output.lzw --max-bits 12
```

### Decoding
```bash
python decoder.py -i lena.lzw -o lena_restored.pgm
```

### Benchmarks
```bash
# Full benchmark (all 17 files)
python benchmark.py

# Skip plots / histograms
python benchmark.py --no-plots --no-histograms

# Custom output directory
python benchmark.py --output-dir results/
```

Results are saved to `wyniki/`:
- `tabela_wyniki.csv` – full results table
- `tabela_wyniki.md` – Markdown report
- `histogramy/*.png` – per-file histograms
- `wykresy/*.png` – CR and bpp comparison charts

---

## Compressed File Format

| Offset | Size | Description |
|--------|------|-------------|
| 0–3    | 4 B  | Magic: `LZW\x00` or `LZ78` |
| 4      | 1 B  | Version (`0x01`) |
| 5      | 1 B  | Codec: `0x00`=LZW, `0x01`=LZ78 |
| 6      | 1 B  | Flags: bit0 = Huffman post-compression |
| 7      | 1 B  | `max_bits` |
| 8–15   | 8 B  | Original file size (`uint64` big-endian) |
| 16+    | –    | Compressed bitstream |

---

## Test Data

| Folder | Files | Description |
|--------|-------|-------------|
| `rozklady_testowe/` | `uniform`, `normal_*`, `geometr_*`, `laplace_*` | Synthetic 512×512 distributions |
| `obrazy_testowe/` | `lena`, `barbara`, `boat`, `peppers`, `mandril`, `chronometer` | Natural grayscale images 512×512 |
| `data_text/` | `pan_tadeusz.txt` | Polish literary text (~494 KB) |

