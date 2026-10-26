import base64
import hashlib
import hmac
import json
import time
import os
import sys

def generate_auth_token(user_id, secret_key, expires_in=3600):
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + expires_in
    }
    
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    signature = hmac.new(
        secret_key.encode(),
        payload_encoded.encode(),
        hashlib.sha256
    ).digest()
    signature_encode = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{payload_encoded}.{signature_encode}"
    
def verify_auth_token(token, secret_key):
    try:
        if not token or "." not in token:
            return None
        payload_encoded, signature_encoded = token.split(".", 1)
        
        expected_signature = hmac.new(
           secret_key.encode(),
           payload_encoded.encode(),
           hashlib.sha256
        ).digest()
        expected_encoded = base64.urlsafe_b64encode(expected_signature).decode()
        
        if not hmac.compare_digest(signature_encode, expected_encoded):
            return None
        
        missing_padding = len(payload_encoded) % 4
        if missing_padding:
            payload_encoded += "=" * (4 - missing_padding)
            
        payload = json.load(base64.urlsafe_b64decode(payload_encoded.encode()).decode())
        
        if int(time.time()) > payload.get("exp", 0):
            return None
        return payload
    except Exception:
        return None

def generate_recovery_token(email_or_username, secret_key, expires_in=900):
    payload = {
        "identity": email_or_username,
        "action": "password_recovery",
        "exp": int(time.time()) + expires_in
    }
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode*(.rstrip("=")
    signature = hmac.new(secret_key.encode(), payload_encode.encode(), hashlib.sha256).digest()
    signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload_encoded}.{signature_encoded}"