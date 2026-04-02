"""
decoder.py – dekoder LZW/LZ78 (aplikacja CLI).

Użycie:
  python decoder.py -i <plik_skompresowany> -o <plik_wyjściowy> [--verbose]

Odczytuje nagłówek pliku i automatycznie dobiera algorytm.
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
HEADER_SIZE = 16   # magic(4) + version(1) + codec(1) + flags(1) + max_bits(1) + orig_size(8)


def parse_header(data: bytes):
    """
    Parsuje nagłówek pliku skompresowanego.
    Zwraca: (codec, flags, max_bits, orig_size)
    """
    if len(data) < HEADER_SIZE:
        raise ValueError("Plik jest za krótki – uszkodzony nagłówek.")

    magic = data[:4]
    if magic == MAGIC_LZW:
        codec = "lzw"
    elif magic == MAGIC_LZ78:
        codec = "lz78"
    else:
        raise ValueError(f"Nieznany format pliku (magic: {magic!r})")

    version, codec_byte, flags, max_bits = struct.unpack_from("BBBB", data, 4)
    orig_size = struct.unpack_from(">q", data, 8)[0]

    if version != 0x01:
        raise ValueError(f"Nieobsługiwana wersja formatu: {version}")

    return codec, flags, max_bits, orig_size


def main():
    parser = argparse.ArgumentParser(
        description="Dekoder LZW/LZ78 – dekompresja pliku"
    )
    parser.add_argument("-i", "--input",  required=True, help="Plik skompresowany")
    parser.add_argument("-o", "--output", required=True, help="Plik wyjściowy")
    parser.add_argument(
        "--verbose", action="store_true",
        help="Wypisz statystyki dekompresji"
    )
    args = parser.parse_args()

    # Wczytaj plik skompresowany
    try:
        with open(args.input, "rb") as f:
            raw = f.read()
    except OSError as e:
        print(f"Błąd: nie można otworzyć pliku '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    # Parsuj nagłówek
    try:
        codec, flags, max_bits, orig_size = parse_header(raw)
    except ValueError as e:
        print(f"Błąd nagłówka: {e}", file=sys.stderr)
        sys.exit(1)

    compressed = raw[HEADER_SIZE:]
    t_start = time.perf_counter()

    # Jeśli była post-kompresja Huffmana, najpierw zdekoduj
    if flags & 0x01:
        try:
            compressed = huffman.decode(compressed)
        except Exception as e:
            print(f"Błąd dekodowania Huffmana: {e}", file=sys.stderr)
            sys.exit(1)

    # Właściwa dekompresja
    try:
        if codec == "lzw":
            data = lzw_core.decode(compressed, max_bits=max_bits)
        else:
            data = lz78_core.decode(compressed, orig_size=orig_size, max_bits=max_bits)
    except Exception as e:
        print(f"Błąd dekompresji {codec.upper()}: {e}", file=sys.stderr)
        sys.exit(1)

    t_end = time.perf_counter()

    # Weryfikacja rozmiaru
    if len(data) != orig_size:
        print(
            f"Ostrzeżenie: rozmiar odtworzonego pliku ({len(data)} B) "
            f"różni się od oczekiwanego ({orig_size} B).",
            file=sys.stderr
        )

    # Zapis pliku
    try:
        with open(args.output, "wb") as f:
            f.write(data)
    except OSError as e:
        print(f"Błąd: nie można zapisać pliku '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    # Statystyki
    if args.verbose or True:
        in_size = len(raw)
        ratio = orig_size / in_size if in_size else float("inf")
        print(f"[decoder] Plik:          {args.input}")
        print(f"[decoder] Algorytm:      {codec.upper()}"
              + (" + Huffman" if flags & 0x01 else ""))
        print(f"[decoder] Rozmiar komp.: {in_size:>10} B")
        print(f"[decoder] Rozmiar odtw.: {orig_size:>10} B")
        print(f"[decoder] Współczynnik:  {ratio:.4f}x")
        print(f"[decoder] Czas:          {t_end - t_start:.3f} s")
        print(f"[decoder] Zapisano do:   {args.output}")


if __name__ == "__main__":
    main()

