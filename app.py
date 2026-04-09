import os
from flask import Flask, render_template, request
from google import genai

app = Flask(__name__)

# Choose a widely available Gemini model
# You can change this to another supported name from the docs if needed.
PRIMARY_MODEL = "gemini-1.5-flash"  # text + good latency[web:331]


def build_client() -> genai.Client | None:
    """
    Build a Gemini client using the GEMINI_API_KEY environment variable.
    Returns None if the key is missing.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def call_gemini(prompt: str) -> str:
    """
    Call Gemini once with the configured model and return plain text.
    Raises an exception if the call fails.
    """
    client = build_client()
    if client is None:
        raise ValueError("GEMINI_API_KEY is not configured on the server.")

    response = client.models.generate_content(
        model=PRIMARY_MODEL,
        contents=prompt,
    )  # standard generate_content use[web:217][web:350]

    text = getattr(response, "text", None)
    if not text or not text.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return text.strip()


def parse_section(text: str, header: str, next_headers: list[str]) -> list[str]:
    """
    Extract bullet lines under a given header, until the next header.
    Expects format like:

    HEADER:
    - bullet 1
    - bullet 2
    """
    header_tag = header + ":\n"
    start = text.find(header_tag)
    if start == -1:
        return []

    start += len(header_tag)
    end = len(text)

    for nh in next_headers:
        idx = text.find(nh + ":\n", start)
        if idx != -1:
            end = min(end, idx)

    block = text[start:end].strip()
    bullets = []

    for line in block.splitlines():
        line = line.strip()
        if line.startswith("-"):
            bullets.append(line[1:].strip())

    return bullets


def parse_advice(text: str) -> dict:
    """
    Convert the raw Gemini text into a dict of sections,
    always returning a valid structure.
    """
    headers = ["PANIC_NOW", "BEFORE", "DURING", "AFTER", "NEARBY_HELP"]

    panic_now = parse_section(text, "PANIC_NOW", headers[1:])
    before = parse_section(text, "BEFORE", headers[2:])
    during = parse_section(text, "DURING", headers[3:])
    after = parse_section(text, "AFTER", headers[4:])
    nearby_help = parse_section(text, "NEARBY_HELP", [])

    return {
        "panic_now": panic_now,
        "before": before,
        "during": during,
        "after": after,
        "nearby_help": nearby_help,
    }


def get_disaster_advice(location: str, disaster_type: str, language: str) -> dict:
    """
    Ask Gemini for structured guidelines and parse them.
    If anything fails, return a minimal error message in panic_now.
    """
    prompt = f"""
You are an emergency survival assistant.

User location: {location}
Disaster type: {disaster_type}
Response language: {language}

Write short survival guidance for this situation.

IMPORTANT:
- KEEP ALL SECTION LABELS IN ENGLISH exactly as shown: PANIC_NOW, BEFORE, DURING, AFTER, NEARBY_HELP.
- Do NOT translate or change these labels.
- ONLY the bullet text should be translated into the Response language.

Respond in PLAIN TEXT only, using exactly this structure:

PANIC_NOW:
- step 1
- step 2
- step 3

BEFORE:
- point 1
- point 2
- point 3

DURING:
- point 1
- point 2
- point 3

AFTER:
- point 1
- point 2
- point 3

NEARBY_HELP:
- bullet 1
- bullet 2
- bullet 3

Rules:
- All bullet text must be in the Response language above.
- Each bullet must be under 20 words.
- Advice must be safe, legal, and realistic for ordinary people.
- Do NOT add any extra headings or explanations.
"""

    try:
        raw_text = call_gemini(prompt)
        advice = parse_advice(raw_text)

        # Ensure we always return the same keys even if Gemini misses one.
        for key in ["panic_now", "before", "during", "after", "nearby_help"]:
            advice.setdefault(key, [])
        return advice

    except Exception as e:
        # Minimal, non–hard-coded fallback: just show the error, no fake advice.
        return {
            "panic_now": [
                "AI guidance is temporarily unavailable. Please try again in a few moments."
            ],
            "before": [],
            "during": [],
            "after": [],
            "nearby_help": [f"Technical detail (for debugging): {str(e)}"],
        }


@app.route("/", methods=["GET", "POST"])
def index():
    user_data = None
    advice = None

    if request.method == "POST":
        location = request.form.get("location", "").strip()
        disaster_type = request.form.get("disaster_type", "").strip()
        language = request.form.get("language", "English").strip()

        user_data = {
            "location": location,
            "disaster_type": disaster_type,
            "language": language,
        }

        advice = get_disaster_advice(location, disaster_type, language)

    return render_template("index.html", user_data=user_data, advice=advice)


if __name__ == "__main__":
    # For local testing; Render will use gunicorn app:app
    app.run(host="0.0.0.0", port=5000, debug=True)
