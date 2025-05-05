import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, flash, url_for
from waitress import serve

UPLOAD_FOLDER = "uploads"
UPLOADS_JSON = "uploads.json"
CONFIG_FILE = "config.json"
ADMIN_PASSWORD = "admin123"  # You can change this to something more secure

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_uploads():
    if os.path.exists(UPLOADS_JSON):
        with open(UPLOADS_JSON, "r") as f:
            return json.load(f)
    return []

def save_uploads(data):
    with open(UPLOADS_JSON, "w") as f:
        json.dump(data, f, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"SFTP_PASS": "A"}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def index():
    uploads = load_uploads()

    if request.method == "POST":
        name = request.form["name"]
        time_str = request.form["time"]
        sftp_user = request.form["sftp_user"]
        file = request.files["file"]

        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Construct datetime for today
            now = datetime.now()
            scheduled_time = datetime.strptime(f"{now.date()} {time_str}", "%Y-%m-%d %H:%M")
            if scheduled_time < now:
                scheduled_time += timedelta(days=1)  # Schedule for next day if time passed

            uploads.append({
                "name": name,
                "filename": filename,
                "time": scheduled_time.strftime("%Y-%m-%d %H:%M"),
                "sftp_user": sftp_user,
                "status": "pending"
            })
            save_uploads(uploads)
            flash(f"{filename} scheduled for upload at {scheduled_time.strftime('%Y-%m-%d %H:%M')}")
            return redirect(url_for("index"))

    return render_template("index.html", uploads=uploads)

@app.route("/flush", methods=["POST"])
def flush():
    password = request.form["flush_password"]
    if password == ADMIN_PASSWORD:
        save_uploads([])
        flash("Upload queue flushed.")
    else:
        flash("Incorrect admin password.")
    return redirect(url_for("index"))

@app.route("/update-password", methods=["POST"])
def update_password():
    new_password = request.form["new_password"]
    if new_password:
        config = load_config()
        config["SFTP_PASS"] = new_password
        save_config(config)
        flash("SFTP password updated.")
    else:
        flash("No password provided.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=61591)
