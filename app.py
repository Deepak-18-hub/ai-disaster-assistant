from flask import Flask, render_template, request
from google import genai
import os

app = Flask(__name__)


def build_client():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


PRIMARY_MODEL = "gemini-1.5-flash"
FALLBACK_MODEL = "gemini-1.5-pro"


def _call_gemini(prompt: str, model_name: str) -> str:
    client = build_client()
    if client is None:
        raise ValueError("Missing GEMINI_API_KEY")

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )
    text = getattr(response, "text", None)
    if text and text.strip():
        return text.strip()

    raise RuntimeError("Empty response from Gemini")


def _parse_section(text: str, header: str, next_headers: list[str]) -> list[str]:
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


def _parse_advice_plain(text: str) -> dict:
    headers = ["PANIC_NOW", "BEFORE", "DURING", "AFTER", "NEARBY_HELP"]

    panic_now = _parse_section(text, "PANIC_NOW", headers[1:])
    before = _parse_section(text, "BEFORE", headers[2:])
    during = _parse_section(text, "DURING", headers[3:])
    after = _parse_section(text, "AFTER", headers[4:])
    nearby_help = _parse_section(text, "NEARBY_HELP", [])

    return {
        "panic_now": panic_now or ["Stay calm and move to a safer area immediately."],
        "before": before or ["Keep emergency supplies ready."],
        "during": during or ["Follow official safety instructions."],
        "after": after or ["Check for injuries and hazards before returning."],
        "nearby_help": nearby_help or ["Contact local emergency responders if needed."]
    }


def fallback_advice(message: str) -> dict:
    return {
        "panic_now": [message],
        "before": [
            "Check your Gemini API key in Render Environment settings.",
            "Make sure billing or free quota is available."
        ],
        "during": [
            "Use gemini-1.5-flash for better availability.",
            "Redeploy after updating the environment variable."
        ],
        "after": [
            "Test locally first with the same API key.",
            "Check Render logs for the exact error."
        ],
        "nearby_help": [
            "For demo: show UI, multilingual flow, and emergency structure.",
            "The app deployment is working; only AI access needs fixing."
        ]
    }


def get_disaster_advice(location: str, disaster_type: str, language: str) -> dict:
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
        text = _call_gemini(prompt, PRIMARY_MODEL)
        return _parse_advice_plain(text)
    except Exception:
        try:
            text = _call_gemini(prompt, FALLBACK_MODEL)
            return _parse_advice_plain(text)
        except ValueError:
            return fallback_advice("Server setup incomplete: GEMINI_API_KEY is missing.")
        except Exception:
            return fallback_advice("AI service is temporarily unavailable. Please check quota, billing, or model access.")


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
            "language": language
        }

        advice = get_disaster_advice(location, disaster_type, language)

    return render_template("index.html", user_data=user_data, advice=advice)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
