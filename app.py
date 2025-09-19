from flask import Flask, request, render_template, jsonify
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
import re
from dotenv import load_dotenv
import traceback  # Para ver detalles completos de los errores

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
    blob_client = blob_service_client.get_blob_client(
        container=BLOB_CONTAINER,
        blob=f"{carpeta}/{carpeta}_{id_entrada}_{archivo.filename}"
    )
    archivo.stream.seek(0)
    blob_client.upload_blob(archivo.stream, overwrite=True)

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
    # Generar ID_ENTRADA único (puede ser timestamp o GUID)
    id_entrada = datetime.now().strftime("%Y%m%d%H%M%S")

    try:
        for tipo, archivo in archivos.items():
            if archivo and archivo.mimetype == "application/pdf":
                subir_a_blob(archivo, tipo, id_entrada)
            else:
                return jsonify({"error": f"El archivo {tipo} no es un PDF válido"}), 400

        return jsonify({"message": "Archivos subidos correctamente", "ID_ENTRADA": id_entrada}), 200

    except Exception as e:
        app.logger.error("Error al subir archivos")
        traceback.print_exc()
        return jsonify({"error": "Ocurrió un error al subir los archivos"}), 500


# ----------------------
# Ejecutar app
# ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
