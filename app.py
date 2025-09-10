from flask import Flask, request, render_template, jsonify
import re
import requests

app = Flask(__name__)

# ----------------------
# Configuraciones
# ----------------------
# Dirección interna de tu servidor local (Hybrid Connection)
LOCAL_SERVER_URL = "http://192.168.10.14:5001/api/upload"
AUTH_TOKEN = "9f82a7f1-2341-456c-b812-9abcde123457"
MAX_FILE_SIZE_MB = 5

# ----------------------
# Funciones auxiliares
# ----------------------
def valid_email(email):
    """Valida formato de correo."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def enviar_a_servidor_local(email, archivos):
    """Envía archivos y email al servidor local vía Hybrid Connection."""
    headers = {'Authorization': f'Bearer {AUTH_TOKEN}'}
    files = {}

    for tipo, archivo in archivos.items():
        if archivo:
            archivo.stream.seek(0)
            content = archivo.read()
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"El archivo {tipo} excede {MAX_FILE_SIZE_MB} MB")
            archivo.stream.seek(0)
            files[tipo] = (archivo.filename, archivo.stream, 'application/pdf')

    data = {'email': email}
    response = requests.post(LOCAL_SERVER_URL, data=data, files=files, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

# ----------------------
# Rutas
# ----------------------
@app.route('/')
def index():
    return render_template('formulario.html')

@app.route('/api/upload', methods=['POST'])
def api_upload():
    # Recibir datos del formulario
    email = request.form.get('email')
    factura = request.files.get('factura')
    orden = request.files.get('orden')
    remision = request.files.get('remision')

    # Validaciones básicas
    if not email or not valid_email(email):
        return jsonify({"error": "Correo no válido"}), 400
    if not factura or not orden or not remision:
        return jsonify({"error": "Todos los archivos son obligatorios"}), 400

    # Validar tipo de archivo PDF
    archivos = {'factura': factura, 'orden': orden, 'remision': remision}
    for tipo, archivo in archivos.items():
        if archivo.mimetype != 'application/pdf':
            return jsonify({"error": f"El archivo {tipo} no es un PDF válido"}), 400

    # Enviar al servidor local
    try:
        resp = enviar_a_servidor_local(email, archivos)
        return jsonify({"message": "Archivos enviados correctamente", "server_response": resp}), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error conexión al servidor local: {e}")
        return jsonify({"error": "No se pudo conectar con el servidor local"}), 500
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error inesperado: {e}")
        return jsonify({"error": "Ocurrió un error inesperado"}), 500

# ----------------------
# Ejecutar app
# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
