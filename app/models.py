from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    aadhar_number = db.Column(db.String(12), unique=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reports = db.relationship('Report', backref='complainant', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Report details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    crime_category = db.Column(db.String(50), nullable=False)
    incident_date = db.Column(db.DateTime, nullable=False)
    incident_location = db.Column(db.String(200), nullable=False)
    
    # Police station info
    police_station = db.Column(db.String(100), nullable=False)
    
    # Evidence
    evidence_file = db.Column(db.String(200))
    
    # Status tracking
    status = db.Column(db.String(20), default='Pending')
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_officer = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Admin remarks
    admin_remarks = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Report {self.complaint_number}>'

class ReportUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False)
    status = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    report = db.relationship('Report', backref='updates', lazy=True)