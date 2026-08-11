from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, DateTimeField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from datetime import datetime
from config import Config

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired(), Length(min=12, max=12)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ReportForm(FlaskForm):
    title = StringField('Complaint Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Detailed Description', validators=[DataRequired()])
    crime_category = SelectField('Crime Category', choices=[(cat, cat) for cat in Config.CRIME_CATEGORIES], validators=[DataRequired()])
    incident_date = DateTimeField('Date & Time of Incident', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    incident_location = StringField('Incident Location', validators=[DataRequired(), Length(max=200)])
    police_station = SelectField('Police Station', choices=[(ps, ps) for ps in Config.POLICE_STATIONS], validators=[DataRequired()])
    evidence_file = FileField('Upload Evidence (Optional)', validators=[FileAllowed(Config.ALLOWED_EXTENSIONS, 'Images and PDF only!')])
    submit = SubmitField('Submit Complaint')

class ReportUpdateForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'),
        ('Under Investigation', 'Under Investigation'),
        ('Evidence Collected', 'Evidence Collected'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected')
    ], validators=[DataRequired()])
    remarks = TextAreaField('Admin Remarks', validators=[Optional()])
    assigned_officer = StringField('Assigned Officer', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Update Report')