"""
WhatsApp conversation session tracking.

Each WhatsApp user gets a session that accumulates spot data
across multiple messages until the submission is complete.
"""

from django.db import models

from commons.models import BaseModel


class WhatsAppSession(BaseModel):
    """Tracks an ongoing WhatsApp conversation for spot submission."""

    class State(models.TextChoices):
        AWAITING_SPOT = "awaiting_spot", "Awaiting spot name/location"
        AWAITING_LOCATION = "awaiting_location", "Awaiting location details"
        AWAITING_EXTRAS = "awaiting_extras", "Awaiting optional details"
        COMPLETE = "complete", "Submission complete"

    phone_number = models.CharField(max_length=20, db_index=True)
    state = models.CharField(
        max_length=30,
        choices=State.choices,
        default=State.AWAITING_SPOT,
    )
    partial_data = models.JSONField(default=dict, blank=True)
    submission = models.ForeignKey(
        'places.Submission',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='whatsapp_sessions',
    )

    class Meta:
        indexes = [
            models.Index(fields=["phone_number", "-created_at"]),
        ]

    def __str__(self):
        return f"WhatsApp {self.phone_number} ({self.state})"
