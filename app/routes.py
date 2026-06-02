from flask import Blueprint, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import mysql
import MySQLdb.cursors


import os
from PyPDF2 import PdfReader

UPLOAD_FOLDER = "app/static/resumes"
main = Blueprint('main', __name__)

import re

def analyze_resume(text, student_profile):

    score = 0
    suggestions = []

    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    # ---------------------------
    # 1️⃣ Section Detection (40 Points)
    # ---------------------------
    sections = {
        "education": 10,
        "experience": 10,
        "skills": 10,
        "projects": 10
    }

    for section, weight in sections.items():
        if section in text_lower:
            score += weight
        else:
            suggestions.append(f"Missing proper {section.capitalize()} section.")

    # ---------------------------
    # 2️⃣ Resume Length (10 Points)
    # ---------------------------
    if 400 <= word_count <= 900:
        score += 10
    else:
        suggestions.append("Resume length should ideally be between 400-900 words.")

    # ---------------------------
    # 3️⃣ Strong Action Verbs (10 Points)
    # ---------------------------
    action_verbs = [
        "developed", "built", "implemented", "designed",
        "optimized", "created", "led", "improved", "achieved"
    ]

    verb_matches = sum(1 for verb in action_verbs if verb in text_lower)

    if verb_matches >= 3:
        score += 10
    else:
        suggestions.append("Use strong action verbs like Developed, Built, Implemented etc.")

    # ---------------------------
    # 4️⃣ Technical Keyword Density (20 Points)
    # ---------------------------
    tech_keywords = [
        "python", "java", "sql", "machine learning",
        "flask", "api", "data", "react", "django"
    ]

    keyword_matches = sum(text_lower.count(word) for word in tech_keywords)

    if keyword_matches >= 5:
        score += 20
    elif keyword_matches >= 3:
        score += 10
    else:
        suggestions.append("Increase technical keyword density for better ATS performance.")

    # ---------------------------
    # 5️⃣ 🔥 Profile Skill Matching (20 Points)
    # ---------------------------
    if student_profile and student_profile['skills']:

        profile_skills = [
            skill.strip().lower()
            for skill in student_profile['skills'].split(",")
        ]

        matched_skills = [
            skill for skill in profile_skills
            if skill in text_lower
        ]

        skill_match_percent = int((len(matched_skills) / len(profile_skills)) * 100) if profile_skills else 0

        score += int(skill_match_percent * 0.2)  # Max 20 points

        missing_skills = set(profile_skills) - set(matched_skills)

        if missing_skills:
            suggestions.append(
                f"Add these missing profile skills in resume: {', '.join(missing_skills)}"
            )

    # ---------------------------
    # Final Score Cap
    # ---------------------------
    if score > 100:
        score = 100

    return score, suggestions


@main.route("/student/resume", methods=["GET", "POST"])
def resume_check():
    if 'user_id' not in session or session['role'] != "student":
        return redirect("/login")

    user_id = session['user_id']

    if request.method == "POST":
        file = request.files['resume']

        if file.filename.endswith(".pdf"):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            # Extract text
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            # 🔥 Basic ATS Analysis
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            cur.execute("SELECT * FROM student_profiles WHERE user_id=%s", (user_id,))
            student_profile = cur.fetchone()

            ats_score, suggestions_list = analyze_resume(text, student_profile)

            suggestions = "\n".join(suggestions_list)

            cur = mysql.connection.cursor()

            cur.execute("""
                INSERT INTO student_resumes 
                (user_id, resume_file, extracted_text, ats_score, suggestions)
                VALUES (%s,%s,%s,%s,%s)
            """, (user_id, file.filename, text, ats_score, suggestions))

            mysql.connection.commit()
            cur.close()

            return render_template("resume_report.html",
                                   score=ats_score,
                                   suggestions=suggestions_list)

    return render_template("resume_upload.html")





@main.route("/")
def home():
    return render_template("index.html")


# ================= REGISTER =================
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form['full_name']
        email = request.form['email']
        contact = request.form['contact']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing = cur.fetchone()

        if existing:
            flash("Email already registered!", "danger")
            return redirect("/register")

        cur.execute("""
            INSERT INTO users (full_name, email, contact, password, role)
            VALUES (%s,%s,%s,%s,%s)
        """, (full_name, email, contact, password, role,0))

        mysql.connection.commit()
        cur.close()

        flash("Registration successful! Wait for admin approval.", "success")
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:

            # ✅ FIXED LINE
            if not user['is_approved']:
                flash("Your account is not approved yet. Please wait for admin approval.", "warning")
                return redirect("/login")

            if check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['name'] = user['full_name']

                if user['role'] == "student":
                    return redirect("/student/dashboard")
                elif user['role'] == "alumni":
                    return redirect("/alumni/dashboard")
                elif user['role'] == "admin":
                    return redirect("/admin/dashboard")

            else:
                flash("Invalid password!", "danger")
        else:
            flash("Email not found!", "danger")

    return render_template("login.html")

# ================= STUDENT DASHBOARD =================
@main.route("/student/dashboard")
def student_dashboard():
    if 'user_id' not in session or session['role'] != "student":
        return redirect("/login")

    user_id = session['user_id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check profile completion
    cur.execute("SELECT profile_completed, profile_strength FROM student_profiles WHERE user_id=%s", (user_id,))
    profile = cur.fetchone()

    if not profile or profile['profile_completed'] == 0:
        flash("Please complete your profile first.", "warning")
        return redirect("/student/profile")

    profile_strength = profile['profile_strength']

    cur.close()

    return render_template(
        "student_dashboard.html",
        name=session['name'],
        profile_strength=profile_strength
    )


# ================= ALUMNI DASHBOARD =================
@main.route("/alumni/dashboard")
def alumni_dashboard():
    if 'user_id' not in session or session['role'] != "alumni":
        return redirect("/login")

    return render_template("alumni_dashboard.html", name=session['name'])


# ================= LOGOUT =================
@main.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= ADMIN DASHBOARD =================
@main.route("/admin/dashboard")
def admin_dashboard():
    if 'user_id' not in session or session['role'] != "admin":
        return redirect("/login")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("SELECT * FROM users WHERE is_approved=0")
    pending_users = cur.fetchall()

    cur.execute("SELECT * FROM users WHERE is_approved=1")
    approved_users = cur.fetchall()

    cur.close()

    return render_template(
        "admin_dashboard.html",
        name=session['name'],
        pending_users=pending_users,
        approved_users=approved_users
    )


@main.route("/admin/approve/<int:user_id>")
def approve_user(user_id):
    if session.get('role') != "admin":
        return redirect("/login")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("UPDATE users SET is_approved=1 WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

    return redirect("/admin/dashboard")


@main.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    if session.get('role') != "admin":
        return redirect("/login")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

    return redirect("/admin/dashboard")


# ================= STUDENT PROFILE =================
@main.route("/student/profile", methods=["GET", "POST"])
def student_profile():
    if 'user_id' not in session or session['role'] != "student":
        return redirect("/login")

    user_id = session['user_id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == "POST":

        data = {
            "college": request.form.get("college", "").strip(),
            "branch": request.form.get("branch", "").strip(),
            "graduation_year": request.form.get("graduation_year", "").strip(),
            "current_year": request.form.get("current_year", "").strip(),
            "skills": request.form.get("skills", "").strip(),
            "certifications": request.form.get("certifications", "").strip(),
            "interests": request.form.get("interests", "").strip(),
            "preferred_domain": request.form.get("preferred_domain", "").strip(),
            "preferred_location": request.form.get("preferred_location", "").strip(),
            "bio": request.form.get("bio", "").strip(),
            "linkedin": request.form.get("linkedin", "").strip(),
            "github": request.form.get("github", "").strip(),
            "portfolio": request.form.get("portfolio", "").strip(),
        }

        # 🔥 PROFILE STRENGTH CALCULATION
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v != "")
        profile_strength = int((filled_fields / total_fields) * 100)

        profile_completed = 1 if profile_strength >= 60 else 0

        # Check existing profile
        cur.execute("SELECT * FROM student_profiles WHERE user_id=%s", (user_id,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE student_profiles SET
                college=%s, branch=%s, graduation_year=%s,
                current_year=%s, skills=%s, certifications=%s,
                interests=%s, preferred_domain=%s,
                preferred_location=%s, bio=%s,
                linkedin=%s, github=%s, portfolio=%s,
                profile_strength=%s,
                profile_completed=%s
                WHERE user_id=%s
            """, (
                data["college"], data["branch"], data["graduation_year"],
                data["current_year"], data["skills"], data["certifications"],
                data["interests"], data["preferred_domain"],
                data["preferred_location"], data["bio"],
                data["linkedin"], data["github"], data["portfolio"],
                profile_strength, profile_completed, user_id
            ))
        else:
            cur.execute("""
                INSERT INTO student_profiles
                (user_id, college, branch, graduation_year,
                 current_year, skills, certifications,
                 interests, preferred_domain, preferred_location,
                 bio, linkedin, github, portfolio,
                 profile_strength, profile_completed)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_id,
                data["college"], data["branch"], data["graduation_year"],
                data["current_year"], data["skills"], data["certifications"],
                data["interests"], data["preferred_domain"],
                data["preferred_location"], data["bio"],
                data["linkedin"], data["github"], data["portfolio"],
                profile_strength, profile_completed
            ))

        mysql.connection.commit()

        flash(f"Profile updated successfully! Strength: {profile_strength}%", "success")
        return redirect("/student/profile")

    # GET profile
    cur.execute("SELECT * FROM student_profiles WHERE user_id=%s", (user_id,))
    profile = cur.fetchone()

    cur.close()

    return render_template("student_profile.html", profile=profile)
