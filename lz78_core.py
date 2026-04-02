"""
lz78_core.py – rdzeń algorytmu LZ78.

Różnice względem LZW:
  - Słownik inicjalizowany PUSTYM słownikiem (brak wstępnie załadowanych symboli).
  - Wyjście: pary (index, bajt) – każda para zapisywana jest jako:
      * index: zmienna liczba bitów (rośnie wraz ze słownikiem)
      * bajt:  8 bitów
  - Brak specjalnych kodów CLEAR/END – rozmiar oryginalny przechowywany w nagłówku.
"""

from lzw_core import BitWriter, BitReader


# ---------------------------------------------------------------------------
# Koder LZ78
# ---------------------------------------------------------------------------

def encode(data: bytes, max_bits: int = 16) -> bytes:
    """
    Koduje dane algorytmem LZ78.
    Zwraca: strumień bitów (pary index+bajt) jako bytes.
    """
    if not data:
        return b""

    max_dict = (1 << max_bits) - 1

    # słownik: ciąg_bajtów → indeks (1-based; 0 = brak wpisu)
    dictionary: dict[bytes, int] = {}
    next_code = 1

    writer = BitWriter()

    # szerokość indeksu – rośnie gdy słownik się powiększa
    index_bits = 1

    w = b""

    def write_pair(idx: int, byte_val: int):
        nonlocal index_bits
        writer.write(idx, index_bits)
        writer.write(byte_val, 8)

    for byte in data:
        c = bytes([byte])
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            parent_idx = dictionary.get(w, 0)
            write_pair(parent_idx, byte)

            if next_code <= max_dict:
                dictionary[wc] = next_code
                next_code += 1
                # aktualizacja szerokości indeksu
                if next_code > (1 << index_bits):
                    index_bits += 1
            else:
                # reset słownika
                dictionary = {}
                next_code = 1
                index_bits = 1

            w = b""

    # flush pozostałości (jeśli w != "")
    if w:
        # wyślij jako sekwencję par
        temp = w
        while temp:
            parent_idx = dictionary.get(temp[:-1], 0) if len(temp) > 1 else 0
            writer.write(parent_idx, index_bits)
            writer.write(temp[-1], 8)
            temp = temp[:-1] if len(temp) > 1 else b""

    return writer.flush()


# ---------------------------------------------------------------------------
# Dekoder LZ78
# ---------------------------------------------------------------------------

def decode(data: bytes, orig_size: int, max_bits: int = 16) -> bytes:
    """
    Dekoduje strumień bitów LZ78.
    orig_size: oryginalny rozmiar danych w bajtach (potrzebny do zatrzymania).
    Zwraca: oryginalne dane jako bytes.
    """
    if not data:
        return b""

    max_dict = (1 << max_bits) - 1
    reader = BitReader(data)
    output = bytearray()

    # słownik: indeks → ciąg_bajtów (1-based)
    dictionary: dict[int, bytes] = {}
    next_code = 1
    index_bits = 1

    while len(output) < orig_size:
        try:
            idx = reader.read(index_bits)
            byte_val = reader.read(8)
        except EOFError:
            break

        byte_c = bytes([byte_val])

        if idx == 0:
            entry = byte_c
        else:
            entry = dictionary.get(idx, b"") + byte_c

        output.extend(entry)

        if next_code <= max_dict:
            dictionary[next_code] = entry
            next_code += 1
            if next_code > (1 << index_bits):
                index_bits += 1
        else:
            # reset
            dictionary = {}
            next_code = 1
            index_bits = 1

    return bytes(output[:orig_size])

