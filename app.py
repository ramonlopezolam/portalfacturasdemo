from flask import Flask, request, jsonify, render_template
import re
import requests

app = Flask(__name__)
app.secret_key = 'clave_secreta'

# Validaciones
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Enviar a servidor local a través de Hybrid Connection
def enviar_a_servidor_local(email, archivos):
    url = "http://hybrydportalfacturas-app:5001/upload"
    headers = {
        'Authorization': 'Bearer 9f82a7f1-2341-456c-b812-9abcde123457'
    }
    for tipo, archivo in archivos.items():
        if archivo and allowed_file(archivo.filename):
            archivo.stream.seek(0)
            files = {'file': (archivo.filename, archivo.stream, 'application/pdf')}
            data = {'email': email}
            response = requests.post(url, data=data, files=files, headers=headers)
            if response.status_code != 200:
                raise Exception(f"{tipo} falló: {response.text}")

@app.route('/')
def index():
    return render_template('formulario.html')

# ✅ API dedicada para subir archivos
@app.route('/api/upload', methods=['POST'])
def api_upload():
    email = request.form.get('email')
    factura = request.files.get('factura')
    orden = request.files.get('orden')
    remision = request.files.get('remision')

    if not email or not valid_email(email):
        return jsonify({'error': 'Correo no válido'}), 400

    archivos = {'Factura': factura, 'Orden': orden, 'Remision': remision}
    try:
        enviar_a_servidor_local(email, archivos)
        return jsonify({'mensaje': 'Archivos enviados correctamente'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run()
