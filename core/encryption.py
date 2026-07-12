import subprocess
import os

SECRET_KEY = os.getenv("ENCRYPTION_KEY", "default-secret-key-123456")

def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    p = subprocess.Popen(
        ["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2", "-pass", f"pass:{SECRET_KEY}"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = p.communicate(input=plain_text)
    if p.returncode != 0:
        raise RuntimeError(f"Encryption failed: {stderr}")
    return stdout.strip()

def decrypt(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    p = subprocess.Popen(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-a", "-pbkdf2", "-pass", f"pass:{SECRET_KEY}"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = p.communicate(input=cipher_text + "\n")
    if p.returncode != 0:
        raise RuntimeError(f"Decryption failed: {stderr}")
    return stdout.strip()
