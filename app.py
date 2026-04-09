from flask import Flask, render_template, request
from google import genai
import os

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]


def build_client():
    if not API_KEY:
        return None
    return genai.Client(api_key=API_KEY)


def call_gemini(prompt: str) -> str:
    client = build_client()
    if client is None:
        raise ValueError("Missing GEMINI_API_KEY")

    last_error = None

    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            text = getattr(response, "text", None)
            if text and text.strip():
                return text.strip()
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Gemini models failed: {last_error}")


def parse_section(text: str, header: str, next_headers: list[str]) -> list[str]:
    header_tag = header + ":\n"
    start = text.find(header_tag)
    if start == -1:
        return []

    start += len(header_tag)
    end = len(text)

    for next_header in next_headers:
        idx = text.find(next_header + ":\n", start)
        if idx != -1:
            end = min(end, idx)

    block = text[start:end].strip()
    items = []

    for line in block.splitlines():
        line = line.strip()
        if line.startswith("-"):
            items.append(line[1:].strip())

    return items


def parse_advice(text: str) -> dict:
    headers = ["PANIC_NOW", "BEFORE", "DURING", "AFTER", "NEARBY_HELP"]

    result = {
        "panic_now": parse_section(text, "PANIC_NOW", headers[1:]),
        "before": parse_section(text, "BEFORE", headers[2:]),
        "during": parse_section(text, "DURING", headers[3:]),
        "after": parse_section(text, "AFTER", headers[4:]),
        "nearby_help": parse_section(text, "NEARBY_HELP", []),
    }

    return {
        "panic_now": result["panic_now"] or ["Stay calm and move away from immediate danger."],
        "before": result["before"] or ["Keep emergency numbers and basic supplies ready."],
        "during": result["during"] or ["Follow official alerts and move to a safe place."],
        "after": result["after"] or ["Check injuries, avoid hazards, and contact help if needed."],
        "nearby_help": result["nearby_help"] or ["Check nearby hospitals, police, and emergency response centers."]
    }


def demo_advice(location: str, disaster_type: str, language: str) -> dict:
    disaster = disaster_type.lower()

    if disaster == "earthquake":
        return {
            "panic_now": [
                "Drop, cover, and hold under a sturdy table.",
                "Stay away from windows, glass, and tall furniture.",
                "Do not use lifts until shaking stops."
            ],
            "before": [
                "Keep a torch, water, and first-aid kit ready.",
                "Identify safe spots under strong furniture.",
                "Store emergency contacts on your phone."
            ],
            "during": [
                "Protect your head and neck immediately.",
                "If outside, move away from buildings and poles.",
                "If driving, stop in a clear open area."
            ],
            "after": [
                "Check for injuries and gas leaks carefully.",
                "Expect aftershocks and stay alert.",
                "Use phone only for urgent communication."
            ],
            "nearby_help": [
                f"Search hospitals and disaster response near {location}.",
                "Follow local government and police advisories.",
                "Use Google Maps for emergency services nearby."
            ]
        }

    if disaster == "flood":
        return {
            "panic_now": [
                "Move to higher ground immediately.",
                "Avoid walking or driving through floodwater.",
                "Switch off electricity if safe to do so."
            ],
            "before": [
                "Keep important documents in waterproof covers.",
                "Store drinking water and emergency food.",
                "Know the nearest safe shelter route."
            ],
            "during": [
                "Stay away from drains, bridges, and fast water.",
                "Listen to official warnings continuously.",
                "Carry only essentials if evacuating."
            ],
            "after": [
                "Avoid contaminated water and damaged wires.",
                "Return home only after official clearance.",
                "Disinfect water-contact items before use."
            ],
            "nearby_help": [
                f"Check relief camps and hospitals near {location}.",
                "Use local disaster helpline numbers.",
                "Open Maps for emergency shelters nearby."
            ]
        }

    if disaster == "fire":
        return {
            "panic_now": [
                "Leave the area immediately using the nearest exit.",
                "Stay low to avoid smoke inhalation.",
                "Call emergency services once safe."
            ],
            "before": [
                "Know exits and keep extinguishers ready.",
                "Avoid overloading electrical sockets.",
                "Store flammable items safely."
            ],
            "during": [
                "Do not use lifts.",
                "Cover nose and mouth with cloth if smoky.",
                "Close doors behind you while escaping."
            ],
            "after": [
                "Do not re-enter until cleared by authorities.",
                "Treat burns with cool running water.",
                "Check for smoke-related breathing issues."
            ],
            "nearby_help": [
                f"Find fire station and hospital near {location}.",
                "Follow local police and fire department updates.",
                "Use Google Maps to locate emergency response."
            ]
        }

    return {
        "panic_now": [
            f"Stay calm and move to a safer place in {location}.",
            "Avoid immediate hazards around you.",
            "Follow official alerts and instructions."
        ],
        "before": [
            "Keep emergency supplies ready.",
            "Know local shelter and hospital locations.",
            "Save emergency contacts on your phone."
        ],
        "during": [
            "Protect yourself first.",
            "Stay informed through official announcements.",
            "Avoid risky roads, structures, or crowds."
        ],
        "after": [
            "Check injuries and hazards nearby.",
            "Help others only when safe.",
            "Use verified sources for updates."
        ],
        "nearby_help": [
            f"Search emergency services near {location}.",
            "Check nearby hospitals and police stations.",
            "Follow district disaster management updates."
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
        text = call_gemini(prompt)
        return parse_advice(text)
    except Exception:
        return demo_advice(location, disaster_type, language)


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
