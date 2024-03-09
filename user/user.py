import base64
import os
import pandas as pd
import numpy as np
import json
import random
import hashlib
import re
import mysql.connector
import string
import datetime

from functools import wraps
from flask import Flask, render_template, request, redirect, session
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
app.config['UPLOAD_FOLDER'] = 'C:/MyFolder/College/BCA 6th Sem/Project-II/ChatBot/src/admin/uploads/profile'

# Loading csv data to a pandas dataframe
data = pd.read_csv('../admin/dataset/heart_disease_data.csv')
# data.head()
# data.shape
# data.describe()
# data['target'].value_counts()

X = data.drop(columns='target', axis=1)
Y = data['target']
# print(X)
# print(Y)

# Splitting data into training and test data
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.5, stratify=Y, random_state=2)
# print(X.shape, X_train.shape, X_test.shape)

# Logistic regression model
model = LogisticRegression(max_iter=1000)
model.fit(X_train, Y_train)

# Print Intercept (β0)
# intercept = model.intercept_[0]
# print("Intercept (β0):", intercept)

# Extract and print coefficients (β1, β2, ..., β13)
# coefficients = model.coef_[0]
# for i, coef in enumerate(coefficients):
#     print(f"β{i + 1}: {coef}")

X_train_prediction = model.predict(X_train)
training_data_accuracy = accuracy_score(X_train_prediction, Y_train)
accuracy = training_data_accuracy * 100
print('Accuracy on Training data: ', training_data_accuracy * 100)
# Accuracy on Training data: 85.53719008264463

X_test_prediction = model.predict(X_test)
test_data_accuracy = accuracy_score(X_test_prediction, Y_test)
print('Accuracy on Test data: ', test_data_accuracy * 100)
# Accuracy on Test data: 80.32786885245902

conversation = []
with open('../admin/dataset/conversation.json') as f:
    intents = json.load(f)['intents']

con = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',
    database='hdp_db'
)

cursor = con.cursor()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return page_not_found(404)
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/", methods=["GET", "POST"])
def index():
    user_logged_in = "user_id" in session

    if request.method == "POST":
        age = int(request.form.get("age"))
        sex = int(request.form.get("gender"))
        cp = int(request.form.get("cp"))
        bp = int(request.form.get("bp"))
        cholesterol = int(request.form.get("cholesterol"))
        fbs = int(request.form.get("fbs"))
        ecg = int(request.form.get("ecg"))
        hr = int(request.form.get("hr"))
        ea = int(request.form.get("ea"))
        st = float(request.form.get("st"))
        sst = int(request.form.get("sst"))
        ca = int(request.form.get("ca"))
        thallium = int(request.form.get("thallium"))

        input_data = np.array([[age, sex, cp, bp, cholesterol, fbs, ecg, hr, ea, st, sst, ca, thallium]])
        prediction = model.predict(input_data)

        # log_odds = intercept + sum(coef * val for coef, val in zip(coefficients, [age, sex, cp, bp, cholesterol,
        # fbs, ecg, hr, ea, st, sst, ca, thallium])) probability = 1 / (1 + np.exp(-log_odds)) print(f"P(Y=1|X) = {
        # probability:.4f}")

        if user_logged_in:
            user_id = session.get("user_id")

            query = """ INSERT INTO prediction_history (Age, Gender, ChestPainType, BloodPressure, Cholesterol, 
                FastingBloodSugarLevel, EKGResults, MaxHeartRate, ExerciseInducedAngina, STDepression, 
                STSlopeSegment, VesselsDetected, ThalliumStress, Result, PredictDate, UserId)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """

            predict_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prediction_result = int(prediction[0])
            values = (
                age, sex, cp, bp, cholesterol, fbs, ecg, hr, ea, st, sst, ca, thallium, prediction_result, predict_date,
                user_id)

            cursor.execute(query, values)
            con.commit()

        if prediction == 0:
            result = "No Heart Disease"
        elif prediction == 1:
            result = "Heart Disease"
        else:
            result = "Error"

        return render_template("prediction.html", result=result)
    else:
        user_id = session.get("user_id")
        user_name = session.get("user_name", "User")
        profile_picture = get_profile_picture(user_id)
        return render_template("index.html", conversation=conversation, userName=user_name, user_status=user_logged_in,
                               profile_picture=profile_picture)


@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        message = request.form["message"]

        sent_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = "INSERT INTO feedbacks (Username, Email, Message, SentDate) VALUES (%s, %s, %s, %s)"
        values = (username, email, message, sent_date)
        cursor.execute(query, values)
        con.commit()

        alert_message = "Thank you for your feedback!"
        return render_template("feedback.html", alert_message=alert_message)

    return render_template("feedback.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        md5_password = hashlib.md5(password.encode()).hexdigest()

        query = "SELECT * FROM users WHERE BINARY Email = %s AND Password = %s"
        values = (email, md5_password)
        cursor.execute(query, values)
        user = cursor.fetchone()

        if user:
            if user[6] == int(0):
                alert_message = "Your account is currently inactive. Please contact support."
                return render_template("login.html", alert_message=alert_message)

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]

            return redirect("/")
        else:
            alert_message = "Incorrect email or password. Please try again"
            return render_template("login.html", alert_message=alert_message)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        md5_password = hashlib.md5(password.encode()).hexdigest()

        query = "SELECT * FROM users WHERE BINARY Email = %s"
        values = (email,)
        cursor.execute(query, values)
        existing_user = cursor.fetchone()

        if existing_user:
            alert_message = "User with this email account already exists"
            return render_template("register.html", alert_message=alert_message)

        if "profile" in request.files:
            profile_picture = request.files["profile"]
            if profile_picture.filename != "":
                profile_picture_filename = secure_filename(profile_picture.filename)
                profile_picture_path = os.path.join(app.config["UPLOAD_FOLDER"], profile_picture_filename)
                profile_picture.save(profile_picture_path)
            else:
                profile_picture_path = None
        else:
            profile_picture_path = None

        creation_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = ("INSERT INTO users (Name, Email, Password, ProfilePic, CreationDate, Status) VALUES (%s, %s, %s, %s, "
                 "%s, %s)")
        values = (username, email, md5_password, profile_picture_path, creation_date, int(1))
        cursor.execute(query, values)
        con.commit()

        alert_message2 = "Account created successfully"
        return render_template("register.html", alert_message2=alert_message2)
    else:
        return render_template("register.html")


@app.route("/forgotPassword", methods=["GET", "POST"])
def forgotPassword():
    if "email" in session:
        return render_template("resetPassword.html")

    if request.method == "POST":
        email = request.form.get("email")

        query = "SELECT * FROM users WHERE BINARY Email = %s"
        values = (email,)
        cursor.execute(query, values)
        existing_user = cursor.fetchone()

        if existing_user:
            if existing_user[6] == int(0):
                alert_message = "Your account is currently inactive. Please contact support."
                return render_template("forgotPassword.html", alert_message=alert_message)

            session["email"] = email
            return redirect("/resetPassword")
        else:
            alert_message3 = "User not found. Please re-check your email address"
            return render_template("forgotPassword.html", alert_message3=alert_message3)
    session.pop("email", None)
    return render_template("forgotPassword.html")


@app.route("/resetPassword", methods=["GET", "POST"])
def resetPassword():
    if "email" in session:
        email = session["email"]

        if request.method == "POST":
            new_password = request.form.get("password")
            confirm_password = request.form.get("confirmPassword")

            if new_password != confirm_password:
                return render_template("404.html"), 404

            hashed_password = hashlib.md5(new_password.encode()).hexdigest()

            query = "UPDATE users SET Password = %s WHERE BINARY Email = %s"
            values = (hashed_password, email)
            cursor.execute(query, values)

            con.commit()

            alert_message4 = "Password updated successfully"
            session.pop("email", None)
            return render_template("resetPassword.html", alert_message4=alert_message4)
    else:
        alert_message3 = "Invalid request Or, Session expired. Please try again"
        return render_template("forgotPassword.html", alert_message3=alert_message3)
    return render_template("resetPassword.html")


@app.route("/help")
def helpFAQ():
    return render_template("help.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = session.get("user_id")
    user_name = session.get("user_name")
    profile_picture = get_profile_picture(user_id)

    query = "SELECT Email FROM users WHERE ID = %s"
    values = (user_id,)
    cursor.execute(query, values)
    result = cursor.fetchone()
    email = result[0] if result else None

    query2 = "SELECT * FROM prediction_history WHERE UserId = %s"
    cursor.execute(query2, values)
    output = cursor.fetchall()

    if request.method == "POST":
        alert_message3 = None

        if "password" in request.form:
            new_password = request.form.get("password")
            confirm_password = request.form.get("confirmPassword")

            if new_password != confirm_password:
                return render_template("404.html"), 404

            hashed_password = hashlib.md5(new_password.encode()).hexdigest()

            query = "UPDATE users SET Password = %s WHERE BINARY Email = %s"
            values = (hashed_password, email)
            cursor.execute(query, values)
            con.commit()

            alert_message3 = "Password updated successfully"

        if "profile" in request.files:
            profile_picture = request.files["profile"]
            if profile_picture.filename != "":
                profile_picture_filename = secure_filename(profile_picture.filename)
                upload_folder = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
                profile_picture_path = os.path.join(upload_folder, profile_picture_filename)
                profile_picture.save(profile_picture_path)

                query = "UPDATE users SET ProfilePic = %s WHERE BINARY Email = %s"
                values = (profile_picture_path, email)
                cursor.execute(query, values)
                con.commit()

                profile_picture = get_profile_picture(user_id)

                alert_message3 = "Profile updated successfully"

        if "username" in request.form:
            new_username = request.form.get("username")

            query = "UPDATE users SET Name = %s WHERE BINARY Email = %s"
            values = (new_username, email)
            cursor.execute(query, values)
            con.commit()

            session["user_name"] = new_username
            user_name = new_username

            profile_picture = get_profile_picture(user_id)

            alert_message3 = "Profile updated successfully"

        if "email" in request.form:
            new_email = request.form.get("email")

            query = "UPDATE users SET Email = %s WHERE BINARY Email = %s"
            values = (new_email, email)
            cursor.execute(query, values)
            con.commit()

            email = new_email

            profile_picture = get_profile_picture(user_id)

            alert_message3 = "Profile updated successfully"

        if alert_message3:
            return render_template("settings.html", alert_message3=alert_message3, userName=user_name, email=email,
                                   profile_picture=profile_picture, output=output)

    return render_template("settings.html", userName=user_name, email=email, profile_picture=profile_picture,
                           output=output)


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    message = request.form.get("message")
    conversation.append(("user", message))
    response = get_chatbot_response(message)
    conversation.append(("chatbot", response))
    return response


def preprocess_message(message):
    processed_message = re.sub(r'[^\w\s]', '', message)
    return processed_message


def get_chatbot_response(message):
    processed_message = preprocess_message(message.lower())

    for patterns in intents:
        for keyword in patterns["patterns"]:
            if keyword in processed_message:
                response = random.choice(patterns["responses"])
                return response

    return "I'm sorry, I didn't understand that. Can you please rephrase it?"


def get_profile_picture(user_id):
    if user_id:
        query = "SELECT ProfilePic FROM users WHERE ID = %s"
        values = (user_id,)
        cursor.execute(query, values)
        result = cursor.fetchone()
        if result and result[0]:
            profile_picture_filename = result[0]
            profile_picture_path = os.path.join(app.config["UPLOAD_FOLDER"], profile_picture_filename)
            if os.path.exists(profile_picture_path):
                with open(profile_picture_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded_image}"

    return "/static/assets/user.png"


@app.route("/logout_confirm")
@login_required
def logout_confirm():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    conversation.clear()
    alert_message = "Logout Successful!"
    return render_template("index.html", alert_message=alert_message)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
