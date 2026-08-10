#!/usr/bin/env python3
"""Encrypt RELT hub source HTML into d.json for GitHub Pages deployment."""

import base64
import hashlib
import json
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PASSWORD = "NextMoveEasy"
SOURCE = os.path.expanduser("~/Vend/dashboards/RELT-hub-source.html")
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "d.json")

with open(SOURCE, "r", encoding="utf-8") as f:
    content = f.read()

salt = secrets.token_bytes(16)
iv = secrets.token_bytes(12)
key = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), salt, 100000, dklen=32)
ct = AESGCM(key).encrypt(iv, content.encode("utf-8"), None)

with open(OUTPUT, "w") as f:
    json.dump({
        "s": base64.b64encode(salt).decode(),
        "i": base64.b64encode(iv).decode(),
        "c": base64.b64encode(ct).decode(),
    }, f)

size_kb = os.path.getsize(OUTPUT) / 1024
print(f"Encrypted {SOURCE}")
print(f"Output: {OUTPUT} ({size_kb:.0f} KB)")
print(f"Password: {PASSWORD}")
