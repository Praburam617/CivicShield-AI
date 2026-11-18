from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    SelectField, DateTimeLocalField, BooleanField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Optional, ValidationError, Regexp
)
from config import Config
from app.models import User


class RegistrationForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(message="Username is required"),
            Length(min=3, max=80, message="Username must be between 3 and 80 characters"),
            Regexp(r'^[a-zA-Z0-9_.-]+$', message="Username can only contain letters, numbers, dots, and underscores")
        ]
    )
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message="Email address is required"),
            Regexp(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message="Please enter a valid email address"),
            Length(max=120)
        ]
    )
    full_name = StringField(
        'Full Name',
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Full name must be between 2 and 100 characters")
        ]
    )
    phone = StringField(
        'Mobile Phone Number',
        validators=[
            DataRequired(message="Phone number is required"),
            Length(min=10, max=15, message="Phone number should be between 10 and 15 digits"),
            Regexp(r'^\+?[0-9\s-]+$', message="Please enter a valid phone number")
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required"),
            Length(min=6, message="Password must be at least 6 characters long")
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo('password', message="Passwords must match")
        ]
    )
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        user = User.query.filter(User.username.ilike(field.data.strip())).first()
        if user:
            raise ValidationError("This username is already taken. Please choose another.")

    def validate_email(self, field):
        user = User.query.filter(User.email.ilike(field.data.strip())).first()
        if user:
            raise ValidationError("This email address is already registered. Please log in.")


class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired(message="Please enter your username or email")])
    password = PasswordField('Password', validators=[DataRequired(message="Please enter your password")])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ComplaintForm(FlaskForm):
    """Guided Complaint Submission Form covering Steps 1 to 4."""
    # Step 1: Incident Info
    title = StringField(
        'Complaint Title',
        validators=[
            DataRequired(message="Complaint title is required"),
            Length(min=5, max=200, message="Title must be between 5 and 200 characters")
        ]
    )
    description = TextAreaField(
        'Detailed Description',
        validators=[
            DataRequired(message="Please provide a detailed description of the incident"),
            Length(min=20, message="Please describe the incident in at least 20 characters for proper investigation")
        ]
    )
    crime_category = SelectField(
        'Crime Category',
        choices=[(cat, cat) for cat in Config.CRIME_CATEGORIES],
        validators=[DataRequired(message="Please select a crime category")]
    )
    incident_date = DateTimeLocalField(
        'Date & Time of Incident',
        format='%Y-%m-%dT%H:%M',
        validators=[DataRequired(message="Please select the date and approximate time of the incident")]
    )

    # Step 2: Location Info
    district = SelectField(
        'District',
        choices=[(d, d) for d in Config.DISTRICTS],
        validators=[DataRequired(message="Please select the district")]
    )
    incident_location = StringField(
        'Specific Incident Location / Landmark',
        validators=[
            DataRequired(message="Please provide the location address or landmark"),
            Length(min=3, max=200)
        ]
    )
    police_station = SelectField(
        'Jurisdiction / Police Station',
        choices=[(ps, ps) for ps in Config.POLICE_STATIONS],
        validators=[DataRequired(message="Please select the relevant police station")]
    )

    # Step 3: Evidence (Handled by multi-part file input in template)
    evidence_files = MultipleFileField(
        'Supporting Evidence Documents / Photos (Optional)',
        validators=[
            Optional(),
            FileAllowed(Config.ALLOWED_EXTENSIONS, f"Allowed formats: {', '.join(Config.ALLOWED_EXTENSIONS)} (Max 16MB each)")
        ]
    )

    # Step 4: Confirmation
    declaration = BooleanField(
        'I confirm that the information provided in this complaint is accurate to the best of my knowledge.',
        validators=[DataRequired(message="You must declare the accuracy of the complaint.")]
    )
    save_as_draft = HiddenField('save_as_draft', default='false')
    submit = SubmitField('Submit Official Complaint')


class ReportUpdateForm(FlaskForm):
    """Used by Admin and Officers to update status and add notes."""
    status = SelectField(
        'Update Status',
        choices=[(st, st) for st in Config.STATUS_CHOICES],
        validators=[DataRequired()]
    )
    remarks = TextAreaField('Investigation Remarks / Public Update', validators=[Optional()])
    is_internal = BooleanField('Internal Case Note (Hidden from citizen)', default=False)
    assigned_officer_id = SelectField('Assign Investigating Officer', coerce=int, choices=[(0, 'Unassigned')], default=0, validate_choice=False, validators=[Optional()])
    submit = SubmitField('Save Case Update')


class OfficerAssignmentForm(FlaskForm):
    """Admin form to assign an officer to a complaint."""
    officer_id = SelectField('Select Officer', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Assignment Instructions', validators=[Optional()])
    submit = SubmitField('Assign Officer')


class UserRoleForm(FlaskForm):
    """Admin form to manage user role and officer badge."""
    role = SelectField(
        'User Role',
        choices=[('citizen', 'Citizen'), ('officer', 'Police Officer'), ('admin', 'Administrator')],
        validators=[DataRequired()]
    )
    badge_number = StringField('Badge / ID Number', validators=[Optional(), Length(max=50)])
    department = StringField('Department / Wing', validators=[Optional(), Length(max=100)])
    police_station = SelectField('Assigned Police Station', choices=[('', 'None')] + [(ps, ps) for ps in Config.POLICE_STATIONS], validators=[Optional()])
    is_active = BooleanField('Account Active', default=True)
    submit = SubmitField('Update User Permissions')


class OfficerProfileForm(FlaskForm):
    """Admin form to create or edit an officer directory profile."""
    name = StringField('Officer Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    badge_number = StringField('Badge Number (e.g. DEMO-SI-071)', validators=[DataRequired(), Length(min=2, max=50)])
    designation = SelectField(
        'Designation / Rank',
        choices=[
            ('Inspector', 'Inspector'),
            ('Sub Inspector', 'Sub Inspector'),
            ('Assistant Sub Inspector', 'Assistant Sub Inspector'),
            ('Head Constable', 'Head Constable'),
            ('Constable', 'Constable')
        ],
        validators=[DataRequired()]
    )
    department = StringField('Department / Wing', default='Law and Order', validators=[DataRequired(), Length(min=2, max=100)])
    police_station = SelectField('Police Station Jurisdiction', choices=[(ps, ps) for ps in Config.POLICE_STATIONS], validators=[DataRequired()])
    is_available = BooleanField('Available for Case Assignments', default=True)
    submit = SubmitField('Save Officer Profile')


class OfficerProvisionAccountForm(FlaskForm):
    """Admin form to provision login credentials for an unlinked officer profile."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=40),
        Regexp(r'^[a-zA-Z0-9_.]+$', message="Username can only contain letters, numbers, dots, and underscores.")
    ])
    email = StringField('Official Email', validators=[
        DataRequired(),
        Regexp(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message="Please enter a valid email address.")
    ])
    password = PasswordField('Initial Password', validators=[
        DataRequired(),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    submit = SubmitField('Create Officer Login Account')

