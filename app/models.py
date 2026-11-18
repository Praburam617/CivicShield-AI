from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    # Aadhar is optional for privacy/security minimization, preserved if present in legacy rows
    aadhar_number = db.Column(db.String(12), unique=True, nullable=True)
    
    # Role-Based Access Control: 'citizen', 'officer', 'admin'
    role = db.Column(db.String(20), default='citizen', nullable=False, index=True)
    badge_number = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    police_station = db.Column(db.String(100), nullable=True)
    
    # Legacy compatibility flag
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reports = db.relationship('Report', foreign_keys='Report.user_id', backref='complainant', lazy=True)
    assigned_reports = db.relationship('Report', foreign_keys='Report.assigned_officer_id', backref='officer_user', lazy=True)
    notifications = db.relationship('Notification', backref='recipient', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin_user(self):
        return self.role == 'admin' or bool(self.is_admin)

    @property
    def is_officer(self):
        return self.role == 'officer'

    @property
    def is_citizen(self):
        return self.role == 'citizen' and not self.is_admin_user

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Report(db.Model):
    __tablename__ = 'report'

    id = db.Column(db.Integer, primary_key=True)
    complaint_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # Core Complaint Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    crime_category = db.Column(db.String(50), nullable=False, index=True)
    incident_date = db.Column(db.DateTime, nullable=False)
    
    # Location Hierarchy
    district = db.Column(db.String(100), default='Central District', nullable=False, index=True)
    incident_location = db.Column(db.String(200), nullable=False)
    police_station = db.Column(db.String(100), nullable=False, index=True)

    # Legacy evidence file reference (single file string preserved for legacy db rows)
    evidence_file = db.Column(db.String(255), nullable=True)

    # Status tracking & workflow
    # Allowed: Pending, Verified, Assigned, Under Investigation, Evidence Collected, Action Required, Resolved, Rejected, Closed
    status = db.Column(db.String(30), default='Pending', nullable=False, index=True)
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Assigned officer text (legacy compatibility) and foreign keys
    assigned_officer = db.Column(db.String(100), nullable=True)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    officer_profile_id = db.Column(db.Integer, db.ForeignKey('officer_profile.id'), nullable=True, index=True)

    # Notes & Remarks
    admin_remarks = db.Column(db.Text, nullable=True)
    is_draft = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    evidence_items = db.relationship('Evidence', backref='report', lazy=True, cascade='all, delete-orphan')
    updates = db.relationship('ReportUpdate', backref='report', lazy=True, cascade='all, delete-orphan', order_by='ReportUpdate.created_at.asc()')
    notifications = db.relationship('Notification', backref='report', lazy=True)
    assigned_officer_profile = db.relationship('OfficerProfile', foreign_keys=[officer_profile_id], backref=db.backref('assigned_reports', lazy=True))

    def __repr__(self):
        return f'<Report {self.complaint_number} - {self.status}>'


class Evidence(db.Model):
    __tablename__ = 'evidence'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Evidence {self.id} for Report #{self.report_id}>'


class ReportUpdate(db.Model):
    __tablename__ = 'report_update'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def __repr__(self):
        return f'<ReportUpdate #{self.id} Status: {self.status}>'


class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), default='status_update')
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Notification #{self.id} for User #{self.user_id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog #{self.id} {self.action} by User #{self.user_id}>'


class PoliceStation(db.Model):
    __tablename__ = 'police_station'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    district = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<PoliceStation {self.name} ({self.district})>'


class CrimeCategory(db.Model):
    __tablename__ = 'crime_category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    code = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CrimeCategory {self.name}>'


class OfficerProfile(db.Model):
    __tablename__ = 'officer_profile'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    badge_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    designation = db.Column(db.String(80), nullable=False)  # Inspector, Sub Inspector, Head Constable, etc.
    department = db.Column(db.String(100), default='Law and Order', nullable=False)
    police_station = db.Column(db.String(100), nullable=False, index=True)
    is_available = db.Column(db.Boolean, default=True, nullable=False, index=True)
    active_case_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Optional linked login account
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to user
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('officer_profile', uselist=False))

    @property
    def has_account(self):
        return self.user_id is not None and self.user is not None

    def recalculate_active_cases(self):
        """Recalculate active case count from non-resolved assigned reports."""
        count = Report.query.filter(
            Report.officer_profile_id == self.id,
            Report.is_draft == False,
            ~Report.status.in_(['Resolved', 'Closed', 'Rejected'])
        ).count()
        self.active_case_count = count
        return count

    def __repr__(self):
        return f'<OfficerProfile {self.designation} {self.name} - {self.badge_number} ({self.police_station})>'

