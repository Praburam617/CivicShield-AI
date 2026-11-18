import os
import sys
import argparse
from app import create_app, db
from app.models import User, Report, ReportUpdate, PoliceStation, CrimeCategory
from config import Config


def setup_cli():
    parser = argparse.ArgumentParser(description="CivicShield AI Management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # create-admin
    admin_parser = subparsers.add_parser("create-admin", help="Create or update an administrator account safely")
    admin_parser.add_argument("--username", default=os.environ.get('ADMIN_USERNAME', 'admin'))
    admin_parser.add_argument("--email", default=os.environ.get('ADMIN_EMAIL', 'admin@civicshield.local'))
    admin_parser.add_argument("--password", default=os.environ.get('ADMIN_PASSWORD'))
    admin_parser.add_argument("--name", default=os.environ.get('ADMIN_FULL_NAME', 'System Administrator'))

    # create-officer
    officer_parser = subparsers.add_parser("create-officer", help="Create a police officer account")
    officer_parser.add_argument("--username", required=True)
    officer_parser.add_argument("--email", required=True)
    officer_parser.add_argument("--password", required=True)
    officer_parser.add_argument("--name", required=True)
    officer_parser.add_argument("--badge", default="TN-POL-042")
    officer_parser.add_argument("--station", default="Central Police Station")

    # seed-demo
    subparsers.add_parser("seed-demo", help="Seed representative demonstration complaints")

    # retrain-ai
    subparsers.add_parser("retrain-ai", help="Retrain AI complaint classifier model")

    return parser


def cmd_create_admin(args):
    app = create_app()
    with app.app_context():
        username = args.username
        email = args.email
        password = args.password or os.environ.get('ADMIN_PASSWORD')
        name = args.name

        if not password:
            import getpass
            print(f"Creating administrator account '{username}'")
            password = getpass.getpass("Enter secure admin password: ")
            confirm = getpass.getpass("Confirm admin password: ")
            if password != confirm:
                print("Error: Passwords do not match.")
                sys.exit(1)

        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            user.role = 'admin'
            user.is_admin = True
            user.is_active = True
            user.set_password(password)
            db.session.commit()
            print(f"Updated existing user '{user.username}' as Administrator.")
        else:
            user = User(
                username=username,
                email=email,
                full_name=name,
                role='admin',
                is_admin=True,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"Created new Administrator '{user.username}' ({user.email}).")


def cmd_create_officer(args):
    app = create_app()
    with app.app_context():
        user = User.query.filter((User.username == args.username) | (User.email == args.email)).first()
        if user:
            user.role = 'officer'
            user.badge_number = args.badge
            user.police_station = args.station
            user.set_password(args.password)
            db.session.commit()
            print(f"Updated user '{user.username}' as Police Officer.")
        else:
            user = User(
                username=args.username,
                email=args.email,
                full_name=args.name,
                role='officer',
                badge_number=args.badge,
                police_station=args.station,
                is_admin=False,
                is_active=True
            )
            user.set_password(args.password)
            db.session.add(user)
            db.session.commit()
            print(f"Created Officer '{user.username}' ({user.badge_number}) at {user.police_station}.")


def cmd_retrain_ai():
    from app.ai.classifier import get_classifier
    clf = get_classifier()
    res = clf.train_and_save()
    print("Retrained AI Classifier:", res)


if __name__ == '__main__':
    parser = setup_cli()
    args = parser.parse_args()

    if args.command == 'create-admin':
        cmd_create_admin(args)
    elif args.command == 'create-officer':
        cmd_create_officer(args)
    elif args.command == 'retrain-ai':
        cmd_retrain_ai()
    else:
        parser.print_help()
