from flask import Flask, render_template, request, redirect, flash, jsonify
import os
import paramiko
import json
import schedule
import time
import threading
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SFTP_HOST = "upload.rakuten.ne.jp"
SFTP_USERS = ["lucida", "gioi", "glv-p5", "peewee-baby", "glv"]
SFTP_PORT = 22
SFTP_DIR = "/ritem/batch"
UPLOADS_JSON = "uploads.json"
CONFIG_FILE = "config.json"

# Load and save config
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"SFTP_PASS": "Sm7tsA01"}  # Default password

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

config = load_config()
SFTP_PASS = config["SFTP_PASS"]

# Load and save uploads
def load_uploads():
    if os.path.exists(UPLOADS_JSON):
        with open(UPLOADS_JSON, "r") as f:
            return json.load(f)
    return []

def save_uploads(data):
    with open(UPLOADS_JSON, "w") as f:
        json.dump(data, f, indent=4)

# Run scheduler in background
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_scheduler, daemon=True).start()

@app.route("/", methods=["GET", "POST"])
def upload_file():
    global SFTP_PASS

    if request.method == "POST":
        name = request.form.get("name")
        time_to_upload = request.form.get("time")
        selected_user = request.form.get("sftp_user")
        new_password = request.form.get("password")

        if new_password:
            SFTP_PASS = new_password
            config["SFTP_PASS"] = new_password
            save_config(config)  # Save new password

        if not name or not time_to_upload or not selected_user:
            flash("Please enter your name, select an SFTP user, and specify a time!")
            return redirect(request.url)

        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        uploads = load_uploads()

        now = datetime.now()
        upload_time = datetime.strptime(time_to_upload, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        if upload_time < now:
            upload_time += timedelta(days=1)

        uploads.append({
            "name": name,
            "filename": file.filename,
            "time": upload_time.strftime("%Y-%m-%d %H:%M"),
            "status": "pending",
            "sftp_user": selected_user
        })
        save_uploads(uploads)

        schedule.every().day.at(upload_time.strftime("%H:%M")).do(upload_to_sftp, file_path, file.filename, name, selected_user)

        flash(f"File '{file.filename}' scheduled for {upload_time.strftime('%Y-%m-%d %H:%M')} by {name}.")
        return redirect(request.url)

    pending_uploads = load_uploads()
    return render_template("index.html", uploads=pending_uploads, sftp_users=SFTP_USERS)

@app.route("/flush", methods=["POST"])
def flush_uploads():
    admin_pass = request.form.get("admin_password")
    if admin_pass == "admin123":  # Change this to a secure admin password
        save_uploads([])
        flash("Upload list cleared!")
    else:
        flash("Invalid admin password!")
    return redirect("/")

def upload_to_sftp(file_path, filename, name, sftp_user):
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=sftp_user, password=SFTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.chdir(SFTP_DIR)
        sftp.put(file_path, filename)

        sftp.close()
        transport.close()

        uploads = load_uploads()
        for upload in uploads:
            if upload["filename"] == filename and upload["name"] == name:
                upload["status"] = "uploaded"
        save_uploads(uploads)

        print(f"✅ {filename} uploaded successfully.")
        return True
    except Exception as e:
        print(f"❌ SFTP Error: {e}")
        return False

if __name__ == "__main__":
    app.run(debug=True)
