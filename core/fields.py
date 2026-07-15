from django.db import models
from datetime import date
from core.encryption import encrypt, decrypt

class EncryptedCharField(models.CharField):
    description = "An encrypted character field using AES-256 via OpenSSL"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            if str(value).startswith("client_enc:"):
                return value
            return encrypt(str(value))
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            if str(value).startswith("client_enc:"):
                return value
            try:
                return decrypt(value)
            except Exception:
                return value
        return value

    def to_python(self, value):
        return value


class EncryptedTextField(models.TextField):
    description = "An encrypted text field using AES-256 via OpenSSL"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            return encrypt(str(value))
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            try:
                return decrypt(value)
            except Exception:
                return value
        return value

    def to_python(self, value):
        return value


class EncryptedIntegerField(models.TextField):
    description = "An encrypted integer field using AES-256 via OpenSSL"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            return encrypt(str(value))
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            try:
                decrypted = decrypt(value)
                return int(decrypted)
            except Exception:
                return value
        return value

    def to_python(self, value):
        if value is not None and not isinstance(value, int):
            try:
                return int(value)
            except ValueError:
                pass
        return value


class EncryptedFloatField(models.TextField):
    description = "An encrypted float field using AES-256 via OpenSSL"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            return encrypt(str(value))
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            try:
                decrypted = decrypt(value)
                return float(decrypted)
            except Exception:
                return value
        return value

    def to_python(self, value):
        if value is not None and not isinstance(value, float):
            try:
                return float(value)
            except ValueError:
                pass
        return value


class EncryptedDateField(models.TextField):
    description = "An encrypted date field using AES-256 via OpenSSL"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            if isinstance(value, date):
                val_str = value.isoformat()
            else:
                val_str = str(value)
            return encrypt(val_str)
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            try:
                decrypted = decrypt(value)
                from django.utils.dateparse import parse_date
                return parse_date(decrypted)
            except Exception:
                return value
        return value

    def to_python(self, value):
        if value is not None and not isinstance(value, date):
            from django.utils.dateparse import parse_date
            parsed = parse_date(value)
            if parsed:
                return parsed
        return value
