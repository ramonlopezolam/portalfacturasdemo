from flask import Flask, render_template, request, redirect, flash
import re
import requests

app = Flask(__name__)
app.secret_key = 'clave_secreta_1234'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def enviar_a_servidor_local(email, archivos):
    url_local = 'http://192.168.10.14:5001/upload'
    files = {}
    for tipo, archivo in archivos.items():
        if archivo and allowed_file(archivo.filename):
            archivo.stream.seek(0)
            files[tipo] = (archivo.filename, archivo.stream, 'application/pdf')

    data = {'email': email}
    headers = {'Authorization': 'Bearer 9f82a7f1-2341-456c-b812-9abcde123457'}

    response = requests.post(url_local, files=files, data=data, headers=headers)
    return response

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        email = request.form.get('email')
        factura = request.files.get('factura')
        orden = request.files.get('orden')
        remision = request.files.get('remision')

        if not email or not valid_email(email):
            flash('Correo electrónico no válido.')
            return redirect(request.url)

        archivos = {
            'Factura': factura,
            'Orden': orden,
            'Remision': remision
        }

        try:
            response = enviar_a_servidor_local(email, archivos)
            if response.status_code == 200:
                flash('Archivos enviados correctamente al servidor local.')
            else:
                flash(f'Error en el servidor local: {response.status_code} - {response.text}')
        except Exception as e:
            flash(f'Error de conexión con el servidor local: {str(e)}')

        return redirect(request.url)

    return render_template('formulario.html')

if __name__ == "__main__":
    app.run()