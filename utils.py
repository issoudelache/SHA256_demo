from __future__ import annotations

def to_uint32(x: int) -> int:
    return x & 0xFFFFFFFF

def rotr(x: int, n: int) -> int:
    x &= 0xFFFFFFFF
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def shr(x: int, n: int) -> int:
    return (x & 0xFFFFFFFF) >> n

def bytes_to_hex(b: bytes) -> str:
    return ''.join(f"{byte:02x}" for byte in b)
