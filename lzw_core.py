"""
lzw_core.py – rdzeń algorytmu LZW z kodami zmiennej długości.

Algorytm:
  - Słownik inicjalizowany 256 symbolami jednobajtowymi (kody 0–255).
  - Kody startują od (init_bits) bitów i rosną do max_bits.
  - Gdy słownik jest pełny – reset do stanu inicjalnego (clear code).
  - Specjalne kody: CLEAR_CODE = 256, END_CODE = 257.

Format strumienia kodów (używany przez encoder/decoder przez BitStream):
  CLEAR_CODE | dane... | END_CODE
"""

CLEAR_CODE = 256
END_CODE = 257
FIRST_CODE = 258  # pierwszy wolny kod po inicjalizacji


class BitWriter:
    """Zapisuje kody o zmiennej liczbie bitów do bufora bajtowego."""

    def __init__(self):
        self._buf = 0
        self._buf_len = 0
        self._output = bytearray()

    def write(self, code: int, n_bits: int):
        self._buf |= code << self._buf_len
        self._buf_len += n_bits
        while self._buf_len >= 8:
            self._output.append(self._buf & 0xFF)
            self._buf >>= 8
            self._buf_len -= 8

    def flush(self) -> bytes:
        if self._buf_len > 0:
            self._output.append(self._buf & 0xFF)
            self._buf = 0
            self._buf_len = 0
        return bytes(self._output)


class BitReader:
    """Odczytuje kody o zmiennej liczbie bitów z bufora bajtowego."""

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0       # pozycja w bajtach
        self._buf = 0
        self._buf_len = 0

    def read(self, n_bits: int) -> int:
        while self._buf_len < n_bits:
            if self._pos >= len(self._data):
                raise EOFError("Koniec danych bitstreamu")
            self._buf |= self._data[self._pos] << self._buf_len
            self._buf_len += 8
            self._pos += 1
        code = self._buf & ((1 << n_bits) - 1)
        self._buf >>= n_bits
        self._buf_len -= n_bits
        return code

    def has_data(self) -> bool:
        return self._pos < len(self._data) or self._buf_len > 0


# ---------------------------------------------------------------------------
# Koder LZW
# ---------------------------------------------------------------------------

def encode(data: bytes, max_bits: int = 16) -> bytes:
    """
    Koduje dane algorytmem LZW z kodami zmiennej długości.
    Zwraca: strumień bitów jako bytes.
    """
    if max_bits < 9 or max_bits > 24:
        raise ValueError("max_bits musi być w zakresie 9–24")

    max_code = (1 << max_bits) - 1

    def _init_dict():
        return {bytes([i]): i for i in range(256)}

    dictionary = _init_dict()
    next_code = FIRST_CODE
    code_width = 9

    writer = BitWriter()
    # wyślij CLEAR na początku
    writer.write(CLEAR_CODE, code_width)

    if not data:
        writer.write(END_CODE, code_width)
        return writer.flush()

    w = bytes([data[0]])

    for byte in data[1:]:
        c = bytes([byte])
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            writer.write(dictionary[w], code_width)

            if next_code <= max_code:
                dictionary[wc] = next_code
                next_code += 1
                # zwiększ szerokość kodu gdy przekroczymy 2^code_width
                if next_code > (1 << code_width) and code_width < max_bits:
                    code_width += 1
            else:
                # reset słownika
                writer.write(CLEAR_CODE, code_width)
                dictionary = _init_dict()
                next_code = FIRST_CODE
                code_width = 9

            w = c

    # wyślij ostatni kod
    writer.write(dictionary[w], code_width)
    writer.write(END_CODE, code_width)
    return writer.flush()


# ---------------------------------------------------------------------------
# Dekoder LZW
# ---------------------------------------------------------------------------

def decode(data: bytes, max_bits: int = 16) -> bytes:
    """
    Dekoduje strumień bitów LZW.
    Zwraca: oryginalne dane jako bytes.
    """
    if max_bits < 9 or max_bits > 24:
        raise ValueError("max_bits musi być w zakresie 9–24")

    reader = BitReader(data)
    output = bytearray()

    def _init_dict():
        return {i: bytes([i]) for i in range(256)}

    code_width = 9
    dictionary = _init_dict()
    next_code = FIRST_CODE

    # oczekuj CLEAR na początku
    first = reader.read(code_width)
    if first != CLEAR_CODE:
        raise ValueError(f"Oczekiwano CLEAR_CODE na początku, got {first}")

    # pierwszy kod po CLEAR
    try:
        code = reader.read(code_width)
    except EOFError:
        return bytes(output)

    if code == END_CODE:
        return bytes(output)

    entry = dictionary[code]
    output.extend(entry)
    prev = entry

    while True:
        try:
            code = reader.read(code_width)
        except EOFError:
            break

        if code == END_CODE:
            break

        if code == CLEAR_CODE:
            dictionary = _init_dict()
            next_code = FIRST_CODE
            code_width = 9
            try:
                code = reader.read(code_width)
            except EOFError:
                break
            if code == END_CODE:
                break
            entry = dictionary[code]
            output.extend(entry)
            prev = entry
            continue

        if code in dictionary:
            entry = dictionary[code]
        elif code == next_code:
            # specjalny przypadek: kod jeszcze nie w słowniku
            entry = prev + bytes([prev[0]])
        else:
            raise ValueError(f"Nieznany kod: {code} (next_code={next_code})")

        output.extend(entry)

        if next_code <= (1 << max_bits) - 1:
            dictionary[next_code] = prev + bytes([entry[0]])
            next_code += 1
            if next_code > (1 << code_width) and code_width < max_bits:
                code_width += 1

        prev = entry

    return bytes(output)


