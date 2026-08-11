import os
from werkzeug.utils import secure_filename
from config import Config


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_attachment(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(path)
        return filename
    return None
