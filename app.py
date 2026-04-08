from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key="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")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_help", methods=["POST"])
def get_help():
    data = request.json
    disaster = data.get("disaster")
    location = data.get("location")

    try:
        prompt = f"Give short, clear survival steps for a {disaster} in {location}. Keep it simple."

        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        response = ai_response.choices[0].message.content

    except:
        # fallback logic
        if disaster == "Flood":
            response = "Move to higher ground. Avoid water."
        elif disaster == "Earthquake":
            response = "Drop, cover, hold."
        elif disaster == "Fire":
            response = "Use stairs. Stay low."
        else:
            response = "Stay safe and follow instructions."

    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
