import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    # c.execute('''
    #     DROP TABLE IF EXISTS education;
    # ''')

    c.execute('''
              CREATE TABLE IF NOT EXISTS admin (
                  admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  password TEXT NOT NULL
              )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    c.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fullname TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                p_web TEXT NOT NULL,
                l_web TEXT NOT NULL,
                Country TEXT NOT NULL,
                State TEXT NOT NULL,
                City TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')


    c.execute('''
            CREATE TABLE IF NOT EXISTS education (
                education_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                institution TEXT,
                fieldOfStudy TEXT,
                degree TEXT,
                startDate DATE,
                endDate DATE,
                gpa TEXT,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS summary (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            summary_text TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS experience (
                experience_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                jobTitle TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                startDate TEXT NOT NULL,
                endDate TEXT,
                employmentType TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                projectName TEXT NOT NULL,
                role TEXT NOT NULL,
                startDate TEXT NOT NULL,
                endDate TEXT,
                skills TEXT,
                url TEXT,
                description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                skills TEXT NOT NULL,
                proficiency TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS innovations (
                innovation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                associated_with TEXT,
                description TEXT NOT NULL,
                url TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS certifications (
                certification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                certification_name TEXT NOT NULL,
                issuing_org TEXT NOT NULL,
                date_obtained TEXT NOT NULL,
                expiry_date TEXT,
                credential_id TEXT,
                url TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS coursework (
                coursework_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_name TEXT NOT NULL,
                course_code TEXT,
                institution TEXT NOT NULL,
                department TEXT,
                completion_date TEXT NOT NULL,
                grade INTEGER,
                skills TEXT,
                description TEXT,
                projects TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')



    conn.commit()
    conn.close()