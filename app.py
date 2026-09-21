
import requests
import pdfkit, os, re
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, session, make_response, url_for, redirect, flash, jsonify
from flask_wtf.csrf import CSRFProtect, CSRFError
import sqlite3
from database import init_db
import database
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# from alter import init_db
app = Flask(__name__)  
database.init_db()
app.secret_key = "your_secret_key_here" 
API_KEY = "sk_d30294205f6d06cce706e3e8ada1c859b4798c9b"

csrf = CSRFProtect(app)

def is_ajax_request():
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.is_json or
        'application/json' in request.headers.get('Accept', '') or
        request.args.get('ajax') == '1'
    )

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if is_ajax_request():
        return jsonify({'success': False, 'error': 'Security token expired or invalid (CSRF error). Please refresh and try again.'}), 400
    flash("Security token expired or invalid (CSRF error). Please try submitting the form again.", "danger")
    return redirect(request.referrer or url_for('login'))

# ==================== VALIDATION HELPERS ====================
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
PHONE_REGEX = re.compile(r'^[+]?[0-9\s\-()]{7,20}$')
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_. -]{3,30}$')

def is_valid_email(email):
    return bool(email and EMAIL_REGEX.match(str(email).strip()))

def is_valid_phone(phone):
    return bool(phone and PHONE_REGEX.match(str(phone).strip()))

def is_valid_username(username):
    return bool(username and USERNAME_REGEX.match(str(username).strip()))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None and not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_current_user():
    user_id = session.get('user_id')
    is_admin = session.get('is_admin', False)
    if not user_id and not is_admin:
        return {'current_user': None}
    if is_admin or user_id == 'admin':
        return {
            'current_user': {
                'id': 'admin',
                'name': 'Administrator',
                'username': 'admin',
                'email': 'admin@system.local',
                'initials': 'AD',
                'is_admin': True
            }
        }
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = c.fetchone()
        c.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        contact_row = c.fetchone()
        conn.close()
        if user_row:
            name = (contact_row['fullname'] if contact_row and contact_row['fullname'] else user_row['name']) or user_row['username']
            parts = name.strip().split()
            if len(parts) >= 2:
                initials = (parts[0][0] + parts[1][0]).upper()
            elif parts:
                initials = parts[0][:2].upper()
            else:
                initials = 'U'
            return {
                'current_user': {
                    'id': user_row['user_id'],
                    'name': name,
                    'username': user_row['username'],
                    'email': user_row['email'],
                    'initials': initials,
                    'is_admin': False
                }
            }
    except Exception:
        pass
    return {'current_user': None}

# if __name__ == "__main__":
#     init_db()


# home
@app.route('/')
def home():
    return render_template('index.html')

# return login page
@app.route('/loginf')
def loginf():
    return render_template('login.html')

# return signup page
@app.route('/signupf')
def signf():
    return render_template('signup.html')

# login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return render_template('login.html')

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Check admin table with secure hash
        c.execute("SELECT * FROM admin WHERE username=?", (username,))
        admin_row = c.fetchone()
        if admin_row and (check_password_hash(admin_row['password'], password) or admin_row['password'] == password):
            if admin_row['password'] == password and not admin_row['password'].startswith(('scrypt:', 'pbkdf2:')):
                c.execute("UPDATE admin SET password=? WHERE admin_id=?", (generate_password_hash(password), admin_row['admin_id']))
                conn.commit()
            conn.close()
            session['is_admin'] = True
            session['user_id'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        # Check regular registered users
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and (check_password_hash(user['password'], password) or user['password'] == password):
            # Auto-upgrade plaintext password to hash if matched
            if user['password'] == password and not user['password'].startswith(('scrypt:', 'pbkdf2:')):
                conn = sqlite3.connect('database.db')
                c = conn.cursor()
                c.execute("UPDATE users SET password=? WHERE user_id=?", (generate_password_hash(password), user['user_id']))
                conn.commit()
                conn.close()

            session['user_id'] = user['user_id']
            session.pop('is_admin', None)

            next_url = request.args.get('next') or request.form.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect(url_for('homepage'))
        else:
            flash("Invalid username or password. Please try again.", "danger")
            return render_template('login.html', next=request.args.get('next'))

    return render_template('login.html', next=request.args.get('next'))


# sign up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not name or not email or not username or not password:
            flash("All fields are required. Please fill in all details.", "warning")
            return render_template('signup.html')

        if len(name) < 2:
            flash("Please enter a valid full name (at least 2 characters).", "warning")
            return render_template('signup.html')

        if not is_valid_email(email):
            flash("Please provide a valid email address (e.g., user@example.com).", "warning")
            return render_template('signup.html')

        if not is_valid_username(username):
            flash("Username must be 3-30 characters containing only letters, numbers, and underscores.", "warning")
            return render_template('signup.html')

        if len(password) < 4:
            flash("Password must be at least 4 characters long.", "warning")
            return render_template('signup.html')

        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT user_id, email, username FROM users WHERE LOWER(email)=LOWER(?) OR LOWER(username)=LOWER(?)", (email, username))
        existing_user = c.fetchone()

        if existing_user:
            conn.close()
            if existing_user['email'].lower() == email.lower():
                flash("An account with this email already exists. Please log in.", "warning")
            else:
                flash("This username is already taken. Please choose another username.", "warning")
            return render_template('signup.html')

        hashed = generate_password_hash(password)
        try:
            c.execute("""
                INSERT INTO users (name, email, username, password)
                VALUES (?, ?, ?, ?)
            """, (name, email, username, hashed))
            conn.commit()
            conn.close()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))

        except sqlite3.IntegrityError:
            conn.close()
            flash("An account with these details already exists. Please log in.", "warning")
            return render_template('signup.html')

    return render_template('signup.html')

# log out
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('home'))



@app.route('/index')
def index():
    return render_template('index.html')

# ==================== RESUME TEMPLATES REGISTRY ====================
TEMPLATES = {
    'classic': {
        'id': 'classic',
        'name': 'Classic Executive',
        'badge': 'One-Column',
        'category': 'one-column',
        'description': 'Traditional single-column serif layout with clean divider rules. Perfect for corporate, legal, and academic resumes.',
        'css_file': 'classic.css',
        'image': 'temp (2).avif'
    },
    'modern': {
        'id': 'modern',
        'name': 'Modern Tech & Colorful',
        'badge': 'Colorful',
        'category': 'colorful',
        'description': 'Vivid indigo header accents, modern typography, and colored pill badges for skills. Ideal for tech, marketing, and startups.',
        'css_file': 'modern.css',
        'image': 'temp (4).avif'
    },
    'two_column': {
        'id': 'two_column',
        'name': 'Two-Column Professional',
        'badge': 'Two-Column',
        'category': 'two-column',
        'description': 'Distinct split layout with a structured sidebar for contact, skills, and certifications, paired with a wide career column.',
        'css_file': 'two_column.css',
        'image': 'temp (11).avif'
    },
    'ats_simple': {
        'id': 'ats_simple',
        'name': 'Simple ATS',
        'badge': 'ATS-Ready',
        'category': 'ats',
        'description': 'High-contrast, distraction-free minimalist layout formatted specifically for Application Tracking Systems (ATS).',
        'css_file': 'ats_simple.css',
        'image': 'temp (9).avif'
    }
}

# template gallery
@app.route('/tempage')
def tempage():
    user_id = session.get('user_id')
    user = None
    if user_id and user_id != 'admin':
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()

    selected_template = session.get('selected_template') or (user['template'] if user and 'template' in user.keys() and user['template'] else 'classic')
    if selected_template not in TEMPLATES:
        selected_template = 'classic'

    return render_template('tempage.html', templates=TEMPLATES, selected_template=selected_template, user=user)

# select template action
@app.route('/select_template/<template_id>', methods=['GET', 'POST'])
def select_template(template_id):
    if template_id not in TEMPLATES:
        if is_ajax_request():
            return jsonify({'success': False, 'error': 'Selected template not found.'}), 404
        flash("Selected template not found.", "warning")
        return redirect(url_for('tempage'))

    session['selected_template'] = template_id

    user_id = session.get('user_id')
    if user_id and user_id != 'admin':
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE users SET template = ? WHERE user_id = ?", (template_id, user_id))
        conn.commit()
        conn.close()

    if is_ajax_request():
        return jsonify({
            'success': True,
            'template': template_id,
            'template_info': TEMPLATES[template_id],
            'css_file': TEMPLATES[template_id]['css_file']
        })

    flash(f"Resume template switched to '{TEMPLATES[template_id]['name']}'!", "success")
    if user_id and user_id != 'admin':
        return redirect(url_for('previewForm'))
    return redirect(url_for('tempage'))

# profile
def get_user_by_id(user_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    contacts = c.fetchone()
    c.execute("SELECT * FROM education WHERE user_id = ? ORDER BY education_id ASC", (user_id,))
    education = c.fetchall()
    c.execute("SELECT * FROM summary WHERE user_id = ? ORDER BY summary_id DESC LIMIT 1", (user_id,))
    summary = c.fetchone()
    c.execute("SELECT * FROM experience WHERE user_id = ? ORDER BY experience_id ASC", (user_id,))
    experience = c.fetchall()
    c.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY project_id ASC", (user_id,))
    projects = c.fetchall()
    c.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY skill_id ASC", (user_id,))
    skills = c.fetchall()
    c.execute("SELECT * FROM certifications WHERE user_id = ? ORDER BY certification_id ASC", (user_id,))
    certifications = c.fetchall()
    c.execute("SELECT * FROM innovations WHERE user_id = ? ORDER BY innovation_id ASC", (user_id,))
    innovations = c.fetchall()
    c.execute("SELECT * FROM coursework WHERE user_id = ? ORDER BY coursework_id ASC", (user_id,))
    coursework = c.fetchall()
    conn.close()
    return user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework

def get_resume_dict(user_id):
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    selected_template = session.get('selected_template') or (user['template'] if user and 'template' in user.keys() and user['template'] else 'classic')
    if selected_template not in TEMPLATES:
        selected_template = 'classic'
    return {
        'user': {
            'user_id': user['user_id'] if user else None,
            'name': user['name'] if user else '',
            'email': user['email'] if user else '',
            'username': user['username'] if user else '',
            'template': selected_template
        } if user else None,
        'contacts': dict(contacts) if contacts else None,
        'summary': dict(summary) if summary else None,
        'education': [dict(e) for e in education] if education else [],
        'experience': [dict(e) for e in experience] if experience else [],
        'projects': [dict(p) for p in projects] if projects else [],
        'skills': [dict(s) for s in skills] if skills else [],
        'certifications': [dict(c) for c in certifications] if certifications else [],
        'innovations': [dict(i) for i in innovations] if innovations else [],
        'coursework': [dict(c) for c in coursework] if coursework else [],
        'selected_template': selected_template
    }

@app.route('/api/resume')
@login_required
def api_resume():
    user_id = session.get('user_id')
    return jsonify({
        'success': True,
        'resume': get_resume_dict(user_id),
        'templates': TEMPLATES
    })

@app.route("/profile")
@login_required
def profile():
    user_id = session.get("user_id")  
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    stats = {
        'education': len(education) if education else 0,
        'experience': len(experience) if experience else 0,
        'projects': len(projects) if projects else 0,
        'skills': len(skills) if skills else 0,
        'certifications': len(certifications) if certifications else 0,
        'innovations': len(innovations) if innovations else 0,
        'coursework': len(coursework) if coursework else 0
    }
    stats['total'] = sum(stats.values())
    return render_template(
        "profile.html",
        user=user,
        contacts=contacts,
        education=education,
        summary=summary,
        experience=experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
        innovations=innovations,
        coursework=coursework,
        stats=stats
    )

@app.route('/settings')
@login_required
def settings():
    return redirect(url_for('profile'))

# return home page
@app.route('/homepage')
@login_required
def homepage():
    user_id = session.get("user_id")  
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    resume_data = get_resume_dict(user_id)
    selected_template = resume_data['selected_template']
    return render_template(
        "sideBar.html",
        user=user,
        contacts=contacts,
        education=education,
        summary=summary,
        experience=experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
        innovations=innovations,
        coursework=coursework,
        selected_template=selected_template,
        templates=TEMPLATES,
        resume_data=resume_data
    )

# preview
@app.route('/previewForm')
@login_required
def previewForm():
    user_id = session.get("user_id")  
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    selected_template = session.get('selected_template') or (user['template'] if user and 'template' in user.keys() and user['template'] else 'classic')
    if selected_template not in TEMPLATES:
        selected_template = 'classic'
    return render_template('previewForm.html', user=user, contacts=contacts, summary=summary, education=education, experience=experience, projects=projects, skills=skills, certifications=certifications, innovations=innovations, coursework=coursework, selected_template=selected_template, templates=TEMPLATES)

# return to edit page
@app.route('/edit')
@login_required
def edit():
    return redirect(url_for('homepage'))

# html to pdf
# html to pdf
@app.route("/dpw/<int:user_id>")
@login_required
def pdf_html(user_id):
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    selected_template = request.args.get('template') or session.get('selected_template') or (user['template'] if user and 'template' in user.keys() and user['template'] else 'classic')
    if selected_template not in TEMPLATES:
        selected_template = 'classic'

    # 1️⃣ Render the preview page
    rendered = render_template(
        "previewForm.html",
        user=user,
        contacts=contacts,
        education=education,
        summary=summary,
        experience=experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
        innovations=innovations,
        coursework=coursework,
        selected_template=selected_template,
        templates=TEMPLATES
    )

    # 2️⃣ Extract the div with id="page1"
    soup = BeautifulSoup(rendered, 'html.parser')
    target_div = soup.find("div", {"id": "page1"})

    if not target_div:
        return "Div not found!", 404

    # Remove all edit/delete action buttons from PDF export
    for action_elem in target_div.find_all(class_="entry-actions"):
        action_elem.decompose()
    for no_print in target_div.find_all(class_="no-print"):
        no_print.decompose()

    # 3️⃣ Load CSS using relative path with os.path.join
    template_css_file = TEMPLATES.get(selected_template, {}).get('css_file', 'classic.css')
    template_css_path = os.path.join(os.getcwd(), 'static', 'templates', template_css_file)
    template_css = ""
    if os.path.exists(template_css_path):
        with open(template_css_path, 'r', encoding='utf-8') as f:
            template_css = f.read()

    # 4️⃣ Wrap the extracted div in a full HTML document with inlined CSS
    user_display_name = user['name'] if user else 'Resume'
    html_for_pdf = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Resume - {user_display_name}</title>
    <style>
        {template_css}
        .entry-actions, .no-print {{ display: none !important; }}
    </style>
</head>
<body>
    {target_div}
</body>
</html>"""

    pdf_bytes = None

    # Option A: Try WeasyPrint (cross-platform, modern CSS3)
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_for_pdf).write_pdf()
    except Exception:
        pdf_bytes = None

    # Option B: Pure-Python xhtml2pdf fallback (zero external .exe, zero GTK dependency, pure Python)
    if not pdf_bytes:
        try:
            from io import BytesIO
            from xhtml2pdf import pisa
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(html_for_pdf, dest=pdf_buffer)
            if not pisa_status.err:
                pdf_bytes = pdf_buffer.getvalue()
        except Exception:
            pdf_bytes = None

    # Option C: Fallback to wkhtmltopdf / pdfkit if present on system
    if not pdf_bytes:
        try:
            import shutil, pdfkit
            wk_path = shutil.which('wkhtmltopdf')
            if not wk_path:
                candidates = [
                    os.path.join(os.getcwd(), 'wkhtmltopdf', 'bin', 'wkhtmltopdf.exe'),
                    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
                    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
                    "/usr/local/bin/wkhtmltopdf",
                    "/usr/bin/wkhtmltopdf",
                ]
                for c in candidates:
                    if os.path.exists(c):
                        wk_path = c
                        break
            if wk_path:
                config = pdfkit.configuration(wkhtmltopdf=wk_path)
                pdf_bytes = pdfkit.from_string(html_for_pdf, False, configuration=config, options={
                    'enable-local-file-access': None,
                    'encoding': 'UTF-8',
                    'page-size': 'A4'
                })
        except Exception:
            pdf_bytes = None

    # 5️⃣ Send PDF as download if generated
    if pdf_bytes:
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Resume_{user_display_name}.pdf'
        return response

    # Option D: Universal printable browser fallback
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Resume - {user_display_name}</title>
    <style>
        {print_css}
        @media print {{
            .entry-actions, .no-print {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    {target_div}
    <script>
        window.onload = function() {{ window.print(); }};
    </script>
</body>
</html>"""


# contact form
@app.route('/contectForm', methods=['GET', 'POST'])
@login_required
def contactForm():
    if request.method == 'POST':
        fullname = request.form.get('fullName', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        p_web = request.form.get('p_web', '').strip()
        l_web = request.form.get('l_web', '').strip()
        country = request.form.get('Country', '').strip()
        state = request.form.get('State', '').strip()
        city = request.form.get('City', '').strip()

        if not fullname or not email or not phone:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Full Name, Email, and Phone number are required.'}), 400
            flash("Full Name, Email, and Phone number are required.", "danger")
            return redirect(url_for('homepage'))

        if not is_valid_email(email):
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Please enter a valid email address.'}), 400
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for('homepage'))

        if not is_valid_phone(phone):
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Please enter a valid phone number (7-20 digits).'}), 400
            flash("Please enter a valid phone number (7-20 digits).", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO contacts (user_id, fullname, email, phone, p_web, l_web, Country, State, City)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], fullname, email, phone, p_web, l_web, country, state, city))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Contact details saved successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Contact details saved successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


# education form
@app.route('/educationForm', methods=['GET', 'POST'])
@login_required
def educationForm():
    if request.method == 'POST':
        institution = request.form.get('institution', '').strip()
        degree = request.form.get('degree', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        gpa = request.form.get('gpa', '').strip()
        description = request.form.get('description', '').strip()

        if not institution or not degree:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Institution and Degree are required for Education.'}), 400
            flash("Institution and Degree are required for Education.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO education (user_id, institution, degree, startDate, endDate, gpa, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], institution, degree, startDate, endDate, gpa, description))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Education record added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Education record added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


# summary form
@app.route('/summaryForm', methods=['GET', 'POST'])
@login_required
def summaryForm():
    if request.method == 'POST':
        summary_text = request.form.get('summary', '').strip()
        if not summary_text:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Summary text cannot be empty.'}), 400
            flash("Summary text cannot be empty.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO summary (user_id, summary_text)
                VALUES (?, ?)
            """, (session['user_id'], summary_text))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Professional summary saved successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Professional summary saved successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))

# experience Form
@app.route('/experienceForm', methods=['GET', 'POST'])
@login_required
def experienceForm():
    if request.method == 'POST':
        jobTitle = request.form.get('jobTitle', '').strip()
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        employmentType = request.form.get('employmentType', '').strip()
        description = request.form.get('description', '').strip()

        if not jobTitle or not company:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Job Title and Company are required for Experience.'}), 400
            flash("Job Title and Company are required for Experience.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO experience (user_id, jobTitle, company, location, startDate, endDate, employmentType, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], jobTitle, company, location, startDate, endDate, employmentType, description))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Experience record added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Experience record added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


# project Form
@app.route('/projectForm', methods=['GET', 'POST'])
@login_required
def projectForm():
    if request.method == 'POST':
        projectName = request.form.get('projectName', '').strip()
        role = request.form.get('role', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        skills = request.form.get('skills', '').strip()
        url = request.form.get('url', '').strip()
        description = request.form.get('description', '').strip()

        if not projectName:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Project Name is required.'}), 400
            flash("Project Name is required.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO projects (user_id, projectName, role, startDate, endDate, skills, url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], projectName, role, startDate, endDate, skills, url, description))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Project added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Project added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


# skill form
@app.route('/skillForm', methods=['GET', 'POST'])
@login_required
def skillForm():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        skills = request.form.get('skills', '').strip()
        proficiency = request.form.get('proficiency', '').strip()

        if not category or not skills:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Skill Category and Skills are required.'}), 400
            flash("Skill Category and Skills are required.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO skills (user_id, category, skills, proficiency)
                VALUES (?, ?, ?, ?)
            """, (session['user_id'], category, skills, proficiency))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Skill added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Skill added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


#  innovation form
@app.route('/inn', methods=['GET', 'POST']) 
@login_required
def inn():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        associated_with = request.form.get('associatedWith', '').strip()
        description = request.form.get('description', '').strip()
        url = request.form.get('url', '').strip()

        if not title:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Title is required for Innovation / Achievement.'}), 400
            flash("Title is required for Innovation / Achievement.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO innovations (user_id, title, date, associated_with, description, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session['user_id'], title, date, associated_with, description, url))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Innovation / Achievement added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Innovation / Achievement added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))

# certificate form
@app.route('/cf', methods=['GET', 'POST'])
@login_required
def cf():
    if request.method == 'POST':
        certification_name = request.form.get('certificationName', '').strip()
        issuing_org = request.form.get('issuingOrg', '').strip()
        date_obtained = request.form.get('dateObtained', '').strip()
        expiry_date = request.form.get('expiryDate', '').strip()
        credential_id = request.form.get('credentialID', '').strip()
        url = request.form.get('url', '').strip()

        if not certification_name or not issuing_org:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Certification Name and Issuing Organization are required.'}), 400
            flash("Certification Name and Issuing Organization are required.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO certifications (user_id, certification_name, issuing_org, date_obtained, expiry_date, credential_id, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], certification_name, issuing_org, date_obtained, expiry_date, credential_id, url))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Certification added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Certification added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))

# course form
@app.route('/courseForm', methods=['GET', 'POST'])
@login_required
def courseForm():
    if request.method == 'POST':
        course_name = request.form.get('courseName', '').strip()
        course_code = request.form.get('courseCode', '').strip()
        institution = request.form.get('institution', '').strip()
        department = request.form.get('department', '').strip()
        completion_date = request.form.get('completionDate', '').strip()
        grade = request.form.get('grade', '').strip()
        skills = request.form.get('skills', '').strip()
        description = request.form.get('description', '').strip()
        projects = request.form.get('projects', '').strip()

        if not course_name or not institution:
            if is_ajax_request():
                return jsonify({'success': False, 'error': 'Course Name and Institution are required.'}), 400
            flash("Course Name and Institution are required.", "danger")
            return redirect(url_for('homepage'))

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO coursework (user_id, course_name, course_code, institution, department, completion_date, grade, skills, description, projects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], course_name, course_code, institution, department, completion_date, grade, skills, description, projects))
        conn.commit()
        conn.close()
        
        if is_ajax_request():
            return jsonify({
                'success': True,
                'message': 'Coursework added successfully!',
                'resume': get_resume_dict(session['user_id'])
            })
        flash("Coursework added successfully!", "success")
        return redirect(url_for('homepage'))
    return redirect(url_for('homepage'))


# delete summary
@app.route('/del_summary', methods=['POST'])
@app.route('/delete_summary/<int:summary_id>', methods=['POST'])
@login_required
def del_summary(summary_id=None):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM summary WHERE user_id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Summary deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Summary deleted.", "info")
    return redirect(request.referrer or url_for("homepage"))


# ==================== SPECIFIC ENTRY EDIT & DELETE ROUTES ====================

# Education
@app.route('/edit_education/<int:education_id>', methods=['GET', 'POST'])
@login_required
def edit_education(education_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        institution = request.form.get('institution', '').strip()
        degree = request.form.get('degree', '').strip()
        fieldOfStudy = request.form.get('fieldOfStudy', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        gpa = request.form.get('gpa', '').strip()
        description = request.form.get('description', '').strip()

        if not institution or not degree:
            flash("Institution and Degree are required.", "danger")
            c.execute("SELECT * FROM education WHERE education_id=? AND user_id=?", (education_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='education', entry=entry, entry_id=education_id, title='Edit Education')

        c.execute("""
            UPDATE education
            SET institution=?, degree=?, fieldOfStudy=?, startDate=?, endDate=?, gpa=?, description=?
            WHERE education_id=? AND user_id=?
        """, (institution, degree, fieldOfStudy, startDate, endDate, gpa, description, education_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Education record updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM education WHERE education_id=? AND user_id=?", (education_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='education', entry=entry, entry_id=education_id, title='Edit Education')


@app.route('/delete_education/<int:education_id>', methods=['POST'])
@login_required
def delete_education(education_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM education WHERE education_id=? AND user_id=?", (education_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Education record deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Education record deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Experience
@app.route('/edit_experience/<int:experience_id>', methods=['GET', 'POST'])
@login_required
def edit_experience(experience_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        jobTitle = request.form.get('jobTitle', '').strip()
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        employmentType = request.form.get('employmentType', '').strip()
        description = request.form.get('description', '').strip()

        if not jobTitle or not company:
            flash("Job Title and Company are required.", "danger")
            c.execute("SELECT * FROM experience WHERE experience_id=? AND user_id=?", (experience_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='experience', entry=entry, entry_id=experience_id, title='Edit Experience')

        c.execute("""
            UPDATE experience
            SET jobTitle=?, company=?, location=?, startDate=?, endDate=?, employmentType=?, description=?
            WHERE experience_id=? AND user_id=?
        """, (jobTitle, company, location, startDate, endDate, employmentType, description, experience_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Experience record updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM experience WHERE experience_id=? AND user_id=?", (experience_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='experience', entry=entry, entry_id=experience_id, title='Edit Experience')


@app.route('/delete_experience/<int:experience_id>', methods=['POST'])
@login_required
def delete_experience(experience_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM experience WHERE experience_id=? AND user_id=?", (experience_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Experience record deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Experience record deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Projects
@app.route('/edit_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        projectName = request.form.get('projectName', '').strip()
        role = request.form.get('role', '').strip()
        startDate = request.form.get('startDate', '').strip()
        endDate = request.form.get('endDate', '').strip()
        skills = request.form.get('skills', '').strip()
        url = request.form.get('url', '').strip()
        description = request.form.get('description', '').strip()

        if not projectName:
            flash("Project Name is required.", "danger")
            c.execute("SELECT * FROM projects WHERE project_id=? AND user_id=?", (project_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='project', entry=entry, entry_id=project_id, title='Edit Project')

        c.execute("""
            UPDATE projects
            SET projectName=?, role=?, startDate=?, endDate=?, skills=?, url=?, description=?
            WHERE project_id=? AND user_id=?
        """, (projectName, role, startDate, endDate, skills, url, description, project_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Project updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM projects WHERE project_id=? AND user_id=?", (project_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='project', entry=entry, entry_id=project_id, title='Edit Project')


@app.route('/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project_specific(project_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE project_id=? AND user_id=?", (project_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Project deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Project deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Skills
@app.route('/edit_skill/<int:skill_id>', methods=['GET', 'POST'])
@login_required
def edit_skill(skill_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        skills = request.form.get('skills', '').strip()
        proficiency = request.form.get('proficiency', '').strip()

        if not category or not skills:
            flash("Skill Category and Skills are required.", "danger")
            c.execute("SELECT * FROM skills WHERE skill_id=? AND user_id=?", (skill_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='skill', entry=entry, entry_id=skill_id, title='Edit Skill')

        c.execute("""
            UPDATE skills
            SET category=?, skills=?, proficiency=?
            WHERE skill_id=? AND user_id=?
        """, (category, skills, proficiency, skill_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Skill updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM skills WHERE skill_id=? AND user_id=?", (skill_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='skill', entry=entry, entry_id=skill_id, title='Edit Skill')


@app.route('/delete_skill/<int:skill_id>', methods=['POST'])
@login_required
def delete_skill(skill_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM skills WHERE skill_id=? AND user_id=?", (skill_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Skill deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Skill deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Certifications
@app.route('/edit_certification/<int:certification_id>', methods=['GET', 'POST'])
@login_required
def edit_certification(certification_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        certification_name = request.form.get('certification_name', '').strip()
        issuing_org = request.form.get('issuing_org', '').strip()
        date_obtained = request.form.get('date_obtained', '').strip()
        expiry_date = request.form.get('expiry_date', '').strip()
        credential_id = request.form.get('credential_id', '').strip()
        url = request.form.get('url', '').strip()

        if not certification_name or not issuing_org:
            flash("Certification Name and Issuing Organization are required.", "danger")
            c.execute("SELECT * FROM certifications WHERE certification_id=? AND user_id=?", (certification_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='certification', entry=entry, entry_id=certification_id, title='Edit Certification')

        c.execute("""
            UPDATE certifications
            SET certification_name=?, issuing_org=?, date_obtained=?, expiry_date=?, credential_id=?, url=?
            WHERE certification_id=? AND user_id=?
        """, (certification_name, issuing_org, date_obtained, expiry_date, credential_id, url, certification_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Certification updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM certifications WHERE certification_id=? AND user_id=?", (certification_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='certification', entry=entry, entry_id=certification_id, title='Edit Certification')


@app.route('/delete_certification/<int:certification_id>', methods=['POST'])
@login_required
def delete_certification(certification_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM certifications WHERE certification_id=? AND user_id=?", (certification_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Certification deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Certification deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Innovations / Extra-Curricular
@app.route('/edit_innovation/<int:innovation_id>', methods=['GET', 'POST'])
@login_required
def edit_innovation(innovation_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        associated_with = request.form.get('associated_with', '').strip()
        description = request.form.get('description', '').strip()
        url = request.form.get('url', '').strip()

        if not title:
            flash("Title is required for Innovation / Achievement.", "danger")
            c.execute("SELECT * FROM innovations WHERE innovation_id=? AND user_id=?", (innovation_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='innovation', entry=entry, entry_id=innovation_id, title='Edit Extra-Curricular Activity')

        c.execute("""
            UPDATE innovations
            SET title=?, date=?, associated_with=?, description=?, url=?
            WHERE innovation_id=? AND user_id=?
        """, (title, date, associated_with, description, url, innovation_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Innovation / Achievement updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM innovations WHERE innovation_id=? AND user_id=?", (innovation_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='innovation', entry=entry, entry_id=innovation_id, title='Edit Extra-Curricular Activity')


@app.route('/delete_innovation/<int:innovation_id>', methods=['POST'])
@login_required
def delete_innovation(innovation_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM innovations WHERE innovation_id=? AND user_id=?", (innovation_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Innovation / Achievement deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Innovation / Achievement deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Coursework
@app.route('/edit_coursework/<int:coursework_id>', methods=['GET', 'POST'])
@login_required
def edit_coursework(coursework_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        course_name = request.form.get('course_name', '').strip()
        course_code = request.form.get('course_code', '').strip()
        institution = request.form.get('institution', '').strip()
        department = request.form.get('department', '').strip()
        completion_date = request.form.get('completion_date', '').strip()
        grade = request.form.get('grade', '').strip()
        skills = request.form.get('skills', '').strip()
        description = request.form.get('description', '').strip()
        projects = request.form.get('projects', '').strip()

        if not course_name or not institution:
            flash("Course Name and Institution are required.", "danger")
            c.execute("SELECT * FROM coursework WHERE coursework_id=? AND user_id=?", (coursework_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='coursework', entry=entry, entry_id=coursework_id, title='Edit Coursework')

        c.execute("""
            UPDATE coursework
            SET course_name=?, course_code=?, institution=?, department=?, completion_date=?, grade=?, skills=?, description=?, projects=?
            WHERE coursework_id=? AND user_id=?
        """, (course_name, course_code, institution, department, completion_date, grade, skills, description, projects, coursework_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Coursework updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM coursework WHERE coursework_id=? AND user_id=?", (coursework_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='coursework', entry=entry, entry_id=coursework_id, title='Edit Coursework')


@app.route('/delete_coursework/<int:coursework_id>', methods=['POST'])
@login_required
def delete_coursework(coursework_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM coursework WHERE coursework_id=? AND user_id=?", (coursework_id, session['user_id']))
    conn.commit()
    conn.close()
    if is_ajax_request():
        return jsonify({
            'success': True,
            'message': 'Coursework deleted.',
            'resume': get_resume_dict(session['user_id'])
        })
    flash("Coursework deleted.", "info")
    return redirect(request.referrer or url_for('homepage'))


# Summary
@app.route('/edit_summary/<int:summary_id>', methods=['GET', 'POST'])
@login_required
def edit_summary(summary_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        summary_text = request.form.get('summary_text', '').strip()
        if not summary_text:
            flash("Summary text cannot be empty.", "danger")
            c.execute("SELECT * FROM summary WHERE summary_id=? AND user_id=?", (summary_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='summary', entry=entry, entry_id=summary_id, title='Edit Summary')

        c.execute("UPDATE summary SET summary_text=? WHERE summary_id=? AND user_id=?", (summary_text, summary_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Summary updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM summary WHERE summary_id=? AND user_id=?", (summary_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='summary', entry=entry, entry_id=summary_id, title='Edit Summary')


@app.route('/delete_summary/<int:summary_id>', methods=['POST'])
@login_required
def delete_summary_specific(summary_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM summary WHERE summary_id=? AND user_id=?", (summary_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Summary deleted.", "info")
    return redirect(url_for('previewForm'))


# Contact
@app.route('/edit_contact/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def edit_contact(contact_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if request.method == 'POST':
        fullname = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        p_web = request.form.get('p_web', '').strip()
        l_web = request.form.get('l_web', '').strip()
        Country = request.form.get('Country', '').strip()
        State = request.form.get('State', '').strip()
        City = request.form.get('City', '').strip()

        if not fullname or not email or not phone:
            flash("Full Name, Email, and Phone number are required.", "danger")
            c.execute("SELECT * FROM contacts WHERE id=? AND user_id=?", (contact_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='contact', entry=entry, entry_id=contact_id, title='Edit Contact Details')

        if not is_valid_email(email):
            flash("Please enter a valid email address.", "danger")
            c.execute("SELECT * FROM contacts WHERE id=? AND user_id=?", (contact_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='contact', entry=entry, entry_id=contact_id, title='Edit Contact Details')

        if not is_valid_phone(phone):
            flash("Please enter a valid phone number (7-20 digits).", "danger")
            c.execute("SELECT * FROM contacts WHERE id=? AND user_id=?", (contact_id, session['user_id']))
            entry = c.fetchone()
            conn.close()
            return render_template('edit_entry.html', section='contact', entry=entry, entry_id=contact_id, title='Edit Contact Details')

        c.execute("""
            UPDATE contacts
            SET fullname=?, email=?, phone=?, p_web=?, l_web=?, Country=?, State=?, City=?
            WHERE id=? AND user_id=?
        """, (fullname, email, phone, p_web, l_web, Country, State, City, contact_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Contact details updated successfully!", "success")
        return redirect(url_for('previewForm'))

    c.execute("SELECT * FROM contacts WHERE id=? AND user_id=?", (contact_id, session['user_id']))
    entry = c.fetchone()
    conn.close()
    if not entry:
        return redirect(url_for('previewForm'))
    return render_template('edit_entry.html', section='contact', entry=entry, entry_id=contact_id, title='Edit Contact Details')




# ==================== ADMIN DASHBOARD ROUTES ====================

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT 
            u.user_id, 
            u.name, 
            u.email, 
            u.username,
            (SELECT phone FROM contacts WHERE user_id = u.user_id LIMIT 1) AS phone,
            (SELECT City FROM contacts WHERE user_id = u.user_id LIMIT 1) AS city,
            (SELECT COUNT(*) FROM education WHERE user_id = u.user_id) AS edu_count,
            (SELECT COUNT(*) FROM experience WHERE user_id = u.user_id) AS exp_count,
            (SELECT COUNT(*) FROM projects WHERE user_id = u.user_id) AS proj_count,
            (SELECT COUNT(*) FROM skills WHERE user_id = u.user_id) AS skill_count
        FROM users u
        ORDER BY u.user_id DESC
    """)
    users = c.fetchall()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM projects")
    total_projects = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM education")
    total_education = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM experience")
    total_experience = c.fetchone()[0]
    conn.close()

    stats = {
        'total_users': total_users,
        'total_projects': total_projects,
        'total_education': total_education,
        'total_experience': total_experience
    }
    return render_template("admin.html", users=users, stats=stats)


@app.route("/admin/resume/<int:user_id>")
@admin_required
def admin_view_resume(user_id):
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    if not user:
        return redirect(url_for('admin_dashboard'))
    selected_template = user['template'] if user and 'template' in user.keys() and user['template'] else 'classic'
    if selected_template not in TEMPLATES:
        selected_template = 'classic'
    return render_template(
        "previewForm.html",
        user=user,
        contacts=contacts,
        summary=summary,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        certifications=certifications,
        innovations=innovations,
        coursework=coursework,
        selected_template=selected_template,
        templates=TEMPLATES,
        is_admin=True
    )


@app.route("/admin/delete_user/<int:user_id>", methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    child_tables = [
        "contacts", "education", "summary", "experience",
        "projects", "skills", "certifications", "innovations", "coursework"
    ]
    for table in child_tables:
        try:
            c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
        except Exception:
            pass
    c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash(f"User #{user_id} and all associated records have been permanently deleted.", "info")
    return redirect(url_for('admin_dashboard'))













if __name__ == '__main__':
    app.run(debug=True)
