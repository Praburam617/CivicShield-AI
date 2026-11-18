"""CivicShield AI — Database Reset & Seeding Utility
Safe one-time command-line utility to reset application demo data to a clean state.

Usage:
    python reset_database.py --confirm
"""

import sys
import os
import argparse

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Report, Evidence, ReportUpdate, Notification, AuditLog, PoliceStation, CrimeCategory, OfficerProfile
from config import Config

# Fictional Officer Directory Dataset (5 unique officers per station x 14 stations = 70 officers)
OFFICER_DIRECTORY_DATA = {
    'Madurai Town Police Station': [
        {'name': 'Arun Kumar', 'badge': 'DEMO-INSP-001', 'designation': 'Inspector', 'department': 'Law and Order', 'is_arun': True},
        {'name': 'Karthik Raj', 'badge': 'DEMO-SI-002', 'designation': 'Sub Inspector', 'department': 'Crime Investigation'},
        {'name': 'Vijay Kumar', 'badge': 'DEMO-SI-003', 'designation': 'Sub Inspector', 'department': 'Law and Order'},
        {'name': 'Suresh Babu', 'badge': 'DEMO-HC-004', 'designation': 'Head Constable', 'department': 'General Duty'},
        {'name': 'Priya Devi', 'badge': 'DEMO-SI-005', 'designation': 'Sub Inspector', 'department': 'Women & Child Protection'},
    ],
    'City Police Station': [
        {'name': 'Rajesh Kannan', 'badge': 'DEMO-INSP-006', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Meenakshi Sundaram', 'badge': 'DEMO-SI-007', 'designation': 'Sub Inspector', 'department': 'Crime Branch'},
        {'name': 'Vigneshwaran S', 'badge': 'DEMO-SI-008', 'designation': 'Sub Inspector', 'department': 'Traffic Enforcement'},
        {'name': 'Muthuvel P', 'badge': 'DEMO-HC-009', 'designation': 'Head Constable', 'department': 'General Duty'},
        {'name': 'Deepa Lakshmi', 'badge': 'DEMO-SI-010', 'designation': 'Sub Inspector', 'department': 'Community Policing'},
    ],
    'North District Police Station': [
        {'name': 'Senthil Nathan', 'badge': 'DEMO-INSP-011', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Anbarasan K', 'badge': 'DEMO-SI-012', 'designation': 'Sub Inspector', 'department': 'Crime Investigation'},
        {'name': 'Saravanan M', 'badge': 'DEMO-SI-013', 'designation': 'Sub Inspector', 'department': 'Patrol Division'},
        {'name': 'Murugan T', 'badge': 'DEMO-HC-014', 'designation': 'Head Constable', 'department': 'Station Operations'},
        {'name': 'Kavitha R', 'badge': 'DEMO-SI-015', 'designation': 'Sub Inspector', 'department': 'Women & Child Protection'},
    ],
    'South District Police Station': [
        {'name': 'Balasubramanian V', 'badge': 'DEMO-INSP-016', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Praveen Kumar', 'badge': 'DEMO-SI-017', 'designation': 'Sub Inspector', 'department': 'Crime Investigation'},
        {'name': 'Selvaraj N', 'badge': 'DEMO-SI-018', 'designation': 'Sub Inspector', 'department': 'Surveillance & Patrol'},
        {'name': 'Dharmaraj K', 'badge': 'DEMO-HC-019', 'designation': 'Head Constable', 'department': 'General Duty'},
        {'name': 'Revathi M', 'badge': 'DEMO-SI-020', 'designation': 'Sub Inspector', 'department': 'Public Grievances'},
    ],
    'East District Police Station': [
        {'name': 'Ilango G', 'badge': 'DEMO-INSP-021', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Ashok Chander', 'badge': 'DEMO-SI-022', 'designation': 'Sub Inspector', 'department': 'Crime Branch'},
        {'name': 'Manickam S', 'badge': 'DEMO-SI-023', 'designation': 'Sub Inspector', 'department': 'Law and Order'},
        {'name': 'Ganesan R', 'badge': 'DEMO-HC-024', 'designation': 'Head Constable', 'department': 'Station Records'},
        {'name': 'Sudha Mohan', 'badge': 'DEMO-SI-025', 'designation': 'Sub Inspector', 'department': 'Juvenile Aid'},
    ],
    'West District Police Station': [
        {'name': 'Velmurugan C', 'badge': 'DEMO-INSP-026', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Harishankar B', 'badge': 'DEMO-SI-027', 'designation': 'Sub Inspector', 'department': 'Crime Investigation'},
        {'name': 'Aravind Swamy', 'badge': 'DEMO-SI-028', 'designation': 'Sub Inspector', 'department': 'Patrol & Security'},
        {'name': 'Ramalingam P', 'badge': 'DEMO-HC-029', 'designation': 'Head Constable', 'department': 'General Duty'},
        {'name': 'Malathi Venkatesh', 'badge': 'DEMO-SI-030', 'designation': 'Sub Inspector', 'department': 'Crime Prevention'},
    ],
    'Central Police Station': [
        {'name': 'Natarajan K', 'badge': 'DEMO-INSP-031', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Dinesh Karthik', 'badge': 'DEMO-SI-032', 'designation': 'Sub Inspector', 'department': 'Special Crime Wing'},
        {'name': 'Mohanraj T', 'badge': 'DEMO-SI-033', 'designation': 'Sub Inspector', 'department': 'Night Patrol'},
        {'name': 'Palanisamy S', 'badge': 'DEMO-HC-034', 'designation': 'Head Constable', 'department': 'Dispatch & Records'},
        {'name': 'Gayathri Raman', 'badge': 'DEMO-SI-035', 'designation': 'Sub Inspector', 'department': 'Citizen Helpdesk'},
    ],
    'Cyber Crime Cell': [
        {'name': 'Arvind Swaminathan', 'badge': 'DEMO-INSP-036', 'designation': 'Inspector', 'department': 'Cyber Forensics'},
        {'name': 'Nithya Kalyani', 'badge': 'DEMO-SI-037', 'designation': 'Sub Inspector', 'department': 'Financial Fraud Unit'},
        {'name': 'Siddharth Menon', 'badge': 'DEMO-SI-038', 'designation': 'Sub Inspector', 'department': 'Digital Forensics'},
        {'name': 'Jayakumar R', 'badge': 'DEMO-HC-039', 'designation': 'Head Constable', 'department': 'Cyber Intelligence'},
        {'name': 'Lavanya Sundar', 'badge': 'DEMO-SI-040', 'designation': 'Sub Inspector', 'department': 'Social Media & Phishing'},
    ],
    'Women Police Station': [
        {'name': 'Jayanthi S', 'badge': 'DEMO-INSP-041', 'designation': 'Inspector', 'department': 'Women Safety Wing'},
        {'name': 'Bhavani Shankari', 'badge': 'DEMO-SI-042', 'designation': 'Sub Inspector', 'department': 'Family Counseling & Protection'},
        {'name': 'Sharmila Banu', 'badge': 'DEMO-SI-043', 'designation': 'Sub Inspector', 'department': 'Investigation Wing'},
        {'name': 'Karpagam M', 'badge': 'DEMO-HC-044', 'designation': 'Head Constable', 'department': 'Helpline Response'},
        {'name': 'Anitha Krishnan', 'badge': 'DEMO-SI-045', 'designation': 'Sub Inspector', 'department': 'Legal Aid & Liaison'},
    ],
    'Railway Police Station': [
        {'name': 'Thangavelu M', 'badge': 'DEMO-INSP-046', 'designation': 'Inspector', 'department': 'Railway Protection'},
        {'name': 'Boopathi Raj', 'badge': 'DEMO-SI-047', 'designation': 'Sub Inspector', 'department': 'Platform Security & Crime'},
        {'name': 'Chandrasekharan V', 'badge': 'DEMO-SI-048', 'designation': 'Sub Inspector', 'department': 'Transit Investigation'},
        {'name': 'Arumugam K', 'badge': 'DEMO-HC-049', 'designation': 'Head Constable', 'department': 'Beat Patrol'},
        {'name': 'Sandhya Devi', 'badge': 'DEMO-SI-050', 'designation': 'Sub Inspector', 'department': 'Passenger Assistance'},
    ],
    'Airport Police Station': [
        {'name': 'Raghavan E', 'badge': 'DEMO-INSP-051', 'designation': 'Inspector', 'department': 'Airport Security'},
        {'name': 'Kiran Kumar', 'badge': 'DEMO-SI-052', 'designation': 'Sub Inspector', 'department': 'Terminal Investigation'},
        {'name': 'Gautham Nair', 'badge': 'DEMO-SI-053', 'designation': 'Sub Inspector', 'department': 'Anti-Smuggling Liaison'},
        {'name': 'Subbiah N', 'badge': 'DEMO-HC-054', 'designation': 'Head Constable', 'department': 'Perimeter Security'},
        {'name': 'Hema Malini', 'badge': 'DEMO-SI-055', 'designation': 'Sub Inspector', 'department': 'Visitor Clearance & Protocol'},
    ],
    'Madurai Cyber Crime Cell': [
        {'name': 'Alagarsamy P', 'badge': 'DEMO-INSP-056', 'designation': 'Inspector', 'department': 'Cyber Crime Division'},
        {'name': 'Vigneshwaran R', 'badge': 'DEMO-SI-057', 'designation': 'Sub Inspector', 'department': 'Online Financial Fraud'},
        {'name': 'Thamarai Selvi', 'badge': 'DEMO-SI-058', 'designation': 'Sub Inspector', 'department': 'Cyber Security Analysis'},
        {'name': 'Pandian M', 'badge': 'DEMO-HC-059', 'designation': 'Head Constable', 'department': 'Digital Evidence Cell'},
        {'name': 'Manikandan K', 'badge': 'DEMO-SI-060', 'designation': 'Sub Inspector', 'department': 'Cyber Outreach'},
    ],
    'Chennai Central Police Station': [
        {'name': 'Rajendran B', 'badge': 'DEMO-INSP-061', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Sivakumar S', 'badge': 'DEMO-SI-062', 'designation': 'Sub Inspector', 'department': 'Crime Investigation'},
        {'name': 'Gokul Nath', 'badge': 'DEMO-SI-063', 'designation': 'Sub Inspector', 'department': 'Metropolitan Patrol'},
        {'name': 'Munusamy C', 'badge': 'DEMO-HC-064', 'designation': 'Head Constable', 'department': 'Law and Order'},
        {'name': 'Vijayalakshmi T', 'badge': 'DEMO-SI-065', 'designation': 'Sub Inspector', 'department': 'Crime Against Women'},
    ],
    'Coimbatore North Police Station': [
        {'name': 'Marimuthu K', 'badge': 'DEMO-INSP-066', 'designation': 'Inspector', 'department': 'Law and Order'},
        {'name': 'Anandha Krishnan', 'badge': 'DEMO-SI-067', 'designation': 'Sub Inspector', 'department': 'Crime Branch'},
        {'name': 'Santhosh Kumar', 'badge': 'DEMO-SI-068', 'designation': 'Sub Inspector', 'department': 'Industrial Zone Patrol'},
        {'name': 'Chinnasamy R', 'badge': 'DEMO-HC-069', 'designation': 'Head Constable', 'department': 'Station Operations'},
        {'name': 'Menaka Devi', 'badge': 'DEMO-SI-070', 'designation': 'Sub Inspector', 'department': 'Community Relations'},
    ]
}


def reset_database(confirmed=False):
    if not confirmed:
        print("[!] Confirmation required. Run with --confirm to execute reset.")
        return False

    app = create_app()
    with app.app_context():
        print("==================================================")
        print(" CIVICSHIELD AI — DATABASE RESET & SEEDING UTILITY")
        print("==================================================")
        print(f"Target Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

        # Ensure all tables exist
        db.create_all()

        print("[1/5] Purging old complaints, evidence, updates, and notifications...")
        # Maintain foreign key referential integrity during cleanup
        Evidence.query.delete()
        ReportUpdate.query.delete()
        Notification.query.delete()
        AuditLog.query.delete()
        Report.query.delete()
        OfficerProfile.query.delete()
        User.query.delete()
        db.session.commit()
        print("      -> Old complaint tables & user records cleared.")

        # Clean active protected upload directory (preserve folder itself)
        upload_folder = app.config.get('PROTECTED_UPLOAD_FOLDER')
        if upload_folder and os.path.exists(upload_folder):
            purged_files = 0
            for item in os.listdir(upload_folder):
                item_path = os.path.join(upload_folder, item)
                if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                        purged_files += 1
                    except Exception as e:
                        print(f"      [!] Warning: Could not remove {item_path}: {e}")
            print(f"      -> Purged {purged_files} old evidence files from active upload storage.")

        print("[2/5] Verifying & seeding Police Stations and Crime Categories...")
        # Ensure 14 stations exist
        for station_name in Config.POLICE_STATIONS:
            district = Config.STATION_DISTRICT_MAP.get(station_name, 'Central District')
            existing_ps = PoliceStation.query.filter_by(name=station_name).first()
            if not existing_ps:
                ps = PoliceStation(
                    name=station_name,
                    district=district,
                    address=f"{station_name}, {district}",
                    phone="044-28445500",
                    active=True
                )
                db.session.add(ps)

        # Ensure crime categories exist
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
            existing_cat = CrimeCategory.query.filter_by(name=name).first()
            if not existing_cat:
                cat = CrimeCategory(name=name, code=code, description=desc, active=True)
                db.session.add(cat)
        db.session.commit()
        print(f"      -> Police Stations ({PoliceStation.query.count()}) & Categories ({CrimeCategory.query.count()}) ready.")

        print("[3/5] Seeding exactly three initial demonstration accounts...")
        # 1. Administrator: Praburam
        admin = User(
            username='praburam',
            email='praburam@civicshield.example',
            full_name='Praburam',
            phone='9840112233',
            role='admin',
            is_admin=True,
            is_active=True
        )
        admin.set_password('Praburam@123')
        db.session.add(admin)

        # 2. Police Officer: Arun Kumar
        arun = User(
            username='arun',
            email='arun@civicshield.example',
            full_name='Arun Kumar',
            phone='9840998877',
            role='officer',
            badge_number='DEMO-INSP-001',
            department='Law and Order',
            police_station='Madurai Town Police Station',
            is_admin=False,
            is_active=True
        )
        arun.set_password('Arun@123')
        db.session.add(arun)

        # 3. Citizen: Surya
        surya = User(
            username='surya',
            email='surya@civicshield.example',
            full_name='Surya',
            phone='9840554433',
            role='citizen',
            is_admin=False,
            is_active=True
        )
        surya.set_password('surya@123')
        db.session.add(surya)

        db.session.commit()
        print("      -> Initial accounts created: praburam (Admin), arun (Officer), surya (Citizen).")

        print("[4/5] Seeding 5 unique fictional officer profiles for all 14 stations (70 total)...")
        seeded_officers = 0
        for station_name, officers in OFFICER_DIRECTORY_DATA.items():
            for off_data in officers:
                is_arun = off_data.get('is_arun', False)
                profile = OfficerProfile(
                    name=off_data['name'],
                    badge_number=off_data['badge'],
                    designation=off_data['designation'],
                    department=off_data['department'],
                    police_station=station_name,
                    is_available=True,
                    active_case_count=0,
                    user_id=arun.id if is_arun else None
                )
                db.session.add(profile)
                seeded_officers += 1

        db.session.commit()
        print(f"      -> Created {seeded_officers} officer directory profiles (only Arun Kumar linked to login user).")

        print("[5/5] Recording audit log entry...")
        audit = AuditLog(
            user_id=admin.id,
            action='SYSTEM_DATABASE_RESET',
            resource_type='database',
            resource_id='0',
            details='One-time demo database reset performed. 3 user accounts seeded, 70 officer profiles seeded, complaints set to 0.',
            ip_address='127.0.0.1'
        )
        db.session.add(audit)
        db.session.commit()

        # Final Summary Verification
        print("--------------------------------------------------")
        print("RESET SUMMARY:")
        print(f"  Complaints:       {Report.query.count()} (Must be 0)")
        print(f"  Active Users:     {User.query.count()} (Must be 3: praburam, arun, surya)")
        print(f"  Officer Profiles: {OfficerProfile.query.count()} (Must be 70)")
        print(f"  Linked Officers:  {OfficerProfile.query.filter(OfficerProfile.user_id.isnot(None)).count()} (Must be 1: Arun Kumar)")
        print(f"  Police Stations:  {PoliceStation.query.count()} (Must be 14)")
        print(f"  Categories:       {CrimeCategory.query.count()} (Must be 14)")
        print("==================================================")
        print("[SUCCESS] Database reset and seeding completed cleanly!")
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reset CivicShield AI Database')
    parser.add_argument('--confirm', action='store_true', help='Confirm execution of database reset')
    args = parser.parse_args()

    if not args.confirm:
        print("\n[CAUTION] This command resets all complaint and user demo data.")
        print("Run with --confirm flag: python reset_database.py --confirm\n")
        sys.exit(1)

    reset_database(confirmed=True)
