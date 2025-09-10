from flask import Flask, request, render_template, jsonify
import re
import requests

app = Flask(__name__)

LOCAL_SERVER_URL = "http://LABJose:5001/api/upload"  # Hostname interno del servidor local
AUTH_TOKEN = "9f82a7f1-2341-456c-b812-9abcde123457"

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def enviar_a_servidor_local(email, archivos):
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}
    files = {}
    for tipo, archivo in archivos.items():
        archivo.stream.seek(0)
        files[tipo] = (archivo.filename, archivo.stream, "application/pdf")
    data = {"email": email}
    response = requests.post(LOCAL_SERVER_URL, data=data, files=files, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

@app.route("/")
def index():
    return render_template("formulario.html")

@app.route("/api/upload", methods=["POST"])
def api_upload():
    email = request.form.get("email")
    factura = request.files.get("factura")
    orden = request.files.get("orden")
    remision = request.files.get("remision")

    if not email or not valid_email(email):
        return jsonify({"error": "Correo no válido"}), 400

    archivos = {"factura": factura, "orden": orden, "remision": remision}

    try:
        resp = enviar_a_servidor_local(email, archivos)
        return jsonify({"message": "Archivos enviados correctamente", "server_response": resp}), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error conexión al servidor local: {e}")
        return jsonify({"error": "No se pudo conectar con el servidor local"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
