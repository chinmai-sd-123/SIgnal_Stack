import re
import random
import string

def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    if not text:
        return ""
    text = text.lower()
    # Remove special characters and replace spaces with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

def generate_seo_slug(title: str, company: str) -> str:
    """Generate a unique job slug."""
    base = slugify(f"{title}-{company}")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{base}-{random_suffix}"

def parse_location(location_str: str):
    """
    Extract city and state from a location string.
    Input example: "San Francisco, CA" -> ("San Francisco", "CA")
    """
    if not location_str:
        return None, None
    
    parts = [p.strip() for p in location_str.split(',')]
    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], None
    return None, None

def generate_location_slug(city: str, state: str) -> str:
    """Create a location slug with 'in-' prefix."""
    if city and state:
        return f"in-{slugify(city)}-{slugify(state)}"
    elif city:
        return f"in-{slugify(city)}"
    return ""
