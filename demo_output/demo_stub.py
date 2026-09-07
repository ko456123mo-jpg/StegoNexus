#!/usr/bin/env python3
# STEGONEXUS EVASION DETECTION DEMO (inert stub)
# The byte blob below is XOR-wrapped with a key-derived keystream
# and split across an innocuous base64 block to simulate the
# classic 'payload hiding' pattern. Scan this file with the
# entropy + marker modules to see how defenders catch it.
import base64, hashlib, sys
KEY = 'StegoNexus-Demo-Key-2026'
BLOB = 'DXNsWEaW2QW1/inIlEsUvamUArMhoO/ZNQKpMco='
def kdf(k):
    return hashlib.pbkdf2_hmac('sha256', k.encode(), b'StegoNexus-EvasionDemo', 20000)
ks = kdf(KEY); data = base64.b64decode(BLOB)
plain = bytes(b ^ ks[i % len(ks)] for i, b in enumerate(data))
print('[demo] inert payload recovered:', plain)
