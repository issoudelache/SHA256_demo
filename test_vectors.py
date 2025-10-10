from sha256 import sha256_hex

def run():
    vecs = {
        "": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "abc": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "hello": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    }
    ok = True
    for m, expected in vecs.items():
        hx = sha256_hex(m)
        print(m or "<empty>", hx, "OK" if hx == expected else "FAIL")
        ok &= (hx == expected)
    return ok

if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
