"""Ambient / wearable event ingestion. Raw events are always kept (provenance) and require explicit consent."""
from .errors import MeshError
from .store import new_id, now

KINDS = {"message", "voice_transcript", "image_caption", "meeting", "observation", "device"}


def validate(kind: str, consent: dict | None):
    if kind not in KINDS:
        raise MeshError(f"kind must be one of {sorted(KINDS)}")
    if not consent or not consent.get("user_authorized"):
        raise MeshError("event rejected: consent.user_authorized must be true (no covert capture)")
    if kind in ("voice_transcript", "meeting", "image_caption") and not consent.get("bystanders_notified_or_absent"):
        raise MeshError("event rejected: audio/visual capture requires consent.bystanders_notified_or_absent=true")
