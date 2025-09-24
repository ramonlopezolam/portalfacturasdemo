from flask import Flask, request, render_template, jsonify
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
import re
from dotenv import load_dotenv
import traceback
import json  # 👈 para guardar el metadata en formato JSON

app = Flask(__name__)

# ----------------------
# Configuración Azure Blob
# ----------------------
load_dotenv()  # Carga variables del .env
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER")

# ----------------------
# Funciones auxiliares
# ----------------------
def valid_email(email):
    """Valida formato de correo electrónico."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def subir_a_blob(archivo, carpeta, id_entrada):
    """Sube un archivo PDF al contenedor Blob con nombre basado en carpeta + id_entrada."""
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    ext = os.path.splitext(archivo.filename)[1]  # conserva extensión (.pdf)
    blob_client = blob_service_client.get_blob_client(
        container=BLOB_CONTAINER,
        blob=f"{carpeta}/{carpeta}_{id_entrada}{ext}"
    )
    archivo.stream.seek(0)
    blob_client.upload_blob(archivo.stream, overwrite=True)

def subir_metadata(email, id_entrada):
    """Crea y sube un JSON con el correo y el IDEntrada a la carpeta metadata/."""
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(
        container=BLOB_CONTAINER,
        blob=f"metadata/metadata_{id_entrada}.json"
    )
    metadata = {
        "IDEntrada": id_entrada,
        "email": email,
        "fecha_subida": datetime.now().isoformat()
    }
    blob_client.upload_blob(json.dumps(metadata, ensure_ascii=False, indent=2), overwrite=True)

# ----------------------
# Rutas
# ----------------------
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
    id_entrada = datetime.now().strftime("%Y%m%d%H%M%S")  # ID único

    try:
        # Subir los 3 PDF
        for tipo, archivo in archivos.items():
            if archivo and archivo.mimetype == "application/pdf":
                subir_a_blob(archivo, tipo, id_entrada)
            else:
                return jsonify({"error": f"El archivo {tipo} no es un PDF válido"}), 400

        # Subir metadata JSON
        subir_metadata(email, id_entrada)

        return jsonify({
            "message": "Archivos subidos correctamente",
            "ID_ENTRADA": id_entrada,
            "email": email
        }), 200

    except Exception as e:
        app.logger.error("Error al subir archivos")
        traceback.print_exc()
        return jsonify({"error": "Ocurrió un error al subir los archivos"}), 500


# ----------------------
# Ejecutar app
# ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
