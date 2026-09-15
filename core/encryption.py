import subprocess
import os
from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = os.getenv("ENCRYPTION_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("ENCRYPTION_KEY environment variable is not set")

def get_env():
    env = os.environ.copy()
    env["ENCRYPTION_PASS"] = SECRET_KEY
    return env

def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    p = subprocess.Popen(
        ["openssl", "enc", "-aes-256-cbc", "-a", "-salt", "-pbkdf2", "-pass", "env:ENCRYPTION_PASS"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=get_env()
    )
    stdout, stderr = p.communicate(input=plain_text)
    if p.returncode != 0:
        raise RuntimeError(f"Encryption failed: {stderr}")
    return stdout.strip()

def decrypt(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    p = subprocess.Popen(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-a", "-pbkdf2", "-pass", "env:ENCRYPTION_PASS"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=get_env()
    )
    stdout, stderr = p.communicate(input=cipher_text + "\n")
    if p.returncode != 0:
        raise RuntimeError(f"Decryption failed: {stderr}")
    return stdout.strip()
