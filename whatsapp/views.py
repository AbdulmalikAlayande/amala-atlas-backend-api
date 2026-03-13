"""
WhatsApp webhook views for Twilio integration.

Twilio sends inbound WhatsApp messages as POST requests to this webhook.
We process the message through the conversation state machine and
return a TwiML response with the bot's reply.

Setup:
1. Configure Twilio WhatsApp sandbox or Business API
2. Set webhook URL to: https://your-domain.com/whatsapp/webhook/
3. Set TWILIO_AUTH_TOKEN in environment
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from whatsapp.conversation import handle_message
from whatsapp.models import WhatsAppSession

logger = logging.getLogger(__name__)

# Sessions older than this are considered expired
SESSION_TIMEOUT = timedelta(hours=24)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """
    Receives WhatsApp messages from Twilio and returns TwiML responses.

    Twilio POST payload includes:
    - From: "whatsapp:+234XXXXXXXXXX"
    - Body: message text
    - NumMedia: number of media attachments
    - MediaUrl0: URL of first media attachment
    - Latitude: location pin latitude (if shared)
    - Longitude: location pin longitude (if shared)
    """

    def get(self, request):
        """Health check / webhook verification."""
        return HttpResponse("Amala Atlas WhatsApp Bot is running", status=200)

    def post(self, request):
        # Parse Twilio payload
        from_number = request.POST.get('From', '').replace('whatsapp:', '')
        body = request.POST.get('Body', '').strip()
        num_media = int(request.POST.get('NumMedia', 0))
        media_url = request.POST.get('MediaUrl0') if num_media > 0 else None
        latitude = _parse_float(request.POST.get('Latitude'))
        longitude = _parse_float(request.POST.get('Longitude'))

        if not from_number:
            return HttpResponse(status=400)

        logger.info(f"WhatsApp from {from_number}: body='{body[:50]}', lat={latitude}, media={bool(media_url)}")

        # Get or create session (reuse recent non-complete sessions)
        session = _get_or_create_session(from_number)

        # Process through conversation state machine
        reply = handle_message(
            session=session,
            body=body,
            media_url=media_url,
            latitude=latitude,
            longitude=longitude,
        )

        # Return TwiML response
        twiml = _make_twiml_response(reply)
        return HttpResponse(twiml, content_type='text/xml')


def _get_or_create_session(phone_number: str) -> WhatsAppSession:
    """
    Get the active session for a phone number, or create a new one.
    Expired or completed sessions are ignored (new one created).
    """
    cutoff = timezone.now() - SESSION_TIMEOUT
    session = (
        WhatsAppSession.objects
        .filter(phone_number=phone_number, created_at__gte=cutoff)
        .exclude(state=WhatsAppSession.State.COMPLETE)
        .order_by('-created_at')
        .first()
    )

    if session:
        return session

    return WhatsAppSession.objects.create(phone_number=phone_number)


def _make_twiml_response(message: str) -> str:
    """Build a TwiML XML response with a message."""
    # Escape XML special characters
    message = (
        message
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{message}</Message></Response>'


def _parse_float(value) -> float | None:
    """Safely parse a float from request data."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
