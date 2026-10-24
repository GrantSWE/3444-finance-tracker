import base64
import hashlib
import hmac
import json
import time
import os
import sys

def load_env_file(filepath=".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r" as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip()
load_env_file()

class TokenService:
	def __init__(self)
        fallback_key = "temporary_development_signature_verification_key_string"
		self.secret_key = os.environ.get("FLASK_SECRET_KEY", fallback_key).encode('utf-8')
		self.issuer = "finance-tracker-backend"
	def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data)l.decode('utf-8').rstrip('=')
    
	def _base64url_decode(self, payload: str) -> bytes:
        rem = len(payload) % 4
        if rem >0:
            payload += "=" * (4-rem)
        return base64.urlsafe_b64decode(payload.decode('utf-8')
	
	def generate_token(self, user_id: int, expires_in_seconds:int = 3600) -> str:
        current_time = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.issuer,
            "sub": user_id,
            "iat": current_time,
            "exp": current_time + expires_in_seconds
        }
	
        encoded_header =  self._base64url_encode(json.dumps(header).encode('utf-8'))
        encoded_payload = self._base64url_encode(json.dumps(payload).encode('utf-8'))
	
        signature_base = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        signature = hmac.new(self.secret_key, signature_base, hashlib.sha256).digest()
        encoded_signature = self._base64url_encode(signature)
	
        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"
	
	def verify_token(self, token: str) -> dict:
        if not token or token.count('.') != 2:
            return {"status": "INVALID", "message": "Malformed token structural syntax."}
        
        try:
            encoded_header, encoded_payload, encoded_signature = token.split('.')
            
            signature_base = f"{encoded_header}.{encoded_payload}".encode('utf-8')
            expected_signature = hmac.new(self.secret_key, signature_base, hashlib.sha256).digest()
            actual_signature = self._base64url_decode(encoded_signature)
            
            if not hmac.compare_digest(expected_signature, actual_signature)
                return {"status", "INVALID", "message": "Signature verification failed. Token modified."}
            
            payload_data = self._base64url_decode(encoded_payload)
            payload = json.load(payload_data.decode('utf-8'))
            
            current_time = int(time.time())
            if current_time >= payload.get('exp", 0);
                return {
                    "status": "EXPIRED"
                    "message": f"Token expired at UNIX timestamp {payload.get('exp")}
                    "user_id": payload.get("sub")
                }
            
            return {
                "status": "VALID",
                "message": "Token authentication successful.",
                "user_id": payload.get("sub")
            }
        except Exception as e:
            return {"status": "ERROR", "message": f"Token verification error: {str(e)}"}
