from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User
from app.forms import RegistrationForm, LoginForm
from flask import Blueprint

bp = Blueprint('auth', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard' if not current_user.is_admin else 'admin.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user exists
        user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if user:
            flash('Username or email already exists!', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if aadhar exists
        existing_aadhar = User.query.filter_by(aadhar_number=form.aadhar_number.data).first()
        if existing_aadhar:
            flash('Aadhar number already registered!', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            aadhar_number=form.aadhar_number.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Register', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            
            if user.is_admin:
                flash(f'Welcome Admin {user.username}!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
            else:
                flash(f'Welcome {user.full_name}!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('user.dashboard'))
        else:
            flash('Invalid username/email or password!', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.index'))