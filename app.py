from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key="AIzaSyDn5jR93G2PwG7WJhPjhre398GNkHfn9zg")

model = genai.GenerativeModel("gemini-pro")

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

        ai_response = model.generate_content(prompt)
        response = ai_response.text

    except:
        # fallback
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
