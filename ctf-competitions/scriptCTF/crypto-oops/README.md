# Crypto/Oops

**Challenge**

**I am from the future! I accidentally forgot to link `chall.zip`! Surely you can find it and solve it right?**

**Solution**

**The missing archive could still be downloaded from the same S3 path used by the other challenges. It contained `chall.py` and `enc.txt`.**

**The encryption code seeded Python's `random` module with the current Unix timestamp, then used `random.randbytes(32)` as an AES key:**

```python
random.seed(int(time.time()))
key = random.randbytes(32)
enc = AES.new(key, AES.MODE_ECB).encrypt(pad(flag, 16))
```

**This makes the key predictable if the encryption time is known. The ZIP metadata for `enc.txt` contained the UTC timestamp `2069-11-30 11:39:00`, matching the hint about being from the future.**

**I tried the nearby timestamps, regenerated each key, and decrypted the ciphertext. The correct seed was 33 seconds after the stored minute:**

```text
2069-11-30 11:39:33 UTC
```

**Flag**

**`scriptCTF{mY_buck37_1s_l34k1ng!}`**

## Verification and Defensive Perspective

The search space was deliberately kept narrow: parse the ZIP timestamp as UTC, test nearby epoch seconds, regenerate `random.randbytes(32)` for each candidate, decrypt with AES-ECB, and accept only correctly padded plaintext beginning with the known `scriptCTF{` prefix. This makes the recovery deterministic and avoids relying on visual inspection of random plaintext.

The cryptographic primitive was not broken; key generation was. Python's `random` module is deterministic and is not suitable for secrets. A secure implementation should use `secrets.token_bytes(32)` or `os.urandom(32)`, use an authenticated mode such as AES-GCM, and never derive a key solely from public or guessable time metadata.
