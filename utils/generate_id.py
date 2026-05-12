"""ID generation utility"""
import uuid


def generate_id() -> str:
    """Generate a unique ID string"""
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """short unique ID - 8 chars"""
    return uuid.uuid4().hex[:8]
