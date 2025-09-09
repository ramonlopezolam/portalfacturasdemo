from flask import Flask, request, render_template, flash, redirect
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
    files = {}
    for tipo, archivo in archivos.items():
        if archivo and allowed_file(archivo.filename):
            archivo.stream.seek(0)
            files['file'] = (archivo.filename, archivo.stream, 'application/pdf')  # Usar solo uno a la vez
            data = {'email': email}
            response = requests.post(url, data=data, files=files, headers=headers)
            if response.status_code != 200:
                raise Exception(f"{tipo} falló: {response.text}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        factura = request.files.get('factura')
        orden = request.files.get('orden')
        remision = request.files.get('remision')

        if not email or not valid_email(email):
            flash('Correo no válido')
            return redirect(request.url)

        archivos = {'Factura': factura, 'Orden': orden, 'Remision': remision}
        try:
            enviar_a_servidor_local(email, archivos)
            flash('Archivos enviados correctamente.')
        except Exception as e:
            flash(f'Error: {str(e)}')

        return redirect(request.url)

    return render_template('formulario.html')

if __name__ == '__main__':
    app.run()
