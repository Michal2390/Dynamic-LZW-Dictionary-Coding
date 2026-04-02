"""
pgm_io.py – parser plików PGM (format binarny P5).

Używany TYLKO do analizy (histogram, entropia).
Koder/dekoder operuje na pełnym strumieniu bajtów pliku.
"""


def read_pgm(path: str):
    """
    Wczytuje plik PGM (P5).
    Zwraca: (header_bytes, pixel_bytes, width, height, maxval)
    """
    with open(path, "rb") as f:
        raw = f.read()

    pos = 0

    def read_token():
        nonlocal pos
        # pomiń białe znaki i komentarze
        while pos < len(raw):
            if raw[pos:pos+1] == b"#":
                while pos < len(raw) and raw[pos:pos+1] != b"\n":
                    pos += 1
            elif raw[pos:pos+1] in (b" ", b"\t", b"\n", b"\r"):
                pos += 1
            else:
                break
        start = pos
        while pos < len(raw) and raw[pos:pos+1] not in (b" ", b"\t", b"\n", b"\r"):
            pos += 1
        return raw[start:pos].decode("ascii")

    magic = read_token()
    if magic != "P5":
        raise ValueError(f"Nieobsługiwany format PGM: {magic} (oczekiwano P5)")

    width = int(read_token())
    height = int(read_token())
    maxval = int(read_token())

    # po maxval jest dokładnie jeden biały znak (separator), potem dane
    pos += 1  # pomijamy jeden znak separatora

    header_bytes = raw[:pos]
    pixel_bytes = raw[pos:]

    expected = width * height * (2 if maxval > 255 else 1)
    if len(pixel_bytes) != expected:
        raise ValueError(
            f"Nieoczekiwana liczba bajtów pikseli: {len(pixel_bytes)} "
            f"(oczekiwano {expected})"
        )

    return header_bytes, pixel_bytes, width, height, maxval


def pixel_bytes_from_file(path: str) -> bytes:
    """Skrót: zwraca tylko bajty pikseli (do analizy)."""
    _, pixel_bytes, _, _, _ = read_pgm(path)
    return pixel_bytes

