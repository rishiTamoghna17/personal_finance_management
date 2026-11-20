import hashlib

from django.db import models

from core.fields import EncryptedTextField


class PushDevice(models.Model):
    """A single-user FCM registration. The raw registration token is encrypted at rest."""

    token_hash = models.CharField(max_length=64, unique=True)
    token = EncryptedTextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def hash_token(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PushDelivery(models.Model):
    """Only a non-reversible event fingerprint is retained for duplicate suppression."""

    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE, related_name="deliveries")
    event_hash = models.CharField(max_length=64)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("device", "event_hash"), name="advisor_push_event_once")]
