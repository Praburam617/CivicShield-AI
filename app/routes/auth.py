from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import login_user, logout_user, current_user, login_required
from app import db, limiter
from app.models import User
from app.forms import RegistrationForm, LoginForm
from app.services.audit import log_audit

bp = Blueprint('auth', __name__)


@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin_user:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_officer:
            return redirect(url_for('officer.dashboard'))
    return render_template('index.html', title='Home')


@bp.route('/help')
def help_faq():
    return render_template('help.html', title='Help & Frequently Asked Questions')


@bp.route('/privacy')
def privacy():
    return render_template('privacy.html', title='Privacy & Platform Advisory')


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        if current_user.is_admin_user:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_officer:
            return redirect(url_for('officer.dashboard'))
        return redirect(url_for('user.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            full_name=form.full_name.data.strip(),
            phone=form.phone.data.strip(),
            role='citizen',
            is_admin=False,
            is_active=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        log_audit(
            action='USER_REGISTERED',
            user_id=user.id,
            resource_type='user',
            resource_id=user.id,
            details=f"Citizen registered: {user.username} ({user.email})"
        )

        flash('Your account has been created successfully! Please sign in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', title='Register for Citizen Portal', form=form)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("15 per minute")
def login():
    if current_user.is_authenticated:
        if current_user.is_admin_user:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_officer:
            return redirect(url_for('officer.dashboard'))
        return redirect(url_for('user.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.username.data.strip()
        user = User.query.filter(
            (User.username.ilike(login_input)) | (User.email.ilike(login_input))
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                log_audit(action='LOGIN_BLOCKED_INACTIVE', user_id=user.id, details=f"Attempt to login to deactivated account: {login_input}")
                flash('Your account is inactive. Please contact the system administrator.', 'danger')
                return render_template('login.html', title='Sign In', form=form)

            login_user(user, remember=form.remember_me.data)
            log_audit(action='LOGIN_SUCCESS', user_id=user.id, details=f"User {user.username} logged in successfully")

            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name}!', 'success')

            if user.is_admin_user:
                return redirect(next_page or url_for('admin.dashboard'))
            elif user.is_officer:
                return redirect(next_page or url_for('officer.dashboard'))
            else:
                return redirect(next_page or url_for('user.dashboard'))
        else:
            log_audit(action='LOGIN_FAILED', details=f"Failed login attempt for identifier: {login_input}")
            flash('Invalid username/email or password. Please verify and try again.', 'danger')

    return render_template('login.html', title='Sign In - CivicShield AI', form=form)


@bp.route('/logout')
@login_required
def logout():
    uid = current_user.id
    uname = current_user.username
    logout_user()
    log_audit(action='LOGOUT', user_id=uid, details=f"User {uname} logged out")
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('auth.index'))
