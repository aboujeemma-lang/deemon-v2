from flask import Flask, render_template, redirect, url_for, request, session, flash, make_response
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, SimpleDocTemplate, PageBreak
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import generate_password_hash
from datetime import datetime, date
from xhtml2pdf import pisa
from flask import make_response
from weasyprint import HTML
from io import BytesIO
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from flask import render_template
from datetime import datetime
from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_login import LoginManager
from extensions import db, migrate
import sqlite3
import os



# --------------------
# APP CONFIG
# --------------------

app = Flask(__name__)

# ================= CONFIG =================
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Fix for Render (postgres:// → postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    # Local development ONLY
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ================= INIT EXTENSIONS =================
db.init_app(app)
migrate.init_app(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --------------------
# DATABASE MODELS
# --------------------
class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=db.func.now())

    users = db.relationship('User', backref='school', lazy=True)
    lessons = db.relationship('Lesson', backref='school', lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'  # explicit table name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    contact = db.Column(db.String(30))  # 👈 NEW
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # super_admin, headmaster, teacher
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    lessons = db.relationship('Lesson', backref='teacher', lazy=True)


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100))
    class_name = db.Column(db.String(50))
    week_ending = db.Column(db.String(50))
    class_size = db.Column(db.Integer)
    day = db.Column(db.String(20))
    period = db.Column(db.String(20))
    lesson_title = db.Column(db.String(200))
    strand = db.Column(db.String(200))
    sub_strand = db.Column(db.String(200))
    indicator_code = db.Column(db.String(100))
    content_standard_code = db.Column(db.String(100))
    lesson_date = db.Column(db.Date, nullable=False, default=date.today)
    performance_indicator = db.Column(db.Text)
    core_competencies = db.Column(db.Text)
    keywords = db.Column(db.Text)
    tlr = db.Column(db.Text)
    reference = db.Column(db.Text)
    phase1 = db.Column(db.Text)
    phase2 = db.Column(db.Text)
    phase3 = db.Column(db.Text)
    materials = db.Column(db.Text)      # ✅ ADD THIS
    assessment = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    feedback = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # use 'users.id'
    approval_date = db.Column(db.DateTime)        # ✅ new
    approved_by = db.Column(db.String(120))
    approval_date = db.Column(db.Date, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected
    feedback = db.Column(db.Text, nullable=True)          # Headmaster remark
    approved_by = db.Column(db.String(100), nullable=True)  # Headmaster name/email
    approval_date = db.Column(db.DateTime, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class YearlyScheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    class_name = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    week = db.Column(db.String(20), nullable=False)

    term1 = db.Column(db.Text)
    term2 = db.Column(db.Text)
    term3 = db.Column(db.Text)

    vetted_by = db.Column(db.String(100), default="Pending")
    vetted_date = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending | approved | rejected
    feedback = db.Column(db.Text)
    teacher = db.relationship('User', backref='yearly_schemes')

    __table_args__ = (
        db.UniqueConstraint(
            'teacher_id', 'class_name', 'subject', 'academic_year',
            name='unique_yearly_scheme'
        ),
    )

class TermlyScheme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    week = db.Column(db.String(20), nullable=False)
    strand = db.Column(db.Text)
    sub_strand = db.Column(db.Text)
    content_standard = db.Column(db.Text)
    indicator = db.Column(db.Text)
    resources = db.Column(db.Text)

    vetted_by = db.Column(db.String(100), default="Pending")
    vetted_date = db.Column(db.DateTime)
    teacher = db.relationship('User', backref='termly_schemes')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending | approved | rejected
    feedback = db.Column(db.Text)
     


# --------------------
# LOGIN MANAGER
# --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()

def create_super_admin():
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            name='Super Admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            role='super_admin'
        )
        db.session.add(admin)
        db.session.commit()
# --------------------
# ROUTES
# --------------------

# After creating app
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.route('/teacher/schemes', methods=['GET', 'POST'])
@login_required
def teacher_schemes():

    if current_user.role != 'teacher':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    yearly_schemes = YearlyScheme.query.filter_by(
        teacher_id=current_user.id
    ).order_by(YearlyScheme.week).all()

    termly_schemes = TermlyScheme.query.filter_by(
        teacher_id=current_user.id
    ).order_by(TermlyScheme.week).all()

    return render_template(
        'teacher_schemes.html',
        yearly_schemes=yearly_schemes,
        termly_schemes=termly_schemes
    )

@app.route('/headmaster/termly-scheme/<int:id>', methods=['GET'])
@login_required
def headmaster_view_termly_scheme(id):

    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    scheme = TermlyScheme.query.get_or_404(id)

    teacher = User.query.get(scheme.teacher_id)

    return render_template(
        'headmaster_view_termly_scheme.html',
        scheme=scheme,
        teacher=teacher
    )

@app.route('/teacher/yearly-scheme/<int:id>/view')
@login_required
def view_yearly_scheme(id):
    scheme = YearlyScheme.query.get_or_404(id)

    if scheme.teacher_id != current_user.id:
        abort(403)

    return render_template(
        'view_yearly_scheme.html',
        scheme=scheme,
        readonly=True
    )

@app.route('/teacher/termly-scheme/<int:id>/view')
@login_required
def view_termly_scheme(id):
    scheme = TermlyScheme.query.get_or_404(id)

    if scheme.teacher_id != current_user.id:
        abort(403)

    return render_template(
        'view_termly_scheme.html',
        scheme=scheme,
        readonly=True
        
    )

@app.route('/headmaster/termly-scheme/<int:id>/vet', methods=['POST'])
@login_required
def vet_termly_scheme(id):

    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    scheme = TermlyScheme.query.get_or_404(id)

    action = request.form.get('action')
    feedback = request.form.get('feedback')

    if action == 'approve':
        scheme.status = 'approved'
        scheme.vetted_by = current_user.name
        scheme.vetted_date = datetime.utcnow()

    elif action == 'reject':
        scheme.status = 'rejected'
        scheme.vetted_by = current_user.name
        scheme.vetted_date = datetime.utcnow()
        scheme.feedback = feedback

    db.session.commit()

    flash('Termly scheme reviewed successfully.', 'success')
    return redirect(url_for('headmaster_schemes'))

@app.route('/teacher/yearly-scheme/create', methods=['POST'])
@login_required
def create_yearly_scheme():

    existing = YearlyScheme.query.filter_by(
        teacher_id=current_user.id,
        class_name=request.form['class_name'],
        subject=request.form['subject'],
        academic_year=request.form['academic_year']
    ).first()

    if existing:
        flash('Yearly scheme already exists for this class, subject and year.', 'warning')
        return redirect(url_for('teacher_schemes'))

    scheme = YearlyScheme(
        teacher_id=current_user.id,
        class_name=request.form['class_name'],
        subject=request.form['subject'],
        academic_year=request.form['academic_year'],
        week=request.form['week'],
        term1=request.form['term1'],
        term2=request.form['term2'],
        term3=request.form['term3']
    )

    db.session.add(scheme)
    db.session.commit()

    flash('Yearly scheme saved successfully.', 'success')
    return redirect(url_for('teacher_schemes'))

@app.route('/teacher/termly-scheme/create', methods=['POST'])
@login_required
def create_termly_scheme():

    if current_user.role != 'teacher':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    scheme = TermlyScheme(
        teacher_id=current_user.id,
        week=request.form['week'],
        strand=request.form.get('strand'),
        sub_strand=request.form.get('sub_strand'),
        content_standard=request.form.get('content_standard'),
        indicator=request.form.get('indicator'),
        resources=request.form.get('resources')
    )

    db.session.add(scheme)
    db.session.commit()

    flash('Termly scheme saved successfully.', 'success')
    return redirect(url_for('teacher_schemes'))

@app.route('/teacher/termly-scheme/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_termly_scheme(id):
    scheme = TermlyScheme.query.get_or_404(id)

    if scheme.teacher_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('teacher_schemes'))

    if scheme.status != 'pending':
        flash('Approved schemes cannot be edited.', 'warning')
        return redirect(url_for('teacher_schemes'))

    if request.method == 'POST':
        scheme.week = request.form['week']
        scheme.strand = request.form.get('strand')
        scheme.sub_strand = request.form.get('sub_strand')
        scheme.content_standard = request.form.get('content_standard')
        scheme.indicator = request.form.get('indicator')
        scheme.resources = request.form.get('resources')

        db.session.commit()
        flash('Termly scheme updated.', 'success')
        return redirect(url_for('teacher_schemes'))

    return render_template('edit_termly_scheme.html', scheme=scheme)

@app.route('/teacher/termly-scheme/delete/<int:id>')
@login_required
def delete_termly_scheme(id):
    scheme = TermlyScheme.query.get_or_404(id)

    if scheme.teacher_id != current_user.id:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('teacher_schemes'))

    if scheme.status != 'pending':
        flash('Approved schemes cannot be deleted.', 'warning')
        return redirect(url_for('teacher_schemes'))

    db.session.delete(scheme)
    db.session.commit()

    flash('Termly scheme deleted.', 'success')
    return redirect(url_for('teacher_schemes'))

@app.route('/headmaster/termly-scheme/approve/<int:id>')
@login_required
def approve_termly_scheme(id):
    scheme = TermlyScheme.query.get_or_404(id)

    scheme.status = 'approved'
    scheme.vetted_by = current_user.name
    scheme.vetted_date = datetime.utcnow()

    db.session.commit()
    flash('Termly scheme approved.', 'success')
    return redirect(url_for('headmaster_schemes'))

@app.route('/headmaster/termly-scheme/reject/<int:id>', methods=['POST'])
@login_required
def reject_termly_scheme(id):
    scheme = TermlyScheme.query.get_or_404(id)

    scheme.status = 'rejected'
    scheme.vetted_by = current_user.name
    scheme.vetted_date = datetime.utcnow()
    scheme.feedback = request.form.get('feedback')

    db.session.commit()
    flash('Termly scheme rejected.', 'danger')
    return redirect(url_for('headmaster_schemes'))


@app.route('/headmaster/schemes')
@login_required
def headmaster_schemes():

    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    yearly_schemes = YearlyScheme.query.order_by(
        YearlyScheme.created_at.desc()
    ).all()

    termly_schemes = TermlyScheme.query.order_by(
        TermlyScheme.created_at.desc()
    ).all()

    return render_template(
        'headmaster_schemes.html',
        yearly_schemes=yearly_schemes,
        termly_schemes=termly_schemes
    )


@app.route('/headmaster/yearly-scheme/<int:id>/vet', methods=['POST'])
@login_required
def vet_yearly_scheme(id):
    scheme = YearlyScheme.query.get_or_404(id)

    action = request.form.get('action')
    feedback = request.form.get('feedback')

    if action == 'approve':
        scheme.status = 'approved'
    elif action == 'reject':
        scheme.status = 'rejected'

    scheme.feedback = feedback
    scheme.vetted_by = session.get('name')
    scheme.vetted_date = datetime.utcnow()

    db.session.commit()

    flash('Scheme vetting completed.', 'success')
    return redirect(url_for('headmaster_schemes'))

@app.route('/headmaster/scheme/<int:id>/approve')
@login_required
def approve_scheme(id):

    scheme = YearlyScheme.query.get_or_404(id)

    scheme.status = 'approved'
    scheme.vetted_by = current_user.name
    scheme.vetted_date = datetime.utcnow()

    db.session.commit()
    flash('Scheme approved successfully.', 'success')
    return redirect(url_for('headmaster_schemes'))

@app.route('/headmaster/scheme/<int:id>/reject', methods=['POST'])
@login_required
def reject_scheme(id):

    scheme = YearlyScheme.query.get_or_404(id)

    scheme.status = 'rejected'
    scheme.feedback = request.form['feedback']
    scheme.vetted_by = current_user.name
    scheme.vetted_date = datetime.utcnow()

    db.session.commit()
    flash('Scheme rejected.', 'warning')
    return redirect(url_for('headmaster_schemes'))


@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        elif current_user.role == 'headmaster':
            return redirect(url_for('headmaster_dashboard'))
        elif current_user.role == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
    return render_template('home.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name

        flash('Login successful', 'success')

        if user.role == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        elif user.role == 'headmaster':
            return redirect(url_for('headmaster_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))

    # ❌ Failed login → return home and reopen modal
    flash('Invalid email or password', 'danger')
    return redirect(url_for('home', showLogin=1))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

# --------------------
# SUPER ADMIN DASHBOARD
# --------------------
@app.route('/super-admin', methods=['GET', 'POST'])
@login_required
def super_admin_dashboard():
    if current_user.role != 'super_admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    schools = School.query.all()
    headmasters = User.query.filter_by(role='headmaster', school_id=None).all()  # unassigned headmasters

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        headmaster_id = request.form.get('headmaster_id')

        if not all([name, email, phone]):
            flash('All fields are required.', 'warning')
            return redirect(url_for('super_admin_dashboard'))

        new_school = School(name=name, email=email, phone=phone)
        db.session.add(new_school)
        db.session.commit()

        if headmaster_id:
            headmaster = User.query.get(int(headmaster_id))
            headmaster.school_id = new_school.id
            db.session.commit()

        flash(f"School '{name}' created successfully!", 'success')
        return redirect(url_for('super_admin_dashboard'))

    return render_template('super_admin_dashboard.html', schools=schools, headmasters=headmasters)

@app.route('/super-admin/create-headmaster', methods=['POST'])
@login_required
def create_headmaster():
    if current_user.role != 'super_admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    school_id = request.form.get('school_id')

    if not all([name, email, password, school_id]):
        flash('All fields are required.', 'warning')
        return redirect(url_for('super_admin_dashboard'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('super_admin_dashboard'))

    # ✅ FIX: hash password properly
    hashed_password = generate_password_hash(password)

    headmaster = User(
        name=name,
        email=email,
        password=hashed_password,   # ✅ now defined
        role='headmaster',
        school_id=int(school_id)
    )

    db.session.add(headmaster)
    db.session.commit()

    flash('Headmaster created and assigned successfully!', 'success')
    return redirect(url_for('super_admin_dashboard'))

@app.route('/teacher/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def teacher_edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    # Lock editing if already reviewed
    if lesson.status != 'pending':
        flash("You cannot edit a lesson that is already reviewed.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        # Update all fields from the form
        lesson.subject = request.form.get('subject')
        lesson.lesson_title = request.form.get('lesson_title')
        lesson.strand = request.form.get('strand')
        lesson.sub_strand = request.form.get('sub_strand')
        lesson.day = request.form.get('day')
        lesson.period = request.form.get('period')
        lesson.class_name = request.form.get('class_name')
        lesson.class_size = request.form.get('class_size')
        lesson.week_ending = request.form.get('week_ending')
        lesson.performance_indicator = request.form.get('performance_indicator')
        lesson.content_standard_code = request.form.get('content_standard_code')
        lesson.indicator_code = request.form.get('indicator_code')
        lesson.core_competencies = request.form.get('core_competencies')
        lesson.keywords = request.form.get('keywords')
        lesson.tlr = request.form.get('tlr')
        lesson.reference = request.form.get('reference')
        lesson.phase1 = request.form.get('phase1')
        lesson.phase2 = request.form.get('phase2')
        lesson.phase3 = request.form.get('phase3')
        lesson.materials = request.form.get('materials')
        lesson.assessment = request.form.get('assessment')

        db.session.commit()
        flash("Lesson updated successfully.", "success")
        return redirect(url_for('teacher_dashboard'))

    return render_template('teacher_edit_lesson.html', lesson=lesson)



@app.route('/teacher/lesson/<int:lesson_id>/pdf')
@login_required
def teacher_export_pdf(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30,leftMargin=30, topMargin=30,bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph(f"Lesson Plan - {lesson.lesson_title}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Helper to safely handle dates and empty fields
    def add_table_row(label, value):
        if isinstance(value, (datetime, date)):
            value = value.strftime("%Y-%m-%d")
        return [Paragraph(f"<b>{label}</b>", styles['Normal']),
                Paragraph(str(value or "—"), styles['Normal'])]

    # Build table data
    data = [
        add_table_row("Lesson Date", lesson.lesson_date),
        add_table_row("Week Ending", lesson.week_ending),
        add_table_row("Class", lesson.class_name),
        add_table_row("Subject", lesson.subject),
        add_table_row("Lesson Title", lesson.lesson_title),
        add_table_row("Strand", lesson.strand),
        add_table_row("Sub-Strand", lesson.sub_strand),
        add_table_row("Indicator Code", lesson.indicator_code),
        add_table_row("Content Standard Code", lesson.content_standard_code),
        add_table_row("Day", lesson.day),
        add_table_row("Period", lesson.period),
        add_table_row("Class Size", lesson.class_size),
        add_table_row("Performance Indicator", lesson.performance_indicator),
        add_table_row("Core Competencies", lesson.core_competencies),
        add_table_row("Keywords", lesson.keywords),
        add_table_row("Teaching & Learning Resources (TLR)", lesson.tlr),
        add_table_row("Reference", lesson.reference),
        add_table_row("Phase 1 (Starter)", lesson.phase1),
        add_table_row("Phase 2 (Main)", lesson.phase2),
        add_table_row("Phase 3 (Reflections)", lesson.phase3),
        add_table_row("Status", lesson.status),
        add_table_row("Headmaster Feedback", lesson.feedback),
        add_table_row("Approved By", lesson.approved_by),
        add_table_row("Approval Date", lesson.approval_date),
    ]

    table = Table(data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"lesson_{lesson.id}.pdf", mimetype='application/pdf')

@app.route('/teacher/view_lesson/<int:lesson_id>')
@login_required
def teacher_view_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    return render_template('teacher_view_lesson.html', lesson=lesson)

# --------------------
# HEADMASTER DASHBOARD
# --------------------
@app.route('/headmaster', methods=['GET', 'POST'])
@login_required
def headmaster_dashboard():
    # 🔐 Role protection
    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    # ➕ CREATE TEACHER
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        contact = request.form.get('contact')
        password = request.form.get('password')

        # Validation
        if not all([name, email, contact, password]):
            flash('All fields are required.', 'warning')
            return redirect(url_for('headmaster_dashboard'))

        # Prevent duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with this email already exists.', 'danger')
            return redirect(url_for('headmaster_dashboard'))

        # Create teacher
        new_teacher = User(
            name=name,
            email=email,
            contact=contact,  # ✅ stored
            password=generate_password_hash(password),  # ✅ hashed
            role='teacher',
            school_id=current_user.school_id  # ✅ VERY IMPORTANT
        )

        db.session.add(new_teacher)  # ❗ fixed variable name
        db.session.commit()

        flash('Teacher created successfully!', 'success')
        return redirect(url_for('headmaster_dashboard'))

    # 📊 DASHBOARD DATA (school-scoped)
    teachers = User.query.filter_by(
        role='teacher',
        school_id=current_user.school_id
    ).all()

    lessons = Lesson.query.filter_by(
        school_id=current_user.school_id
    ).order_by(Lesson.date_created.desc()).all()

    return render_template(
        'headmaster_dashboard.html',
        teachers=teachers,
        lessons=lessons
    )


@app.route('/headmaster/lesson/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def headmaster_view_lesson(lesson_id):
    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    lesson = Lesson.query.get_or_404(lesson_id)

    if request.method == 'POST':
        action = request.form.get('action')
        lesson.feedback = request.form.get('remark')  # Headmaster feedback

        # Update status based on action
        if action == 'approve':
            lesson.status = 'approved'
        elif action == 'reject':
            lesson.status = 'rejected'

        # Audit trail
        lesson.approved_by = current_user.name  # store who approved/rejected
        lesson.approval_date = datetime.utcnow()  # store timestamp

        db.session.commit()
        flash(f'Lesson {lesson.status} successfully!', 'success')
        return redirect(url_for('headmaster_dashboard'))

    return render_template('headmaster_view_lesson.html', lesson=lesson)

# --------------------
# TEACHER DASHBOARD
# --------------------
@app.route('/teacher', methods=['GET', 'POST'])
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':

        # 🔍 TEMPORARY DEBUG (KEEP FOR NOW)
        print("FORM DATA:", request.form)

        lesson = Lesson(
            subject=request.form.get('subject'),
            lesson_date=date.today(),
            class_name=request.form.get('class_name'),
            week_ending=request.form.get('week_ending'),
            class_size=request.form.get('class_size'),
            day=request.form.get('day'),
            period=request.form.get('period'),

            lesson_title=request.form.get('lesson_title'),
            strand=request.form.get('strand'),
            sub_strand=request.form.get('sub_strand'),
            indicator_code=request.form.get('indicator_code'),
            content_standard_code=request.form.get('content_standard_code'),
            performance_indicator=request.form.get('performance_indicator'),
            core_competencies=request.form.get('core_competencies'),
            keywords=request.form.get('keywords'),

            # ✅ MODEL-CONFIRMED FIELDS
            tlr=request.form.get('tlr'),
            reference=request.form.get('reference'),
            assessment=request.form.get('assessment'),

            # ✅ PHASES (MATCH MODEL)
            phase1=request.form.get('phase1'),
            phase2=request.form.get('phase2'),
            phase3=request.form.get('phase3'),

            status='pending',
            teacher_id=current_user.id,
            school_id=current_user.school_id
        )

        db.session.add(lesson)
        db.session.commit()

        flash('Lesson submitted successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))

    lessons = Lesson.query.filter_by(
        teacher_id=current_user.id
    ).order_by(Lesson.date_created.desc()).all()

    return render_template('teacher_dashboard.html', lessons=lessons)
# Step 1: Forgot Password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email found! You can now reset your password.', 'success')
            return redirect(url_for('reset_password', user_id=user.id))
        else:
            flash('Email not found!', 'danger')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

# Step 2: Reset Password
@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')          # Must match form field name
        confirm_password = request.form.get('confirm_password', '')  # Must match form field name

        if not new_password or not confirm_password:
            flash('Please fill in all password fields.', 'warning')
            return redirect(url_for('reset_password', user_id=user_id))

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', user_id=user_id))

        # Update password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Password updated successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', user=user)

@app.route('/teacher/change_password', methods=['GET', 'POST'])
@login_required
def teacher_change_password():
    if current_user.role != 'teacher':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_pw or not new_pw or not confirm_pw:
            flash('All fields are required.', 'warning')
            return redirect(url_for('teacher_change_password'))

        if not check_password_hash(current_user.password, current_pw):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('teacher_change_password'))

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('teacher_change_password'))

        current_user.password = generate_password_hash(new_pw)
        db.session.commit()
        flash('Password updated successfully!', 'success')
        return redirect(url_for('teacher_dashboard'))

    return render_template('teacher_change_password.html')


@app.route('/headmaster/export-lessons-pdf')
@login_required
def export_lessons_pdf():
    if current_user.role != 'headmaster':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    lessons = Lesson.query.order_by(Lesson.date_created.desc()).all()  # fetch all lessons

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    elements.append(Paragraph("All Submitted Lessons", title_style))
    elements.append(Spacer(1, 12))

    for lesson in lessons:
        # Header table
        header_data = [
            ['Subject:', lesson.subject, 'Class:', lesson.class_name],
            ['Lesson Title:', lesson.lesson_title, 'Week Ending:', str(lesson.week_ending)],
            ['Teacher ID:', str(lesson.teacher_id), 'Status:', lesson.status.capitalize()],
            ['Approved By:', lesson.approved_by or '—', 'Approval Date:', str(lesson.approval_date or '—')],
            ['Feedback:', lesson.feedback or '—', '', '']
        ]
        header_table = Table(header_data, colWidths=[80, 160, 80, 160], repeatRows=0, splitByRow=1)
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))

        # Phases and other long text fields as Paragraphs
        phase_data = [
            ['Phase 1 (Starter)', Paragraph(lesson.phase1 or '—', normal_style)],
            ['Phase 2 (Main)', Paragraph(lesson.phase2 or '—', normal_style)],
            ['Phase 3 (Reflections)', Paragraph(lesson.phase3 or '—', normal_style)],
            ['Performance Indicator', Paragraph(lesson.performance_indicator or '—', normal_style)],
            ['Core Competencies', Paragraph(lesson.core_competencies or '—', normal_style)],
            ['Keywords', Paragraph(lesson.keywords or '—', normal_style)],
            ['Teaching & Learning Resources', Paragraph(lesson.tlr or '—', normal_style)],
            ['Reference', Paragraph(lesson.reference or '—', normal_style)]
        ]
        phase_table = Table(phase_data, colWidths=[150, 330], repeatRows=0, splitByRow=1)
        phase_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1, colors.black),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(phase_table)
        elements.append(PageBreak())  # start each lesson on a new page

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="all_lessons.pdf",
        mimetype='application/pdf'
    )


@app.route('/lesson/<int:lesson_id>/pdf')
@login_required
def export_lesson_pdf(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    html = render_template('lesson_pdf.html', lesson=lesson)
    return HTML(string=html).write_pdf()

    # Fetch lessons for this headmaster's school
    lessons = Lesson.query.filter_by(school_id=current_user.school_id).order_by(Lesson.date_created.desc()).all()

    # Render HTML template for PDF
    rendered = render_template('headmaster_lessons_pdf.html', lessons=lessons, headmaster=current_user)

    # Convert HTML to PDF
    pdf_file = BytesIO()
    HTML(string=rendered).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Return PDF as download
    response = make_response(pdf_file.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=submitted_lessons.pdf'

    return response


@app.route('/teacher/resources')
@login_required
def teacher_resources():
    if current_user.role != 'teacher':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))

    schemes = [
        {"title": "Primary 1 Scheme of Work", "file": "primary1_scheme.pdf"},
        {"title": "Primary 2 Scheme of Work", "file": "primary2_scheme.pdf"},
        {"title": "Primary 3 Scheme of Work", "file": "primary3_scheme.pdf"},
    ]

    return render_template('teacher_resources.html', schemes=schemes)

# --------------------
# DATABASE INIT (LOCAL DEV ONLY)
# --------------------
if os.environ.get("FLASK_ENV") == "development":
    with app.app_context():
        db.create_all()

        # Default school
        default_school = School.query.filter_by(name="Default School").first()
        if not default_school:
            default_school = School(
                name="Default School",
                email="default@school.com",
                phone="0000000000"
            )
            db.session.add(default_school)
            db.session.commit()

        # Default super admin
        if not User.query.filter_by(email='admin@example.com').first():
            admin = User(
                name='Super Admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                role='super_admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Superadmin created")

# --------------------
# RUN APP
# --------------------
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)