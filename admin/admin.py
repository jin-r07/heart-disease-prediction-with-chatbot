import base64
import csv
import json
import os
import hashlib
import mysql.connector
import numpy as np
import datetime

from functools import wraps
from flask import Flask, render_template, request, redirect, session, render_template_string, send_file
from src.admin.prediction_visualization import get_prediction_distribution_chart
from src.user.user import X_test_prediction, accuracy

app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
app.config['IMAGE_FOLDER'] = "C:/MyFolder/College/BCA 6th Sem/Project-II/ChatBot/src/admin/static/assets"
user_profile_dir = "C:/MyFolder/College/BCA 6th Sem/Project-II/ChatBot/src/admin/uploads/profile"
uploaded_files_dir = "C:/MyFolder/College/BCA 6th Sem/Project-II/ChatBot/src/admin/dataset"

con = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',
    database='hdp_db'
)

cursor = con.cursor()


def admin_login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            return admin_page_not_found(404)
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        name = request.form.get("admin_name")
        email = request.form.get("admin_email")
        password = request.form.get("admin_password")

        md5_password = hashlib.md5(password.encode()).hexdigest()

        query = "SELECT * FROM admin WHERE BINARY Name = %s AND Email = %s AND Password = %s"
        values = (name, email, md5_password)
        cursor.execute(query, values)

        admin = cursor.fetchone()

        if admin:
            session["admin_id"] = admin[0]
            session["admin_name"] = admin[1]
            return redirect("/dashboard")
        else:
            alert_message = "Incorrect name, email or password. Please try again."
            return render_template("login.html", alert_message=alert_message)
    else:
        return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
@admin_login_required
def dashboard():
    global selected_option2, selected_option
    admin_logged_in = "admin_id" in session
    if admin_logged_in:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM datasets")
        ds = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM feedbacks")
        fd = cursor.fetchone()[0]

        admin_id = session.get("admin_id")
        admin_name = session.get("admin_name", "Admin")
        profile_picture = get_profile_picture(admin_id)

        cursor.execute("SELECT * FROM users")
        user_details = cursor.fetchall()

        cursor.execute("SELECT ProfilePic FROM users")
        user_profile = cursor.fetchall()
        image_urls = ["/images/" + image_path[0].replace("\\", "/").split("/")[-1] for image_path in user_profile]

        combined_data = [{'image_url': img_url, 'user_detail': usr_detail} for img_url, usr_detail in
                         zip(image_urls, user_details)]

        cursor.execute("SELECT * FROM datasets")
        ds_details = cursor.fetchall()

        cursor.execute("SELECT * FROM feedbacks")
        feedbacks = cursor.fetchall()

        cursor.execute("SELECT * FROM prediction_history")
        prediction_history = cursor.fetchall()

        prediction_distribution = {
            "No Heart Disease": len(np.where(X_test_prediction == 0)[0]),
            "Heart Disease": len(np.where(X_test_prediction == 1)[0])
        }

        prediction_chart = get_prediction_distribution_chart(prediction_distribution)

        cursor.execute("SELECT FileName FROM datasets WHERE FileType = 'csv'")
        disease_dataset = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT FileName FROM datasets WHERE FileType = 'json'")
        conversation_dataset = [row[0] for row in cursor.fetchall()]

        option_csv = disease_dataset[0]
        option_json = conversation_dataset[0]

        file_path = os.path.join(uploaded_files_dir, option_csv)
        with open(file_path, 'r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.reader(csv_file)
            csv_data = list(csv_reader)
            selected_option = option_csv

        file_path = os.path.join(uploaded_files_dir, option_json)
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
            selected_option1 = option_json

        return render_template("index.html", adminName=admin_name, adminImage=profile_picture, total_users=total_users,
                               ds=ds, fd=fd, accuracy=round(accuracy, 2), ds_details=ds_details,
                               chart=prediction_chart, feedbacks=feedbacks, history=prediction_history,
                               profile=combined_data, disease_dataset=disease_dataset,
                               conversation_dataset=conversation_dataset,
                               csv_data=csv_data, json_data=json_data,
                               selected_option=selected_option, selected_option1=selected_option1)
    else:
        render_template("404.html")


def get_profile_picture(admin_id):
    if admin_id:
        query = "SELECT ProfilePic FROM admin WHERE ID = %s"
        values = (admin_id,)
        cursor.execute(query, values)
        result = cursor.fetchone()
        if result and result[0]:
            profile_picture_filename = result[0]
            profile_picture_path = os.path.join(app.config["IMAGE_FOLDER"], profile_picture_filename)
            if os.path.exists(profile_picture_path):
                with open(profile_picture_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded_image}"
    return "/static/assets/default.png"


@app.route("/add_dataset", methods=["GET", "POST"])
@admin_login_required
def addDataset():
    admin_logged_in = "admin_id" in session
    if admin_logged_in:
        if request.method == "POST":
            file = request.files["datasetFile"]
            if file:
                filename = file.filename
                file_extension = filename.split(".")[-1].lower()

                cursor.execute("SELECT COUNT(*) FROM datasets WHERE FileName = %s", (filename,))
                if cursor.fetchone()[0] > 0:
                    alert_message = "This filename already exists"
                    return f"<script>alert('{alert_message}'); window.location.href='/dashboard';</script>"

                if file_extension in ["json", "csv"]:
                    upload_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    admin_id = session.get("admin_id")

                    insert = "INSERT INTO datasets (FileName, FileType, UploadDate, AdminId) VALUES (%s, %s, %s, %s)"
                    insert_data = (filename, file_extension, upload_date, admin_id)
                    cursor.execute(insert, insert_data)
                    con.commit()

                    saved_file_path = os.path.join(uploaded_files_dir, filename)
                    file.save(saved_file_path)

                    alert_message2 = "Dataset Added Successfully"
                    return f"<script>alert('{alert_message2}'); window.location.href='/dashboard';</script>"
            else:
                return render_template("404.html")
        else:
            return render_template("404.html")
    else:
        return render_template("404.html")


@app.route('/images/<path:filename>')
@admin_login_required
def serve_image(filename):
    image_path = os.path.join(user_profile_dir, filename)
    return send_file(image_path, mimetype='image/jpeg')


@app.route('/delete/<int:user_id>', methods=['POST'])
@admin_login_required
def status_user(user_id):
    if user_id:
        select_query = "SELECT Status FROM users WHERE id = %s"
        cursor.execute(select_query, (user_id,))
        current_status = cursor.fetchone()[0]

        new_status = 1 if current_status == 0 else 0
        admin_id = session.get("admin_id")

        update_query = "UPDATE users SET Status = %s, AdminId = %s WHERE id = %s"
        cursor.execute(update_query, (new_status, admin_id, user_id))
        con.commit()

        alert_message = "User status changed"
        return f"<script>alert('{alert_message}'); window.location.href='/dashboard';</script>"
    else:
        alert_message = "User not found"
        return render_template_string("""
        <script>
            var result = confirm('{{ alert_message }}');
            if (result) {
                window.location.href = "/dashboard";
            } else {
                window.location.href = "/dashboard";
            }
        </script>
        """, alert_message=alert_message)


@app.route('/update_json', methods=['POST'])
def update_json():
    tag = request.form.get('tag')
    patterns = request.form.get('patterns').split(', ')
    responses = request.form.get('responses').split(', ')

    if not tag or not patterns or not responses or '' in patterns or '' in responses:
        alert_message = "Please fill out all form fields."
    else:
        data['intents'].append({
            'tag': tag,
            'patterns': patterns,
            'responses': responses
        })

        with open('dataset/conversation.json', 'w') as json_file:
            json.dump(data, json_file, indent=4)

        alert_message = "Conversation Dataset Updated Successfully"
    return f"<script>alert('{alert_message}'); window.location.href='/dashboard';</script>"


@app.route('/delete_dataset/<int:ds_id>', methods=['POST'])
@admin_login_required
def dataset_delete(ds_id):
    if ds_id:
        cursor.execute("DELETE FROM datasets WHERE id = %s", (ds_id,))
        con.commit()

        alert_message = "Dataset Deleted Successfully"
        return f"<script>alert('{alert_message}'); window.location.href='/dashboard';</script>"
    else:
        alert_message = "Dataset not found"
        return render_template_string("""
        <script>
            var result = confirm('{{ alert_message }}');
            if (result) {
                window.location.href = "/dashboard";
            } else {
                window.location.href = "/dashboard";
            }
        </script>
        """, alert_message=alert_message)


@app.route('/delete_feedback/<int:feedback_id>', methods=['POST'])
@admin_login_required
def feedback_delete(feedback_id):
    if feedback_id:
        cursor.execute("DELETE FROM feedbacks WHERE id = %s", (feedback_id,))
        con.commit()

        alert_message = "Feedback Deleted Successfully"
        return f"<script>alert('{alert_message}'); window.location.href='/dashboard';</script>"
    else:
        alert_message = "Feedback not found"
        return render_template_string("""
        <script>
            var result = confirm('{{ alert_message }}');
            if (result) {
                window.location.href = "/dashboard";
            } else {
                window.location.href = "/dashboard";
            }
        </script>
        """, alert_message=alert_message)


@app.route("/admin_logout")
@admin_login_required
def admin_logout():
    alert_message = "Do you want to logout?"
    return render_template_string("""
    <script>
        var result = confirm('{{ alert_message }}');
        if (result) {
            window.location.href = "/confirm_logout";
        } else {
            window.location.href = "/dashboard";
        }
    </script>
    """, alert_message=alert_message)


@app.route("/confirm_logout")
@admin_login_required
def admin_logout_confirm():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    return redirect("/")


@app.errorhandler(404)
def admin_page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(port=5001, debug=True)
