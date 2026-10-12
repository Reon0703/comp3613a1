from pathlib import Path
from uuid import uuid4


PROFILE_DIRECTORY = Path("app/static/img/company_profiles")


PROFILE_PALETTES = {
    "Business": ("#12333F", "#94B0B7"),
    "Science": ("#245B5A", "#A5C8C2"),
    "Technology": ("#243B53", "#82B7C9"),
    "Agriculture": ("#365C3A", "#B9D39B"),
    "Sports": ("#7B3F2A", "#E0A36F"),
    "Engineering": ("#4A4E69", "#A9B4C2"),
    "Energy": ("#526A39", "#D0C77B"),
    "Creative": ("#704C6D", "#D8A7C8"),
    "Health": ("#3D6475", "#A9D2D5"),
    "Logistics": ("#5A5142", "#D4B483"),
}


def _initials(company_name: str) -> str:
    words = [word for word in company_name.split() if word]
    if len(words) == 1:
        return words[0][:2].upper()
    return "".join(word[0] for word in words[:2]).upper()


def ensure_company_profile_image(
    username: str,
    company_name: str,
    discipline: str,
) -> str:
    """Create a lightweight branded profile image once and return its static URL."""
    primary, secondary = PROFILE_PALETTES.get(
        discipline,
        ("#12333F", "#C2C8C5"),
    )
    initials = _initials(company_name)
    filename = f"{username}.svg"
    destination = PROFILE_DIRECTORY / filename
    PROFILE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not destination.exists():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 420" role="img" aria-labelledby="title desc">
  <title id="title">{company_name} profile image</title>
  <desc id="desc">Branded company profile image for {company_name}</desc>
  <rect width="640" height="420" rx="36" fill="{primary}"/>
  <circle cx="520" cy="88" r="142" fill="{secondary}" opacity="0.72"/>
  <circle cx="104" cy="390" r="168" fill="{secondary}" opacity="0.2"/>
  <path d="M0 300 C150 230 260 390 420 294 C510 240 578 250 640 272 L640 420 L0 420 Z" fill="{secondary}" opacity="0.2"/>
  <text x="56" y="110" fill="#FFFFFF" font-family="Georgia, serif" font-size="26" opacity="0.82">{discipline}</text>
  <text x="56" y="286" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="112" font-weight="700" letter-spacing="4">{initials}</text>
</svg>
'''
        destination.write_text(svg, encoding="utf-8")

    return f"/static/img/company_profiles/{filename}"


def save_uploaded_profile_image(
    content: bytes,
    content_type: str | None,
    username: str,
    profile_group: str = "company_profiles",
) -> str:
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    if content_type not in allowed_types:
        raise ValueError("Upload a JPG, PNG, or WEBP image.")
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("Images must be 5 MB or smaller.")

    if profile_group not in {"company_profiles", "student_profiles"}:
        raise ValueError("Invalid profile image destination.")

    destination_directory = Path("app/static/uploads") / profile_group
    destination_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{username}-{uuid4().hex}{allowed_types[content_type]}"
    (destination_directory / filename).write_bytes(content)
    return f"/static/uploads/{profile_group}/{filename}"
