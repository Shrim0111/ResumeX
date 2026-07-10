
import requests
import pdfkit, os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request,session,make_response,url_for,redirect
import sqlite3
from database import init_db
import database
# from alter import init_db
app = Flask(__name__)  
database.init_db()
app.secret_key = "your_secret_key_here" 
API_KEY = "sk_d30294205f6d06cce706e3e8ada1c859b4798c9b"

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
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "123":
         return render_template('admin.html')
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0] 
            return render_template('sideBar.html', user=user)

        else:
            return "Incorrect details please try again"

    return render_template('login.html')


# sign up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("""
                INSERT INTO users (name,email,username, password)
                VALUES (?, ?, ?, ?)
            """, (name,email,username,password))
            conn.commit()
            conn.close()

            return  render_template('login.html')

        except sqlite3.IntegrityError:
            return "You have already registered please login"

    return render_template('signup.html')

# log out
@app.route('/logout')
def logout():
    session.clear()
    return render_template('index.html')



@app.route('/index')
def index():
    return render_template('index.html')

# template
@app.route('/tempage')
def tempage():
    return render_template('tempage.html')

# profile
def get_user_by_id(user_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    contacts = c.fetchone()
    c.execute("SELECT * FROM education WHERE user_id = ? ORDER BY  education_id DESC LIMIT 5", (user_id,))
    education = c.fetchall()
    c.execute("SELECT * FROM summary WHERE user_id = ? ORDER BY summary_id DESC LIMIT 1", (user_id,))
    summary = c.fetchone()
    c.execute("SELECT * FROM experience WHERE user_id = ? ORDER BY experience_id DESC LIMIT 5", (user_id,))
    experience = c.fetchall()
    c.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY  project_id DESC LIMIT 3" , (user_id,))
    projects = c.fetchall()
    c.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY skill_id DESC LIMIT 5", (user_id,))
    skills = c.fetchall()
    c.execute("SELECT * FROM certifications WHERE user_id = ? ORDER BY certification_id DESC LIMIT 5", (user_id,))
    certifications = c.fetchall()
    c.execute("SELECT * FROM innovations  WHERE user_id = ? ORDER BY innovation_id DESC LIMIT 5", (user_id,))
    innovations  = c.fetchall()
    c.execute("SELECT * FROM coursework WHERE user_id = ? ORDER BY coursework_id DESC LIMIT 5", (user_id,))
    coursework = c.fetchall()
    conn.close()
    return user, contacts, education, summary, experience,projects,skills,certifications,innovations,coursework


@app.route("/profile")
def profile():
    user_id = session.get("user_id")  
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    return render_template("profile.html", user=user, contacts=contacts , education=education, summary=summary, experience=experience, projects=projects, skills=skills, certifications=certifications, innovations=innovations, coursework=coursework)

# return home page
@app.route('/homepage')
def homepage():
    return render_template("sideBar.html")


# preview
@app.route('/previewForm')
def previewForm():
    user_id = session.get("user_id")  
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    return render_template('previewForm.html', user=user, contacts=contacts, summary=summary, education=education, experience=experience, projects=projects, skills=skills, certifications=certifications, innovations=innovations, coursework=coursework)

# return to edit page
@app.route('/edit')
def edit():
    return render_template("sideBar.html")

# html to pdf
options = {
    'enable-local-file-access': None,
    'no-stop-slow-scripts': None,
    'page-size': 'A4',
    'encoding': "UTF-8"

}

@app.route("/dpw/<int:user_id>")
def pdf_html(user_id):
    # Path to your CSS
    css_path = os.path.join(os.getcwd(), 'static', 'preview1.css')
    user, contacts, education, summary, experience, projects, skills, certifications, innovations, coursework = get_user_by_id(user_id)
    # 1️⃣ Render the whole preview page as HTML string
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
        coursework=coursework
    )

    # 2️⃣ Extract the div with id="page1"
    soup = BeautifulSoup(rendered, 'html.parser')
    target_div = soup.find("div", {"id": "page1"})

    if not target_div:
        return "Div not found!", 404

    # 3️⃣ Wrap the extracted div in a full HTML document
    html_for_pdf = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="file:///E:/New_folder_(2)/RBPY/static/print.css">
    </head>
    <body>
        {target_div}
    </body>
    </html>
    """

    # 4️⃣ wkhtmltopdf config
    path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    options = {
        'enable-local-file-access': None,
        'encoding': 'UTF-8',
        'page-size': 'A4'
    }

    # 5️⃣ Generate PDF from only that div
    pdf = pdfkit.from_string(html_for_pdf, False, configuration=config, options=options)

    # 6️⃣ Send PDF as download
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=YourResume.pdf'
    return response


# contact form
@app.route('/contectForm', methods=['GET' ,'POST'])
def contactForm():
    if request.method == 'POST':
        fullname = request.form['fullName']
        email = request.form['email']
        phone = request.form['phone']
        p_web = request.form['p_web']
        l_web = request.form['l_web']
        country = request.form['Country']
        state = request.form['State']
        city = request.form['City']


        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO contacts (user_id, fullname, email, phone, p_web, l_web, Country, State, City)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], fullname, email, phone, p_web, l_web, country, state, city))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


# education form
@app.route('/educationForm', methods=['GET', 'POST'])
def educationForm():
    if request.method == 'POST':
        institution = request.form['institution']
        degree = request.form['degree']
        startDate = request.form['startDate']
        endDate = request.form['endDate']
        gpa = request.form['gpa']
        description = request.form['description']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO education (user_id, institution, degree, startDate, endDate, gpa, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], institution, degree, startDate, endDate, gpa, description))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


# summary form
@app.route('/summaryForm', methods=['GET', 'POST'])
def summaryForm():
    if request.method == 'POST':
        summary_text = request.form['summary']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO summary (user_id, summary_text)
                VALUES (?, ?)
            """, (session['user_id'], summary_text))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')

# experince Form
@app.route('/experienceForm', methods=['GET', 'POST'])
def experienceForm():
    if request.method == 'POST':
        jobTitle = request.form['jobTitle']
        company = request.form['company']
        location = request.form.get('location')
        startDate = request.form['startDate']
        endDate = request.form.get('endDate')
        employmentType = request.form['employmentType']
        description = request.form.get('description')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO experience (user_id, jobTitle, company, location, startDate, endDate, employmentType, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], jobTitle, company, location, startDate, endDate, employmentType, description))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


# project Form
@app.route('/projectForm', methods=['GET', 'POST'])
def projectForm():
    if request.method == 'POST':
        projectName = request.form['projectName']
        role = request.form['role']
        startDate = request.form['startDate']
        endDate = request.form.get('endDate')
        skills = request.form.get('skills')
        url = request.form.get('url')
        description = request.form.get('description')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO projects (user_id, projectName, role, startDate, endDate, skills, url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], projectName, role, startDate, endDate, skills, url, description))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


# skill form
@app.route('/skillForm', methods=['GET', 'POST'])
def skillForm():
    if request.method == 'POST':
        category = request.form['category']
        skills = request.form['skills']
        proficiency = request.form['proficiency']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO skills (user_id, category, skills, proficiency)
                VALUES (?, ?, ?, ?)
            """, (session['user_id'], category, skills, proficiency))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


#  innovation form
@app.route('/inn', methods=['GET', 'POST']) 
def inn():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        associated_with = request.form['associatedWith']
        description = request.form['description']
        url = request.form['url']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO innovations (user_id, title, date, associated_with, description, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session['user_id'], title, date, associated_with, description, url))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')

# certificate form
@app.route('/cf', methods=['GET', 'POST'])
def cf():
    if request.method == 'POST':
        certification_name = request.form['certificationName']
        issuing_org = request.form['issuingOrg']
        date_obtained = request.form['dateObtained']
        expiry_date = request.form.get('expiryDate')
        credential_id = request.form.get('credentialID')
        url = request.form.get('url')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO certifications (user_id, certification_name, issuing_org, date_obtained, expiry_date, credential_id, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], certification_name, issuing_org, date_obtained, expiry_date, credential_id, url))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')

# course form
@app.route('/courseForm', methods=['GET', 'POST'])
def courseForm():
    if request.method == 'POST':
        course_name = request.form['courseName']
        course_code = request.form.get('courseCode', '')
        institution = request.form['institution']
        department = request.form.get('department', '')
        completion_date = request.form['completionDate']
        grade = request.form.get('grade', None)
        skills = request.form.get('skills', '')
        description = request.form.get('description', '')
        projects = request.form.get('projects', '')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""
                INSERT INTO coursework (user_id, course_name, course_code, institution, department, completion_date, grade, skills, description, projects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session['user_id'], course_name, course_code, institution, department, completion_date, grade, skills, description, projects))
        conn.commit()
        conn.close()
        return render_template('sideBar.html')
    return render_template('sideBar.html')


    # delete summary
@app.route('/del_summary', methods=['POST'])
def del_summary():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM summary WHERE user_id = ?", (session['user_id'],))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))

# delet projects
@app.route('/del_project', methods=['POST'])
def delete_project():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE user_id = ? AND project_id = (SELECT project_id FROM projects WHERE user_id = ? ORDER BY project_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('previewForm'))  # Redirect back to preview page


@app.route('/del_education', methods=['POST'])
def del_education():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM education WHERE user_id = ? AND education_id = (SELECT education_id FROM education WHERE user_id = ? ORDER BY education_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))


@app.route('/del_skills', methods=['POST'])
def del_skills():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM skills WHERE user_id = ? AND skill_id = (SELECT skill_id FROM skills WHERE user_id = ? ORDER BY skill_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))

@app.route('/del_experience', methods=['POST'])
def del_experiences():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM experience WHERE user_id = ? AND experience_id = (SELECT experience_id FROM experience WHERE user_id = ? ORDER BY experience_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))

@app.route('/del_certifications', methods=['POST'])
def del_certifivateion():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM certifications WHERE user_id = ? AND certification_id = (SELECT certification_id FROM certifications WHERE user_id = ? ORDER BY certification_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))

@app.route('/del_extra_curricular', methods=['POST'])
def del_extra():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM innovations WHERE user_id = ? AND innovation_id = (SELECT innovation_id FROM innovations WHERE user_id = ? ORDER BY innovation_id ASC LIMIT 1)", (session['user_id'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("previewForm"))




# @app.route("/abc")
# def admin_dashboard():
#     conn = sqlite3.connect("database.db")
#     cursor = conn.execute("SELECT * FROM users where user_id = 1")
#     users = cursor.fetchall()
#     conn.close()
#     return render_template("admin.html", users=users)

# @app.route("/abc")
# def admin_dashboard():
#     conn = sqlite3.connect("database.db")
#     conn.row_factory = sqlite3.Row
#     cursor = conn.execute("SELECT * FROM users WHERE user_id = 1")
#     user = cursor.fetchone()  # fetchone since you're expecting one user
#     conn.close()
#     return render_template("admin.html", user=user)

# @app.route("/admin")
# def show_users():
#     conn = sqlite3.connect("database.db")
#     conn.row_factory = sqlite3.Row  # allows dict-style access
#     cursor = conn.execute("SELECT * FROM users")
#     users = cursor.fetchall()
#     conn.close()
#     return render_template("users.html", users=users)













if __name__ == '__main__':
    app.run(debug=True)
