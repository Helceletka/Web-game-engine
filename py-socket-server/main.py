# Web-game-engine is a simple web platform allowing you to design multiplayer games that communicate over a local network.
# This is the server-side code that runs on the host computer. This code is written in Python and uses Flask and SocketIO.
# The client-side code is written in JavaScript, and it is served by the server-side code.

import webbrowser
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO, emit
from engineio.async_drivers import gevent
import json
import os
import sys
import socket
from database import Database

PORT = 80
DATAFILE = 'data.json'

ALLOWED_EXTENSIONS = {'json'}

if getattr(sys, 'frozen', False):
    # frozen
    ROOT_DIR = os.path.dirname(sys.executable)
    TEMPLATES_DIR = os.path.join(sys._MEIPASS, 'templates')
    STATIC_DIR = os.path.join(sys._MEIPASS, 'static')
    DEBUG = False
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATES_DIR = os.path.join(ROOT_DIR, 'templates')
    STATIC_DIR = os.path.join(ROOT_DIR, 'static')
    DEBUG = True

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize the database
db = Database(ROOT_DIR, DATAFILE)
data_storage = db.read_data()

# Function to get the local network IP address
def get_local_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address

# Get local IP
local_ip = f'http://{get_local_ip_address()}:{PORT}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/udavac')
def udavac():
    return render_template('udavac.html')

@app.route('/admin')
def admin():
    return render_template('admin.html', data=data_storage, ip_address=local_ip)

@app.route('/download_data')
def download_data():
    return send_from_directory(ROOT_DIR, DATAFILE, as_attachment=True)

@app.route('/clear_data')
def clear_data():
    global data_storage
    data_storage = {}
    db.write_data(data_storage)
    return jsonify({"status": "success"})

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_data', methods=['POST'])
def upload_data():
    global data_storage
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})

    if file and allowed_file(file.filename):
        print(f'Uploading file {file.filename} that will overwrite the current data')
        data_storage= db.save_file(file)

        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Invalid file type"})

@socketio.on('send_admin_message')
def handle_admin_message(message):
    emit('admin_messages', message, broadcast=True)

connected_clients = 0
@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients += 1
    emit('update_clients', {'count': connected_clients}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global connected_clients
    connected_clients -= 1
    emit('update_clients', {'count': connected_clients}, broadcast=True)

@socketio.on('set')
def handle_set(json):
    key = json.get('key')
    value = json.get('value')
    data_storage[key] = value
    db.write_data(data_storage)
    return {'status': 'success'}

@socketio.on('get')
def handle_get(key):
    return {'value': data_storage.get(key)}

@socketio.on('edit_data')
def handle_edit_data(json):
    key = json.get('key')
    value = json.get('value')
    data_storage[key] = value
    db.write_data(data_storage)
    return {'status': 'success'}

@socketio.on('delete_data')
def handle_delete_data(key):
    if key in data_storage:
        del data_storage[key]
        db.write_data(data_storage)
        return {'status': 'success'}
    return {'status': 'error', 'message': 'Key not found'}

if __name__ == '__main__':
    if not DEBUG:
        webbrowser.open(f'http://localhost:{PORT}/admin')
        webbrowser.open(f'http://localhost:{PORT}')

    # stop the server with Ctrl-C
    try:
        print(f'Server started at {local_ip}')
        socketio.run(app, debug=DEBUG, host='0.0.0.0', port=PORT)
    except KeyboardInterrupt:
        print('Server stopped')
        sys.exit(0)
