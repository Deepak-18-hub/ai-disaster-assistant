from flask import Flask, render_template, request
from google import genai
from google.genai import types, errors
import os

app = Flask(__name__)

# ----- Gemini client configuration -----
client = genai.Client(
    http_options=types.HttpOptions(api_version="v1")
)

PRIMARY_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-2.5-pro"


def _call_gemini(prompt: str, model_name: str) -> str:
    result = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    return result.text.strip()


def _parse_section(text: str, header: str, next_headers: list[str]) -> list[str]:
    header_tag = header + ":\n"
    start = text.find(header_tag)
    if start == -1:
        return []

    start = start + len(header_tag)
    end = len(text)

    for nh in next_headers:
        idx = text.find(nh + ":\n", start)
        if idx != -1:
            end = min(end, idx)

    section_block = text[start:end].strip()

    bullets = []
    for line in section_block.splitlines():
        line = line.strip()
        if line.startswith("-"):
            bullets.append(line.lstrip("-").strip())
    return bullets


def _parse_advice_plain(text: str) -> dict:
    headers = ["PANIC_NOW", "BEFORE", "DURING", "AFTER", "NEARBY_HELP"]

    panic_now = _parse_section(text, "PANIC_NOW", headers[1:])
    before = _parse_section(text, "BEFORE", headers[2:])
    during = _parse_section(text, "DURING", headers[3:])
    after = _parse_section(text, "AFTER", headers[4:])
    nearby_help = _parse_section(text, "NEARBY_HELP", [])

    return {
        "panic_now": panic_now,
        "before": before,
        "during": during,
        "after": after,
        "nearby_help": nearby_help,
    }


def get_disaster_advice(location: str, disaster_type: str, language: str) -> dict:
    if not os.environ.get("GEMINI_API_KEY"):
        return {
            "panic_now": ["Server is not configured correctly. Please set GEMINI_API_KEY on the backend."],
            "before": [],
            "during": [],
            "after": [],
            "nearby_help": []
        }

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
        advice = _parse_advice_plain(text)
        return advice

    except errors.ServerError:
        try:
            text = _call_gemini(prompt, FALLBACK_MODEL)
            advice = _parse_advice_plain(text)
            return advice
        except Exception:
            return {
                "panic_now": ["AI service is temporarily unavailable. Please try again in a moment."],
                "before": [],
                "during": [],
                "after": [],
                "nearby_help": []
            }

    except errors.ClientError:
        return {
            "panic_now": ["AI request was rejected by the service. Check quota, model access, or billing."],
            "before": [],
            "during": [],
            "after": [],
            "nearby_help": []
        }

    except Exception:
        return {
            "panic_now": ["Unexpected error while contacting AI. Please try again later."],
            "before": [],
            "during": [],
            "after": [],
            "nearby_help": []
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
    app.run(debug=True)
