import os
import base64
import secrets

from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

SECRET_KEY = os.getenv("ENCRYPTION_KEY", "default-secret-key-123456")
PBKDF2_ITERATIONS = 10000
SALT_PREFIX = b"Salted__"
KEY_LENGTH = 32
IV_LENGTH = 16


def _derive_key_and_iv(salt: bytes) -> tuple[bytes, bytes]:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH + IV_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    key_material = kdf.derive(SECRET_KEY.encode("utf-8"))
    return key_material[:KEY_LENGTH], key_material[KEY_LENGTH:]

def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    salt = secrets.token_bytes(8)
    key, iv = _derive_key_and_iv(salt)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(plain_text.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    payload = SALT_PREFIX + salt + encrypted
    return base64.b64encode(payload).decode("ascii")

def decrypt(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    raw = base64.b64decode(cipher_text)
    if not raw.startswith(SALT_PREFIX):
        raise RuntimeError("Decryption failed: invalid ciphertext header")

    salt = raw[len(SALT_PREFIX):len(SALT_PREFIX) + 8]
    encrypted = raw[len(SALT_PREFIX) + 8:]
    key, iv = _derive_key_and_iv(salt)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(encrypted) + decryptor.finalize()
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    plain_text = unpadder.update(padded) + unpadder.finalize()
    return plain_text.decode("utf-8")
