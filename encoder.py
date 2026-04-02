"""
encoder.py – koder LZW/LZ78 (aplikacja CLI).

Użycie:
  python encoder.py -i <plik_wejściowy> -o <plik_wyjściowy> [opcje]

Opcje:
  --codec   {lzw,lz78}   algorytm kompresji (domyślnie: lzw)
  --max-bits INT          maks. szerokość kodu w bitach (domyślnie: 16)
  --post-huffman          dodatkowo kompresuj wyjście Huffmanem
  --verbose               wypisz statystyki

Format pliku wyjściowego (.lzw / .lz78):
  Bajty 0-3  : magic   "LZW\\x00" lub "LZ78"
  Bajt  4    : wersja  0x01
  Bajt  5    : codec   0x00=LZW, 0x01=LZ78
  Bajt  6    : flags   bit0=huffman
  Bajt  7    : max_bits
  Bajty 8-15 : orig_size (uint64 big-endian)
  Bajty 16.. : skompresowane dane
"""

import argparse
import struct
import sys
import time

import lzw_core
import lz78_core
import huffman


MAGIC_LZW  = b"LZW\x00"
MAGIC_LZ78 = b"LZ78"
VERSION    = 0x01


def build_header(codec: str, flags: int, max_bits: int, orig_size: int) -> bytes:
    magic = MAGIC_LZW if codec == "lzw" else MAGIC_LZ78
    codec_byte = 0x00 if codec == "lzw" else 0x01
    return (
        magic
        + struct.pack("BBBBq", VERSION, codec_byte, flags, max_bits, orig_size)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Koder LZW/LZ78 – kompresja pliku"
    )
    parser.add_argument("-i", "--input",  required=True, help="Plik wejściowy")
    parser.add_argument("-o", "--output", required=True, help="Plik wyjściowy")
    parser.add_argument(
        "--codec", choices=["lzw", "lz78"], default="lzw",
        help="Algorytm kompresji (domyślnie: lzw)"
    )
    parser.add_argument(
        "--max-bits", type=int, default=16,
        help="Maks. szerokość kodu w bitach (domyślnie: 16)"
    )
    parser.add_argument(
        "--post-huffman", action="store_true",
        help="Post-kompresja wyjścia koderem Huffmana"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Wypisz statystyki kompresji"
    )
    args = parser.parse_args()

    # Wczytaj dane wejściowe
    try:
        with open(args.input, "rb") as f:
            data = f.read()
    except OSError as e:
        print(f"Błąd: nie można otworzyć pliku '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    orig_size = len(data)
    t_start = time.perf_counter()

    # Kompresja
    if args.codec == "lzw":
        compressed = lzw_core.encode(data, max_bits=args.max_bits)
    else:
        compressed = lz78_core.encode(data, max_bits=args.max_bits)

    # Opcjonalna post-kompresja Huffmanem
    flags = 0x00
    if args.post_huffman:
        compressed = huffman.encode(compressed)
        flags |= 0x01

    t_end = time.perf_counter()

    # Zapis pliku
    header = build_header(args.codec, flags, args.max_bits, orig_size)
    try:
        with open(args.output, "wb") as f:
            f.write(header)
            f.write(compressed)
    except OSError as e:
        print(f"Błąd: nie można zapisać pliku '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    # Statystyki
    out_size = len(header) + len(compressed)
    if args.verbose or True:
        ratio = orig_size / out_size if out_size else float("inf")
        bpp   = (out_size * 8) / orig_size if orig_size else 0.0
        print(f"[encoder] Plik:          {args.input}")
        print(f"[encoder] Algorytm:      {args.codec.upper()}"
              + (" + Huffman" if args.post_huffman else ""))
        print(f"[encoder] Rozmiar oryg.: {orig_size:>10} B")
        print(f"[encoder] Rozmiar komp.: {out_size:>10} B")
        print(f"[encoder] Współczynnik:  {ratio:.4f}x")
        print(f"[encoder] Śr. dł. kodu:  {bpp:.4f} bpp")
        print(f"[encoder] Czas:          {t_end - t_start:.3f} s")
        print(f"[encoder] Zapisano do:   {args.output}")


if __name__ == "__main__":
    main()

