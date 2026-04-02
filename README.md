<div align="center">

# 🗜️ Dynamic LZW Dictionary Coding

**Python implementation of LZW & LZ78 dynamic dictionary compression algorithms**  
with entropy analysis, benchmarking, and optional Huffman post-compression.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)](https://numpy.org/)
[![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=for-the-badge&logo=matplotlib&logoColor=white)](https://matplotlib.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> 🎓 Warsaw University of Technology – Data Compression (KODA) course project, 2025/2026

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔵 **LZW Encoder/Decoder** | Variable-width codes (9 → `max_bits`), dictionary reset on overflow |
| 🟢 **LZ78 Encoder/Decoder** | Empty dictionary initialization, `(index, byte)` output pairs |
| 🟠 **Huffman Post-compression** | Optional second pass on LZW output (`--post-huffman`) |
| 📊 **Entropy Analysis** | H1, H2, H3 (block entropy), H_Markov order 1 & 2 |
| 📈 **Benchmarking** | Automated tests on all datasets with CSV/Markdown reports and PNG plots |
| 🖼️ **PGM Support** | Reads binary PGM (P5) test images directly |

---

## 📁 Project Structure

```
📦 Dynamic-LZW-Dictionary-Coding
 ├── 🔐 encoder.py            # CLI encoder (LZW / LZ78)
 ├── 🔓 decoder.py            # CLI decoder (LZW / LZ78)
 ├── ⚙️  lzw_core.py          # LZW algorithm core (BitWriter / BitReader)
 ├── ⚙️  lz78_core.py         # LZ78 algorithm core
 ├── 🌳 huffman.py            # Huffman entropy coder (post-compression)
 ├── 🖼️  pgm_io.py            # PGM file parser (analysis only)
 ├── 📊 analysis.py           # Entropy, histogram, compression stats
 ├── 🏁 benchmark.py          # Full benchmark runner
 ├── 📋 requirements.txt
 ├── 🖼️  obrazy_testowe/      # 6 natural test images (512×512 PGM)
 ├── 📉 rozklady_testowe/     # 10 synthetic distribution files (512×512 PGM)
 └── 📝 data_text/            # Text test data (Pan Tadeusz)
```

---

## 🚀 Installation

```bash
git clone https://github.com/Michal2390/Dynamic-LZW-Dictionary-Coding.git
cd Dynamic-LZW-Dictionary-Coding
pip install -r requirements.txt
```

---

## 🛠️ Usage

### 🔐 Encoding

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

### 🔓 Decoding

```bash
python decoder.py -i lena.lzw -o lena_restored.pgm
```

### 🏁 Benchmarks

```bash
# Full benchmark (all 17 files)
python benchmark.py

# Skip plots / histograms
python benchmark.py --no-plots --no-histograms

# Custom output directory
python benchmark.py --output-dir results/
```

> 📂 Results are saved to `wyniki/`:
> - `tabela_wyniki.csv` – full results table
> - `tabela_wyniki.md` – Markdown report
> - `histogramy/*.png` – per-file histograms
> - `wykresy/*.png` – CR and bpp comparison charts

---

## 📦 Compressed File Format

> Every `.lzw` / `.lz78` file starts with a **16-byte binary header**:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0–3 | 4 B | Magic | `LZW\x00` or `LZ78` |
| 4 | 1 B | Version | `0x01` |
| 5 | 1 B | Codec | `0x00` = LZW, `0x01` = LZ78 |
| 6 | 1 B | Flags | bit0 = Huffman post-compression |
| 7 | 1 B | `max_bits` | Max code width in bits |
| 8–15 | 8 B | `orig_size` | Original file size (`uint64` big-endian) |
| 16+ | – | Bitstream | Compressed data |

---

## 🧪 Test Data

| Folder | Files | Description |
|--------|-------|-------------|
| 📉 `rozklady_testowe/` | `uniform`, `normal_10/30/50`, `geometr_05/09/099`, `laplace_10/20/30` | Synthetic 512×512 grayscale distributions |
| 🖼️ `obrazy_testowe/` | `lena`, `barbara`, `boat`, `peppers`, `mandril`, `chronometer` | Natural grayscale images 512×512 |
| 📝 `data_text/` | `pan_tadeusz.txt` | Polish literary text (~494 KB) |

---

## 🔬 Algorithms Overview

<details>
<summary><b>📘 LZW (Lempel–Ziv–Welch)</b></summary>

- Dictionary pre-initialized with all 256 single-byte symbols
- Codes grow from **9 bits** up to `max_bits` as the dictionary expands
- Special codes: `CLEAR` (256) resets the dictionary, `END` (257) marks end of stream
- On dictionary overflow → automatic reset and restart

</details>

<details>
<summary><b>📗 LZ78 (Lempel–Ziv 1978)</b></summary>

- Dictionary starts **empty** (key difference from LZW)
- Output format: pairs of `(parent_index, byte)` instead of plain indices
- Index bit-width grows dynamically with the dictionary size
- On dictionary overflow → automatic reset

</details>

<details>
<summary><b>📙 Huffman Post-compression</b></summary>

- Applied to the raw LZW bitstream bytes for additional entropy coding
- Code table serialized in the output header for self-contained decoding
- Activated via `--post-huffman` flag in the encoder

</details>

---

<div align="center">

Made with ❤️ at **Warsaw University of Technology**

</div>
