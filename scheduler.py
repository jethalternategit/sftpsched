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

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"SFTP_PASS": "Sm7tsA01"}

def load_uploads():
    if os.path.exists(UPLOADS_JSON):
        with open(UPLOADS_JSON, "r") as f:
            return json.load(f)
    return []

def save_uploads(data):
    with open(UPLOADS_JSON, "w") as f:
        json.dump(data, f, indent=4)

def upload_to_sftp(file_path, filename, sftp_user, sftp_pass):
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=sftp_user, password=sftp_pass)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir(SFTP_DIR)
        sftp.put(file_path, filename)
        sftp.close()
        transport.close()
        print(f"[✅] {filename} uploaded successfully.")
        return True
    except Exception as e:
        print(f"[❌] Failed to upload {filename}: {e}")
        return False

def check_and_upload():
    uploads = load_uploads()
    config = load_config()
    updated = False

    now = datetime.now()

    for upload in uploads:
        if upload["status"] != "pending":
            continue

        scheduled_time = datetime.strptime(upload["time"], "%Y-%m-%d %H:%M")
        if now >= scheduled_time:
            file_path = os.path.join(UPLOAD_FOLDER, upload["filename"])
            if os.path.exists(file_path):
                print(f"[⏳] Uploading: {upload['filename']}")
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
                print(f"[⚠️] File not found: {file_path}")

    if updated:
        save_uploads(uploads)

if __name__ == "__main__":
    print("✅ Scheduler started. Checking for uploads every 15 seconds...")
    while True:
        check_and_upload()
        time.sleep(15)
