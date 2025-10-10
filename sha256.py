from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
from utils import to_uint32, rotr, shr

# Constants (FIPS 180-4)
K: List[int] = [
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
]
H0: List[int] = [
    0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19,
]

# Boolean helpers
Ch = lambda x, y, z: (x & y) ^ (~x & z)
Maj = lambda x, y, z: (x & y) ^ (x & z) ^ (y & z)
Sigma0 = lambda x: rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)
Sigma1 = lambda x: rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)
sigma0 = lambda x: rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)
sigma1 = lambda x: rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

@dataclass
class RoundState:
    i: int
    a: int; b: int; c: int; d: int; e: int; f: int; g: int; h: int
    T1: int; T2: int; K: int; W: int

@dataclass
class Trace:
    padding: Dict[str, int]
    blocks: List[List[int]]          # per block: 16 initial 32-bit words
    schedules: List[List[int]]       # per block: W[0..63]
    rounds: List[List[RoundState]]   # per block: 64 round states

# Padding
def _pad(message: bytes) -> bytes:
    bit_len = len(message) * 8
    m = message + b"\x80"
    k = (56 - (len(m) % 64)) % 64
    m += b"\x00" * k
    m += bit_len.to_bytes(8, "big")
    return m

# Message schedule
def _schedule(block: bytes) -> List[int]:
    assert len(block) == 64
    W = [0] * 64
    for t in range(16):
        W[t] = int.from_bytes(block[4*t:4*(t+1)], "big")
    for t in range(16, 64):
        W[t] = to_uint32(W[t-16] + sigma0(W[t-15]) + W[t-7] + sigma1(W[t-2]))
    return W

# Compression for one block
def _compress(H: List[int], W: List[int], trace_rounds: List[RoundState] | None = None) -> List[int]:
    a, b, c, d, e, f, g, h = H
    for i in range(64):
        T1 = to_uint32(h + Sigma1(e) + Ch(e, f, g) + K[i] + W[i])
        T2 = to_uint32(Sigma0(a) + Maj(a, b, c))
        h = g; g = f; f = e
        e = to_uint32(d + T1)
        d = c; c = b; b = a
        a = to_uint32(T1 + T2)
        if trace_rounds is not None:
            trace_rounds.append(RoundState(i, a, b, c, d, e, f, g, h, T1, T2, K[i], W[i]))
    return [
        to_uint32(H[0] + a), to_uint32(H[1] + b), to_uint32(H[2] + c), to_uint32(H[3] + d),
        to_uint32(H[4] + e), to_uint32(H[5] + f), to_uint32(H[6] + g), to_uint32(H[7] + h),
    ]

# Public API
def sha256(data: bytes) -> bytes:
    H = H0.copy()
    padded = _pad(data)
    for i in range(0, len(padded), 64):
        block = padded[i:i+64]
        W = _schedule(block)
        H = _compress(H, W)
    return b"".join(x.to_bytes(4, "big") for x in H)

def sha256_hex(text: str) -> str:
    return sha256(text.encode("utf-8")).hex()

def sha256_trace(data: bytes) -> Tuple[bytes, Trace]:
    H = H0.copy()
    padded = _pad(data)
    total_pad_bits = (len(padded) - len(data)) * 8
    zero_bits = total_pad_bits - 1 - 64

    pad_info = {
        "data_bits": len(data) * 8,
        "one_bit": 1,
        "zero_pad_bits": zero_bits,
        "len_field_bits": 64,
        "total_bits": len(padded) * 8,
        "blocks": len(padded) // 64,
    }

    blocks_words: List[List[int]] = []
    schedules: List[List[int]] = []
    rounds: List[List[RoundState]] = []

    for i in range(0, len(padded), 64):
        block = padded[i:i+64]
        words16 = [int.from_bytes(block[4*t:4*(t+1)], "big") for t in range(16)]
        blocks_words.append(words16)
        W = _schedule(block)
        schedules.append(W)
        rlist: List[RoundState] = []
        H = _compress(H, W, rlist)
        rounds.append(rlist)

    digest = b"".join(x.to_bytes(4, "big") for x in H)
    return digest, Trace(pad_info, blocks_words, schedules, rounds)
