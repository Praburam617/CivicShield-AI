import os
import shutil
from sqlalchemy import text, inspect
from config import Config


def ensure_directories(app):
    """Ensure all required runtime directories exist."""
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    os.makedirs(app.config['PROTECTED_UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AI_ARTIFACTS_DIR'], exist_ok=True)

    # Copy legacy uploads to protected upload folder if not already copied
    legacy_folder = app.config.get('LEGACY_UPLOAD_FOLDER')
    protected_folder = app.config['PROTECTED_UPLOAD_FOLDER']
    if legacy_folder and os.path.isdir(legacy_folder):
        for item in os.listdir(legacy_folder):
            src = os.path.join(legacy_folder, item)
            dst = os.path.join(protected_folder, item)
            if os.path.isfile(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass


def migrate_database_schema(db):
    """Safely apply schema additions to existing SQLite or MySQL databases without losing data."""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    with db.engine.connect() as conn:
        # Check user table columns
        if 'user' in tables:
            user_cols = {col['name'] for col in inspector.get_columns('user')}
            if 'role' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'citizen'"))
                conn.commit()
            if 'badge_number' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN badge_number VARCHAR(50)"))
                conn.commit()
            if 'department' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN department VARCHAR(100)"))
                conn.commit()
            if 'police_station' not in user_cols:
                conn.execute(text("ALTER TABLE user ADD COLUMN police_station VARCHAR(100)"))
                conn.commit()

            # Synchronize admin role
            conn.execute(text("UPDATE user SET role = 'admin' WHERE is_admin = 1 AND (role IS NULL OR role = 'citizen')"))
            conn.commit()

        # Check report table columns
        if 'report' in tables:
            report_cols = {col['name'] for col in inspector.get_columns('report')}
            if 'district' not in report_cols:
                conn.execute(text("ALTER TABLE report ADD COLUMN district VARCHAR(100) DEFAULT 'Central District'"))
                conn.commit()
            if 'assigned_officer_id' not in report_cols:
                conn.execute(text("ALTER TABLE report ADD COLUMN assigned_officer_id INTEGER"))
                conn.commit()
            if 'officer_profile_id' not in report_cols:
                conn.execute(text("ALTER TABLE report ADD COLUMN officer_profile_id INTEGER"))
                conn.commit()
            if 'is_draft' not in report_cols:
                conn.execute(text("ALTER TABLE report ADD COLUMN is_draft BOOLEAN DEFAULT 0"))
                conn.commit()

        # Check report_update table columns
        if 'report_update' in tables:
            update_cols = {col['name'] for col in inspector.get_columns('report_update')}
            if 'is_internal' not in update_cols:
                conn.execute(text("ALTER TABLE report_update ADD COLUMN is_internal BOOLEAN DEFAULT 0"))
                conn.commit()
            if 'updated_by_id' not in update_cols:
                conn.execute(text("ALTER TABLE report_update ADD COLUMN updated_by_id INTEGER"))
                conn.commit()


def seed_reference_data(db):
    """Seed initial categories, stations, and backfill legacy evidence files."""
    from app.models import PoliceStation, CrimeCategory, Report, Evidence

    # Seed police stations
    if PoliceStation.query.count() == 0:
        for station_name in Config.POLICE_STATIONS:
            district = Config.STATION_DISTRICT_MAP.get(station_name, 'Central District')
            ps = PoliceStation(
                name=station_name,
                district=district,
                address=f"{station_name}, {district}",
                phone="044-28445500",
                active=True
            )
            db.session.add(ps)
        db.session.commit()

    # Seed crime categories
    if CrimeCategory.query.count() == 0:
        category_descriptions = {
            'Theft': 'Unlawful taking of personal property without force',
            'Cyber Crime': 'Online fraud, phishing, identity theft, unauthorized access, hacking',
            'Assault': 'Physical attack or threat of physical harm against an individual',
            'Robbery': 'Taking property by force, threat, or intimidation',
            'Burglary': 'Illegal entry into a building with intent to commit a crime',
            'Domestic Violence': 'Abuse or violence occurring in a domestic setting',
            'Fraud': 'Deception intended to result in financial or personal gain',
            'Sexual Harassment': 'Unwelcome sexual advances, requests, or verbal/physical conduct',
            'Kidnapping': 'Unlawful abduction and detention of a person against their will',
            'Murder': 'Unlawful premeditated killing of a human being',
            'Drug Offense': 'Possession, trafficking, or distribution of illegal substances',
            'Traffic Violation': 'Reckless driving, hit and run, or major vehicle offenses',
            'Vandalism': 'Deliberate destruction or damage to public or private property',
            'Other': 'General grievances and miscellaneous criminal incidents'
        }
        for name in Config.CRIME_CATEGORIES:
            code = name.upper().replace(' ', '_')
            desc = category_descriptions.get(name, f'Reporting and investigation of {name} incidents')
            cat = CrimeCategory(name=name, code=code, description=desc, active=True)
            db.session.add(cat)
        db.session.commit()

    # Backfill legacy single evidence_file entries into the Evidence table
    reports_with_legacy_evidence = Report.query.filter(Report.evidence_file.isnot(None), Report.evidence_file != '').all()
    for rep in reports_with_legacy_evidence:
        existing_evidence = Evidence.query.filter_by(report_id=rep.id).first()
        if not existing_evidence:
            ext = os.path.splitext(rep.evidence_file)[1].lower()
            mime = 'application/pdf' if ext == '.pdf' else 'image/jpeg'
            ev = Evidence(
                report_id=rep.id,
                filename=rep.evidence_file,
                original_filename=rep.evidence_file,
                file_type=mime,
                file_size=0,
                uploaded_at=rep.created_at
            )
            db.session.add(ev)
    db.session.commit()
