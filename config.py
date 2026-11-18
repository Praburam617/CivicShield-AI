import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'civicshield-ai-secure-dev-key-change-in-prod-2026'
    
    # Database
    # Supports MySQL (mysql+pymysql://user:password@localhost/civicshield) or SQLite fallback
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Storage & Uploads
    LEGACY_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    PROTECTED_UPLOAD_FOLDER = os.environ.get('PROTECTED_UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'instance', 'protected_uploads')
    UPLOAD_FOLDER = PROTECTED_UPLOAD_FOLDER  # default active upload folder
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
    ALLOWED_MIME_TYPES = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
        'application/pdf': '.pdf'
    }

    # Rate Limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', "300 per day; 60 per hour")
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', "memory://")
    RATELIMIT_STRATEGY = 'fixed-window'

    # AI Configuration
    AI_ARTIFACTS_DIR = os.path.join(BASE_DIR, 'app', 'ai', 'artifacts')
    AI_MODEL_PATH = os.path.join(AI_ARTIFACTS_DIR, 'complaint_classifier.joblib')
    OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434/api/generate')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')

    # Configured Districts
    DISTRICTS = [
        'Central District',
        'North District',
        'South District',
        'East District',
        'West District',
        'Chennai',
        'Madurai',
        'Coimbatore',
        'Tiruchirappalli',
        'Salem'
    ]

    # Police stations (name -> district)
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
        'Airport Police Station',
        'Madurai Town Police Station',
        'Madurai Cyber Crime Cell',
        'Chennai Central Police Station',
        'Coimbatore North Police Station'
    ]

    STATION_DISTRICT_MAP = {
        'City Police Station': 'Central District',
        'North District Police Station': 'North District',
        'South District Police Station': 'South District',
        'East District Police Station': 'East District',
        'West District Police Station': 'West District',
        'Central Police Station': 'Central District',
        'Cyber Crime Cell': 'Central District',
        'Women Police Station': 'Central District',
        'Railway Police Station': 'Central District',
        'Airport Police Station': 'South District',
        'Madurai Town Police Station': 'Madurai',
        'Madurai Cyber Crime Cell': 'Madurai',
        'Chennai Central Police Station': 'Chennai',
        'Coimbatore North Police Station': 'Coimbatore'
    }

    # Controlled crime categories
    CRIME_CATEGORIES = [
        'Theft',
        'Cyber Crime',
        'Assault',
        'Robbery',
        'Burglary',
        'Domestic Violence',
        'Fraud',
        'Sexual Harassment',
        'Kidnapping',
        'Murder',
        'Drug Offense',
        'Traffic Violation',
        'Vandalism',
        'Other'
    ]

    STATUS_CHOICES = [
        'Pending',
        'Verified',
        'Assigned',
        'Under Investigation',
        'Evidence Collected',
        'Action Required',
        'Resolved',
        'Rejected',
        'Closed'
    ]
