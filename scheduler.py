import os
import json
import time
from datetime import datetime
import paramiko

UPLOAD_FOLDER = "uploads"
UPLOADS_JSON = "uploads.json"
CONFIG_FILE = "config.json"
SFTP_HOST = "upload.rakuten.ne.jp"
SFTP_PORT = 22
SFTP_DIR = "/ritem/batch"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    log("⚠️ Config file not found. Using default password.")
    return {"SFTP_PASS": "Sm7tsA01"}

def load_uploads():
    if os.path.exists(UPLOADS_JSON):
        with open(UPLOADS_JSON, "r") as f:
            return json.load(f)
    log("⚠️ uploads.json not found. Nothing to upload.")
    return []

def save_uploads(data):
    with open(UPLOADS_JSON, "w") as f:
        json.dump(data, f, indent=4)

def upload_to_sftp(file_path, filename, sftp_user, sftp_pass):
    try:
        log(f"🔌 Connecting to SFTP: {SFTP_HOST}")
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=sftp_user, password=sftp_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir(SFTP_DIR)
        sftp.put(file_path, filename)
        sftp.close()
        transport.close()
        log(f"✅ {filename} uploaded successfully.")
        return True
    except Exception as e:
        log(f"❌ Failed to upload {filename}: {e}")
        return False

def check_and_upload():
    uploads = load_uploads()
    config = load_config()
    updated = False
    now = datetime.now()

    log("🔍 Checking for scheduled uploads...")

    for upload in uploads:
        if upload["status"] != "pending":
            continue

        try:
            scheduled_time = datetime.strptime(upload["time"], "%Y-%m-%d %H:%M")
        except ValueError:
            log(f"❌ Invalid time format in entry: {upload}")
            continue

        log(f"⏱️ Scheduled: {scheduled_time} | Now: {now} | File: {upload['filename']}")

        if now >= scheduled_time:
            file_path = os.path.join(UPLOAD_FOLDER, upload["filename"])
            if os.path.exists(file_path):
                log(f"🚀 Uploading: {upload['filename']}")
                success = upload_to_sftp(
                    file_path,
                    upload["filename"],
                    upload["sftp_user"],
                    config["SFTP_PASS"]
                )
                if success:
                    upload["status"] = "uploaded"
                    updated = True
            else:
                log(f"⚠️ File not found: {file_path}")
        else:
            log(f"⏳ Waiting for time. Not yet: {upload['filename']}")

    if updated:
        log("💾 Saving upload status updates...")
        save_uploads(uploads)

if __name__ == "__main__":
    log("✅ Scheduler started. Checking for uploads every 15 seconds...")
    while True:
        check_and_upload()
        time.sleep(15)
