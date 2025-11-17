from flask import Flask, request, jsonify, render_template
import os
import json
import re
import traceback
from datetime import datetime
import msal
import requests
# Agregar carga de variables de entorno desde .env (útil en desarrollo local)
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# -----------------------------
# Cargar credenciales SharePoint
# -----------------------------
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID", "246e9e0b-5e48-4497-9488-61953e2249f5")
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID", "72beb247-1940-465a-9f09-12ead802ba76")
# CORRECCIÓN: leer la variable de entorno por su nombre. No usar el secreto como clave.
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET")
if not SHAREPOINT_CLIENT_SECRET:
    # Opcional: levantar excepción temprana si no está configurado
    raise RuntimeError("Falta la variable de entorno SHAREPOINT_CLIENT_SECRET")

SHAREPOINT_HOST = "caiasa.sharepoint.com"
SHAREPOINT_SITE_PATH = "sites/PortalFacturas"
SHAREPOINT_DOC_LIB = "Documentos_Recibidos"

GRAPH_API = "https://graph.microsoft.com/v1.0"


# -----------------------------
# Obtener token (App Only)
# -----------------------------
def get_access_token():
    authority = f"https://login.microsoftonline.com/{SHAREPOINT_TENANT_ID}"
    app_msal = msal.ConfidentialClientApplication(
        client_id=SHAREPOINT_CLIENT_ID,
        client_credential=SHAREPOINT_CLIENT_SECRET,
        authority=authority
    )

    result = app_msal.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )

    if not result or "access_token" not in result:
        raise Exception("Error obteniendo token: " + str(result))

    return result["access_token"]


# -----------------------------
# Utilidades SharePoint
# -----------------------------
def get_site_id(token):
    url = f"{GRAPH_API}/sites/{SHAREPOINT_HOST}:/{SHAREPOINT_SITE_PATH}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise Exception(f"Error obteniendo site id ({r.status_code}): {r.text}")
    data = r.json()
    return data.get("id")


def get_drive_id(token, site_id):
    url = f"{GRAPH_API}/sites/{site_id}/drives"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        raise Exception(f"Error obteniendo drives ({r.status_code}): {r.text}")
    drives = r.json().get("value", [])
    for d in drives:
        if d.get("name") == SHAREPOINT_DOC_LIB:
            return d.get("id")
    raise Exception("No se encontró la Document Library")


def upload_file(token, drive_id, folder, filename, file_stream):
    if file_stream is None:
        # No hay nada que subir
        return

    upload_url = f"{GRAPH_API}/drives/{drive_id}/root:/{SHAREPOINT_DOC_LIB}/{folder}/{filename}:/content"

    r = requests.put(
        upload_url,
        data=file_stream,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
    )

    if r.status_code not in [200, 201]:
        raise Exception(f"Error subiendo archivo ({r.status_code}): {r.text}")


# -----------------------------
# Obtener ID autoincremental
# -----------------------------
def get_next_id(token, drive_id):
    counter_path = f"{GRAPH_API}/drives/{drive_id}/root:/{SHAREPOINT_DOC_LIB}/metadata/counter.json:/content"
    r = requests.get(counter_path, headers={"Authorization": f"Bearer {token}"})

    if r.status_code == 200:
        data = json.loads(r.text)
        last_id = data.get("last_id", 0)
    else:
        last_id = 0

    new_id = last_id + 1
    counter_json = json.dumps({"last_id": new_id})

    put_r = requests.put(
        counter_path,
        data=counter_json,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    if put_r.status_code not in [200,201]:
        # No fatal, pero dejar rastro
        app.logger.warning("No se pudo actualizar counter.json: %s", put_r.text)

    return new_id


# -----------------------------
# Validación email
# -----------------------------
def valid_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


# -----------------------------
# Rutas
# -----------------------------
@app.route("/")
def index():
    return render_template("formulario.html")


@app.route("/api/upload", methods=["POST"])
def api_upload():
    try:
        email = request.form.get("email")
        factura = request.files.get("factura")
        orden = request.files.get("orden")
        remision = request.files.get("remision")

        if not valid_email(email):
            return jsonify({"error": "Correo inválido"}), 400

        token = get_access_token()
        site_id = get_site_id(token)
        drive_id = get_drive_id(token, site_id)

        # generar ID
        id_entrada = get_next_id(token, drive_id)

        documentos = {
            "factura": factura,
            "orden": orden,
            "remision": remision
        }

        for tipo, archivo in documentos.items():
            if archivo:
                nombre_final = f"{tipo}_{id_entrada}.pdf"
                upload_file(token, drive_id, tipo, nombre_final, archivo.read())
            else:
                app.logger.info("No se proporcionó archivo para %s, se omite.", tipo)

        # metadata JSON
        metadata = {
            "IDEntrada": id_entrada,
            "email": email,
            "fecha_subida": datetime.now().isoformat()
        }

        upload_file(
            token,
            drive_id,
            "metadata",
            f"metadata_{id_entrada}.json",
            json.dumps(metadata, indent=2).encode("utf-8")
        )

        return jsonify({
            "message": "Archivos enviados correctamente",
            "ID_ENTRADA": id_entrada
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Usar puerto y debug configurables por entorno
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
