"""
huffman.py – koder/dekoder Huffmana używany jako post-kompresja na wyjściu LZW.

Operuje na bajtach (symbole 0–255).
Format skompresowanego strumienia:
  [4 bajty: rozmiar oryginalny uint32]
  [2 bajty: liczba symboli w tablicy N uint16]
  N × [1 bajt: symbol, 1 bajt: długość kodu, ceil(dlugosc/8) bajtów: kod]
  [dane bitowe – kody Huffmana]
"""

import heapq
import struct
from collections import Counter
from lzw_core import BitWriter, BitReader


# ---------------------------------------------------------------------------
# Budowa drzewa Huffmana
# ---------------------------------------------------------------------------

class _Node:
    __slots__ = ("freq", "symbol", "left", "right")

    def __init__(self, freq: int, symbol: int = -1, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


def _build_tree(data: bytes):
    freq = Counter(data)
    if len(freq) == 0:
        return None, {}
    if len(freq) == 1:
        sym = next(iter(freq))
        root = _Node(freq[sym], sym)
        return root, {sym: (1, 0b0)}   # kod jednobitowy "0"

    heap = [_Node(f, s) for s, f in freq.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, _Node(a.freq + b.freq, -1, a, b))
    root = heap[0]

    # generowanie kodów
    codes: dict[int, tuple[int, int]] = {}  # symbol → (długość, wartość)

    def _traverse(node, length, value):
        if node.symbol >= 0:
            codes[node.symbol] = (length, value)
            return
        _traverse(node.left, length + 1, value << 1)
        _traverse(node.right, length + 1, (value << 1) | 1)

    _traverse(root, 0, 0)
    return root, codes


# ---------------------------------------------------------------------------
# Koder Huffmana
# ---------------------------------------------------------------------------

def encode(data: bytes) -> bytes:
    """
    Kompresuje dane Huffmanem.
    Zwraca skompresowany strumień wraz z nagłówkiem (tablica kodów).
    """
    if not data:
        return struct.pack(">IH", 0, 0)

    _, codes = _build_tree(data)

    # nagłówek: rozmiar oryginalny + tablica kodów
    header = bytearray()
    header += struct.pack(">I", len(data))           # 4 bajty: rozmiar oryg.
    header += struct.pack(">H", len(codes))          # 2 bajty: liczba symboli

    for sym, (length, value) in sorted(codes.items()):
        n_bytes = (length + 7) // 8
        header.append(sym)                           # 1 bajt: symbol
        header.append(length)                        # 1 bajt: długość kodu
        header += value.to_bytes(n_bytes, "big")     # kod (MSB first)

    # dane
    writer = BitWriter()
    for byte in data:
        length, value = codes[byte]
        # BitWriter zapisuje LSB first – konwertujemy wartość
        writer.write(_reverse_bits(value, length), length)

    return bytes(header) + writer.flush()


# ---------------------------------------------------------------------------
# Dekoder Huffmana
# ---------------------------------------------------------------------------

def decode(data: bytes) -> bytes:
    """
    Dekompresuje dane zakodowane funkcją encode().
    """
    if len(data) < 6:
        return b""

    pos = 0
    orig_size = struct.unpack_from(">I", data, pos)[0]; pos += 4
    n_symbols = struct.unpack_from(">H", data, pos)[0]; pos += 2

    if orig_size == 0:
        return b""

    # odtworzenie tablicy kodów
    codes: dict[int, tuple[int, int]] = {}
    for _ in range(n_symbols):
        sym = data[pos]; pos += 1
        length = data[pos]; pos += 1
        n_bytes = (length + 7) // 8
        value = int.from_bytes(data[pos:pos + n_bytes], "big"); pos += n_bytes
        codes[sym] = (length, value)

    # budowa drzewa dekodującego z tablicy kodów
    # (trie: dict (length, value) → symbol)
    lookup: dict[tuple[int, int], int] = {
        (length, value): sym for sym, (length, value) in codes.items()
    }
    max_len = max(l for l, _ in lookup) if lookup else 0

    reader = BitReader(data[pos:])
    output = bytearray()

    current_value = 0
    current_len = 0

    while len(output) < orig_size:
        try:
            bit = reader.read(1)
        except EOFError:
            break
        current_value = (current_value << 1) | bit
        current_len += 1
        key = (current_len, current_value)
        if key in lookup:
            output.append(lookup[key])
            current_value = 0
            current_len = 0
        elif current_len > max_len:
            raise ValueError(f"Błąd dekodowania Huffmana przy pozycji {len(output)}")

    return bytes(output)


def _reverse_bits(value: int, n_bits: int) -> int:
    """Odwraca kolejność bitów (MSB→LSB)."""
    result = 0
    for _ in range(n_bits):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result

