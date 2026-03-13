"""
WhatsApp conversation state machine.

Manages the multi-turn conversation for collecting spot data:
  awaiting_spot → awaiting_location → awaiting_extras → complete

Each state handler returns a reply message and optionally transitions
to the next state.
"""

import logging

from whatsapp.models import WhatsAppSession
from whatsapp.parser import parse_spot_message, parse_location_text, parse_extras_message
from places.models import Submission, PhotoURL
from places.services import create_candidate_from_submission

logger = logging.getLogger(__name__)


def handle_message(session: WhatsAppSession, body: str, media_url: str = None,
                   latitude: float = None, longitude: float = None) -> str:
    """
    Process an incoming WhatsApp message and return a reply.

    Routes to the appropriate state handler based on session state.
    """
    state = session.state

    # Special commands that work in any state
    if body and body.strip().lower() in ('reset', 'start over', 'cancel'):
        session.state = WhatsAppSession.State.AWAITING_SPOT
        session.partial_data = {}
        session.save()
        return (
            "No problem! Let's start fresh.\n\n"
            "Drop an Amala spot you know — just send me the name and area.\n"
            "Example: _Iya Basira, Mokola Ibadan_"
        )

    if state == WhatsAppSession.State.AWAITING_SPOT:
        return _handle_awaiting_spot(session, body, latitude, longitude)
    elif state == WhatsAppSession.State.AWAITING_LOCATION:
        return _handle_awaiting_location(session, body, latitude, longitude)
    elif state == WhatsAppSession.State.AWAITING_EXTRAS:
        return _handle_awaiting_extras(session, body, media_url)
    elif state == WhatsAppSession.State.COMPLETE:
        # Previous submission done, start new one
        session.state = WhatsAppSession.State.AWAITING_SPOT
        session.partial_data = {}
        session.save()
        return _handle_awaiting_spot(session, body, latitude, longitude)
    else:
        session.state = WhatsAppSession.State.AWAITING_SPOT
        session.partial_data = {}
        session.save()
        return "Something went wrong. Let's start over — send me an Amala spot!"


def _handle_awaiting_spot(session, body, latitude, longitude):
    """Handle initial spot name/location message."""
    data = session.partial_data

    # If user sent a location pin first
    if latitude is not None and longitude is not None:
        data['lat'] = latitude
        data['lng'] = longitude
        session.partial_data = data
        session.state = WhatsAppSession.State.AWAITING_SPOT
        session.save()
        return (
            "Got your location pin! 📍\n\n"
            "Now tell me the name of the spot.\n"
            "Example: _Iya Basira Amala_"
        )

    if not body or not body.strip():
        return (
            "Welcome to *Amala Atlas*! 🍲\n\n"
            "Know an Amala spot? Drop the name and area.\n"
            "Example: _Iya Basira, Mokola Ibadan_\n\n"
            "Or share a 📍 location pin first!"
        )

    parsed = parse_spot_message(body)

    if not parsed["parsed"] or not parsed["name"]:
        return (
            "Hmm, I couldn't quite get that. Try sending like this:\n"
            "_Spot Name, Area/City_\n\n"
            "Example: _Mama T, Agege Lagos_"
        )

    data['name'] = parsed['name']
    if parsed['phone']:
        data['phone'] = parsed['phone']

    if parsed['city']:
        data['city'] = parsed['city']
    if parsed['address']:
        data['address'] = parsed['address']

    # If we already have location pin from earlier message
    if data.get('lat') and data.get('lng'):
        session.partial_data = data
        session.state = WhatsAppSession.State.AWAITING_EXTRAS
        session.save()
        return _extras_prompt(data)

    # If we got a city, move to extras
    if parsed['city']:
        session.partial_data = data
        session.state = WhatsAppSession.State.AWAITING_EXTRAS
        session.save()
        return _extras_prompt(data)

    # Need location
    session.partial_data = data
    session.state = WhatsAppSession.State.AWAITING_LOCATION
    session.save()
    return (
        f"Got it — *{parsed['name']}*!\n\n"
        "Where is it located? You can:\n"
        "• Share a 📍 location pin (best!)\n"
        "• Type the area/city (e.g. _Mokola, Ibadan_)"
    )


def _handle_awaiting_location(session, body, latitude, longitude):
    """Handle location follow-up message."""
    data = session.partial_data

    if latitude is not None and longitude is not None:
        data['lat'] = latitude
        data['lng'] = longitude
        session.partial_data = data
        session.state = WhatsAppSession.State.AWAITING_EXTRAS
        session.save()
        return _extras_prompt(data)

    if body and body.strip():
        parsed = parse_location_text(body)
        if parsed['city']:
            data['city'] = parsed['city']
        if parsed['address']:
            data['address'] = parsed['address']

        if parsed['city'] or parsed['address']:
            session.partial_data = data
            session.state = WhatsAppSession.State.AWAITING_EXTRAS
            session.save()
            return _extras_prompt(data)

    return (
        "I need a location to add this spot. Try:\n"
        "• Share a 📍 pin from WhatsApp\n"
        "• Type the area, e.g. _Surulere, Lagos_"
    )


def _handle_awaiting_extras(session, body, media_url):
    """Handle optional extras (phone, price, photos) or submission."""
    data = session.partial_data

    if body:
        text = body.strip().lower()

        # Check for "done" / "skip" to submit as-is
        if text in ('done', 'skip', 'submit', 'that\'s all', 'no', 'nope'):
            return _complete_submission(session)

        # Parse extras from message
        extras = parse_extras_message(body)
        if extras:
            data.update(extras)
            session.partial_data = data
            session.save()

            # If they sent a phone, prompt for more or done
            return (
                "Got it! Anything else?\n"
                "• Phone number\n"
                "• Price range (cheap/mid/expensive)\n"
                "• Or type *done* to submit"
            )

    if media_url:
        photos = data.get('photos', [])
        photos.append(media_url)
        data['photos'] = photos
        session.partial_data = data
        session.save()
        return "Photo received! Send more, or type *done* to submit."

    return (
        "Any extra info? (all optional)\n"
        "• Phone number of the spot\n"
        "• Price range (cheap/mid/expensive)\n"
        "• Send a photo\n\n"
        "Or type *done* to submit as-is."
    )


def _complete_submission(session):
    """Create the Submission + Candidate and return confirmation."""
    data = session.partial_data

    try:
        photo_urls_list = data.get('photos', [])

        submission = Submission.objects.create(
            name=data.get('name', 'Unknown Spot'),
            kind='manual',
            address=data.get('address', ''),
            city=data.get('city', ''),
            country='Nigeria',
            lat=data.get('lat'),
            lng=data.get('lng'),
            phone=data.get('phone', ''),
            price_band=data.get('price_band', ''),
            source_channel='whatsapp',
            whatsapp_phone=session.phone_number,
            conversation_id=str(session.public_id),
            transcript=str(data),
        )

        for url in photo_urls_list:
            PhotoURL.objects.create(url=url, content_object=submission)

        candidate = create_candidate_from_submission(submission, photo_urls=photo_urls_list)

        session.state = WhatsAppSession.State.COMPLETE
        session.submission = submission
        session.save()

        city_display = data.get('city', 'Nigeria')
        return (
            f"*{data.get('name')}* in {city_display} has been submitted! ✅\n\n"
            f"It'll appear on the map once verified.\n"
            f"Score: {float(candidate.score):.0%}\n\n"
            f"Know another spot? Just send the name!\n"
            f"Share Amala Atlas with friends 🍲"
        )

    except Exception as e:
        logger.exception(f"Failed to create submission from WhatsApp: {e}")
        session.state = WhatsAppSession.State.AWAITING_SPOT
        session.partial_data = {}
        session.save()
        return "Something went wrong saving your spot. Please try again!"


def _extras_prompt(data):
    """Generate the extras prompt showing what we already have."""
    name = data.get('name', '???')
    city = data.get('city', '')
    has_pin = bool(data.get('lat'))

    location_str = f"📍 Pin received" if has_pin else city
    return (
        f"*{name}* — {location_str}\n\n"
        "Any extra info? (all optional)\n"
        "• Phone number of the spot\n"
        "• Price range (cheap/mid/expensive)\n"
        "• Send a photo\n\n"
        "Or type *done* to submit as-is."
    )
