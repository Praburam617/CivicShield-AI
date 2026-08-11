import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app/static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Police stations (example data)
    POLICE_STATIONS = [
        'City Police Station',
        'North District Police Station',
        'South District Police Station',
        'East District Police Station',
        'West District Police Station',
        'Central Police Station',
        'Cyber Crime Cell',
        'Women Police Station',
        'Railway Police Station',
        'Airport Police Station'
    ]
    
    # Crime categories
    CRIME_CATEGORIES = [
        'Theft',
        'Robbery',
        'Assault',
        'Burglary',
        'Cyber Crime',
        'Fraud',
        'Domestic Violence',
        'Sexual Harassment',
        'Kidnapping',
        'Murder',
        'Drug Offense',
        'Traffic Violation',
        'Other'
    ]