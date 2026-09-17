import os
import sqlite3
import hashlib
import hmac
import base64
import json
import time

# 1. SECURITY MODULE
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "tsm_superbrain_jwt_secret_quant_2026_x89a!")

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(salt + dk).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        raw = base64.b64decode(hashed.encode("utf-8"))
        salt = raw[:16]
        dk = raw[16:]
        check_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(dk, check_dk)
    except Exception:
        return False

def xor_encrypt(text: str, key: str = SECRET_KEY) -> str:
    if not text:
        return ""
    k = (key * ((len(text) // len(key)) + 1))[:len(text)]
    enc = bytes([ord(c) ^ ord(kc) for c, kc in zip(text, k)])
    return base64.b64encode(enc).decode("utf-8")

def xor_decrypt(enc_text: str, key: str = SECRET_KEY) -> str:
    if not enc_text:
        return ""
    try:
        raw = base64.b64decode(enc_text.encode("utf-8"))
        k = (key * ((len(raw) // len(key)) + 1))[:len(raw)]
        dec = "".join([chr(b ^ ord(kc)) for b, kc in zip(raw, k)])
        return dec
    except Exception:
        return ""

def create_jwt_token(payload: dict, expires_in_sec: int = 86400 * 7) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload_copy = dict(payload)
    payload_copy["exp"] = int(time.time()) + expires_in_sec
    
    hdr_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    pay_b64 = base64.urlsafe_b64encode(json.dumps(payload_copy).encode("utf-8")).decode("utf-8").rstrip("=")
    
    msg = f"{hdr_b64}.{pay_b64}".encode("utf-8")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    
    return f"{hdr_b64}.{pay_b64}.{sig_b64}"

def verify_jwt_token(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        hdr_b64, pay_b64, sig_b64 = parts
        
        # Verify signature
        msg = f"{hdr_b64}.{pay_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
        
        # Padding
        rem = len(sig_b64) % 4
        if rem > 0:
            sig_b64 += "=" * (4 - rem)
        provided_sig = base64.urlsafe_b64decode(sig_b64.encode("utf-8"))
        
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        
        rem_p = len(pay_b64) % 4
        if rem_p > 0:
            pay_b64 += "=" * (4 - rem_p)
        payload = json.loads(base64.urlsafe_b64decode(pay_b64.encode("utf-8")).decode("utf-8"))
        
        if payload.get("exp", 0) < time.time():
            return None # Expired
            
        return payload
    except Exception:
        return None

print("Security module test:", verify_password("testPass123", hash_password("testPass123")))