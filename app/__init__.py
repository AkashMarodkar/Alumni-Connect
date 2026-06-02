from flask import Flask
from flask_mysqldb import MySQL
from flask import Flask, render_template
from flask import flash
from flask import flash

mysql = MySQL()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    print("MYSQL_HOST =", app.config.get("MYSQL_HOST"))
    print("MYSQL_PORT =", app.config.get("MYSQL_PORT"))
    print("MYSQL_USER =", app.config.get("MYSQL_USER"))
    print("MYSQL_DB =", app.config.get("MYSQL_DB"))
    print("MYSQL_PASSWORD =", app.config.get("MYSQL_PASSWORD"))

    mysql.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    @app.route("/alumni-dashboard")
    def alumni_dashboard():
        return render_template("alumni_dashboard.html")

    @app.route("/alumni-requests")
    def alumni_requests():
        return "<h2>Mentorship Requests Page</h2>"

    @app.route("/alumni-mentees")
    def alumni_mentees():

        if "user_id" not in session or session.get("role") != "alumni":
            return redirect(url_for("login"))

        mentor_id = session["user_id"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT users.full_name,
                   users.email,
                   mentor_requests.requested_at
            FROM mentor_requests
            JOIN users ON mentor_requests.student_id = users.id
            WHERE mentor_requests.mentor_id = %s
            AND mentor_requests.status = 'accepted'
            ORDER BY mentor_requests.requested_at DESC
        """, (mentor_id,))

        mentees = cur.fetchall()

        cur.close()

        return render_template("alumni_mentees.html", mentees=mentees)

    @app.route("/alumni-jobs")
    def alumni_jobs():

        alumni_id = session["user_id"]
        search = request.args.get("search")
        job_type = request.args.get("job_type")

        cur = mysql.connection.cursor()

        query = "SELECT * FROM jobs WHERE alumni_id = %s"
        params = [alumni_id]

        if search:
            query += " AND title LIKE %s"
            params.append(f"%{search}%")

        if job_type:
            query += " AND job_type = %s"
            params.append(job_type)

        query += " ORDER BY created_at DESC"

        cur.execute(query, tuple(params))
        jobs = cur.fetchall()
        cur.close()

        return render_template("alumni_jobs.html", jobs=jobs)


    @app.route("/alumni-delete-job/<int:job_id>")
    def alumni_delete_job(job_id):
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for("alumni_jobs"))

    @app.route("/alumni-edit-job/<int:job_id>", methods=["GET", "POST"])
    def alumni_edit_job(job_id):

        cur = mysql.connection.cursor()

        if request.method == "POST":
            title = request.form.get("title")
            company = request.form.get("company")
            location = request.form.get("location")
            job_type = request.form.get("job_type")
            experience = request.form.get("experience")
            salary = request.form.get("salary")
            skills = request.form.get("skills")
            description = request.form.get("description")
            deadline = request.form.get("deadline")

            cur.execute("""
                UPDATE jobs 
                SET title=%s, company_name=%s, location=%s, job_type=%s,
                    experience_required=%s, salary=%s, skills_required=%s,
                    description=%s, deadline=%s
                WHERE id=%s
            """, (title, company, location, job_type, experience,
                  salary, skills, description, deadline, job_id))

            mysql.connection.commit()
            cur.close()

            return redirect(url_for("alumni_jobs"))

        cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        job = cur.fetchone()
        cur.close()

        return render_template("alumni_edit_job.html", job=job)

    from flask import request, redirect, url_for
    from datetime import datetime
    from flask import session, redirect, url_for

    @app.route("/alumni-post-job", methods=["GET", "POST"])
    def alumni_post_job():
        if request.method == "POST":
            alumni_id = session["user_id"]  # temporary

            title = request.form.get("title")
            company = request.form.get("company")
            location = request.form.get("location")
            job_type = request.form.get("job_type")
            experience = request.form.get("experience")
            salary = request.form.get("salary")
            skills = request.form.get("skills")
            description = request.form.get("description")
            deadline = request.form.get("deadline")

            cur = mysql.connection.cursor()

            cur.execute("""
                INSERT INTO jobs 
                (alumni_id, title, company_name, location, job_type, experience_required, salary, skills_required, description, deadline)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (alumni_id, title, company, location, job_type, experience, salary, skills, description, deadline))

            mysql.connection.commit()
            cur.close()

            return redirect(url_for("alumni_dashboard"))

        return render_template("alumni_post_job.html")

    @app.route("/alumni-profile", methods=["GET", "POST"])
    def alumni_profile():

        if "user_id" not in session or session.get("role") != "alumni":
            return redirect(url_for("login"))

        user_id = session["user_id"]

        cur = mysql.connection.cursor()

        if request.method == "POST":

            company = request.form.get("company")
            designation = request.form.get("designation")
            industry = request.form.get("industry")
            location = request.form.get("location")
            experience = request.form.get("experience")
            skills = request.form.get("skills")
            bio = request.form.get("bio")

            # Check if profile exists
            cur.execute("SELECT id FROM alumni_profiles WHERE user_id = %s", (user_id,))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE alumni_profiles
                    SET company=%s, designation=%s, industry=%s,
                        location=%s, experience_years=%s,
                        skills=%s, bio=%s
                    WHERE user_id=%s
                """, (company, designation, industry, location,
                      experience, skills, bio, user_id))
            else:
                cur.execute("""
                    INSERT INTO alumni_profiles
                    (user_id, company, designation, industry, location, experience_years, skills, bio)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, company, designation, industry,
                      location, experience, skills, bio))

            mysql.connection.commit()

        # Fetch profile data
        cur.execute("SELECT * FROM alumni_profiles WHERE user_id = %s", (user_id,))
        profile = cur.fetchone()
        cur.close()

        return render_template("alumni_profile.html", profile=profile)

    @app.route("/student-jobs")
    def student_jobs():

        if "user_id" not in session or session.get("role") != "student":
            return redirect(url_for("login"))

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT jobs.*, users.full_name
            FROM jobs
            JOIN users ON jobs.alumni_id = users.id
            ORDER BY created_at DESC
        """)

        jobs = cur.fetchall()
        cur.close()

        return render_template("student_jobs.html", jobs=jobs)

    @app.route("/apply-job/<int:job_id>", methods=["GET"])
    def apply_job(job_id):

        if "user_id" not in session or session.get("role") != "student":
            return redirect(url_for("login"))

        student_id = session["user_id"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT id FROM job_applications
            WHERE job_id=%s AND student_id=%s
        """, (job_id, student_id))

        existing = cur.fetchone()

        if existing:
            flash("You have already applied for this job.", "warning")
        else:
            cur.execute("""
                INSERT INTO job_applications (job_id, student_id)
                VALUES (%s, %s)
            """, (job_id, student_id))

            mysql.connection.commit()

            flash("Application submitted successfully!", "success")

        cur.close()

        return redirect(url_for("student_jobs"))

    @app.route("/alumni-settings")
    def alumni_settings():
        return "<h2>Settings Page</h2>"

    from flask import jsonify

    @app.route("/my-applications")
    def my_applications():

        if "user_id" not in session or session.get("role") != "student":
            return redirect(url_for("login"))

        student_id = session["user_id"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT 
                job_applications.id,
                jobs.title,
                jobs.company_name,
                jobs.location,
                jobs.job_type,
                job_applications.status,
                job_applications.applied_at
            FROM job_applications
            JOIN jobs ON job_applications.job_id = jobs.id
            WHERE job_applications.student_id = %s
            ORDER BY job_applications.applied_at DESC
        """, (student_id,))

        applications = cur.fetchall()
        cur.close()

        return render_template("my_applications.html", applications=applications)

    @app.route("/mentors")
    def mentors():

        if "user_id" not in session or session.get("role") != "student":
            return redirect(url_for("login"))

        student_id = session["user_id"]

        company = request.args.get("company")
        experience = request.args.get("experience")

        cur = mysql.connection.cursor()

        query = """
        SELECT users.id,
               users.full_name,
               alumni_profiles.company,
               alumni_profiles.designation,
               alumni_profiles.experience_years,
               alumni_profiles.location,
               mentor_requests.status
        FROM users
        JOIN alumni_profiles ON users.id = alumni_profiles.user_id
        LEFT JOIN mentor_requests
            ON mentor_requests.mentor_id = users.id
            AND mentor_requests.student_id = %s
        WHERE users.role='alumni'
        """

        params = [student_id]

        if company:
            query += " AND alumni_profiles.company LIKE %s"
            params.append(f"%{company}%")

        if experience:
            query += " AND alumni_profiles.experience_years >= %s"
            params.append(experience)

        cur.execute(query, tuple(params))

        mentors = cur.fetchall()

        cur.close()

        return render_template("mentors.html", mentors=mentors)

    @app.route("/request-mentor/<int:mentor_id>")
    def request_mentor(mentor_id):

        if "user_id" not in session:
            return redirect(url_for("login"))

        student_id = session["user_id"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT status FROM mentor_requests
            WHERE student_id=%s AND mentor_id=%s
        """, (student_id, mentor_id))

        existing = cur.fetchone()

        if existing:

            if existing[0] == "pending":
                flash("Mentorship request already sent.", "warning")

            elif existing[0] == "accepted":
                flash("You are already connected with this mentor.", "success")

            else:
                flash("Request already exists.", "info")

        else:

            cur.execute("""
            INSERT INTO mentor_requests (student_id, mentor_id)
            VALUES (%s,%s)
            """, (student_id, mentor_id))

            mysql.connection.commit()

            flash("Mentor request sent successfully!", "success")

        cur.close()

        return redirect(url_for("mentors"))

    @app.route("/alumni-mentor-requests")
    def alumni_mentor_requests():

        if "user_id" not in session or session.get("role") != "alumni":
            return redirect(url_for("login"))

        mentor_id = session["user_id"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT mentor_requests.id,
                   users.full_name,
                   users.email,
                   mentor_requests.status,
                   mentor_requests.requested_at
            FROM mentor_requests
            JOIN users ON mentor_requests.student_id = users.id
            WHERE mentor_requests.mentor_id = %s
            ORDER BY mentor_requests.requested_at DESC
        """, (mentor_id,))

        requests = cur.fetchall()

        cur.close()

        return render_template("alumni_mentor_requests.html", requests=requests)

    @app.route("/accept-mentor/<int:req_id>")
    def accept_mentor(req_id):

        if "user_id" not in session:
            return redirect(url_for("login"))

        cur = mysql.connection.cursor()

        cur.execute("""
            UPDATE mentor_requests
            SET status='accepted'
            WHERE id=%s
        """, (req_id,))

        mysql.connection.commit()

        cur.close()

        flash("Mentorship request accepted.", "success")

        return redirect(url_for("alumni_mentor_requests"))

    @app.route("/reject-mentor/<int:req_id>")
    def reject_mentor(req_id):

        cur = mysql.connection.cursor()

        cur.execute("""
            UPDATE mentor_requests
            SET status='rejected'
            WHERE id=%s
        """, (req_id,))

        mysql.connection.commit()

        cur.close()

        flash("Mentorship request rejected.", "warning")

        return redirect(url_for("alumni_mentor_requests"))


    @app.route("/api/alumni-jobs")
    def api_alumni_jobs():

        if "user_id" not in session or session.get("role") != "alumni":
            return jsonify([])

        alumni_id = session["user_id"]
        search = request.args.get("search")
        job_type = request.args.get("job_type")

        cur = mysql.connection.cursor()

        query = "SELECT * FROM jobs WHERE alumni_id = %s"
        params = [alumni_id]

        if search:
            query += " AND title LIKE %s"
            params.append(f"%{search}%")

        if job_type:
            query += " AND job_type = %s"
            params.append(job_type)

        query += " ORDER BY created_at DESC"

        cur.execute(query, tuple(params))
        jobs = cur.fetchall()
        cur.close()

        job_list = []
        for job in jobs:
            job_list.append({
                "id": job[0],
                "title": job[2],
                "company": job[3],
                "location": job[4],
                "job_type": job[5],
                "experience": job[6],
                "salary": job[7],
                "skills": job[8],
                "deadline": str(job[10])
            })

        return jsonify(job_list)

    return app
