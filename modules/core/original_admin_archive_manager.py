import os
import pandas as pd
from datetime import datetime

ARCHIVE_FOLDER = "admin_archive"
ARCHIVE_METADATA_FILE = "admin_archive_metadata.csv"

# --- Ensure Archive Directory Exists ---
def ensure_archive_folder():
    if not os.path.exists(ARCHIVE_FOLDER):
        os.makedirs(ARCHIVE_FOLDER)

# --- Save Scenario Report ---
def save_scenario_report_to_archive(file_bytes, project_name, department, username="admin"):
    ensure_archive_folder()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_name = project_name.replace(" ", "_").lower()
    filename = f"scenario_{sanitized_name}_{timestamp}.pdf"
    full_path = os.path.join(ARCHIVE_FOLDER, filename)

    # Save PDF bytes
    with open(full_path, "wb") as f:
        f.write(file_bytes)

    # Save metadata
    if os.path.exists(os.path.join(ARCHIVE_FOLDER, ARCHIVE_METADATA_FILE)):
        metadata = pd.read_csv(os.path.join(ARCHIVE_FOLDER, ARCHIVE_METADATA_FILE))
    else:
        metadata = pd.DataFrame(columns=["Filename", "ProjectName", "Department", "CreatedBy", "Timestamp"])

    new_row = {
        "Filename": filename,
        "ProjectName": project_name,
        "Department": department,
        "CreatedBy": username,
        "Timestamp": timestamp
    }
    metadata = pd.concat([metadata, pd.DataFrame([new_row])], ignore_index=True)
    metadata.to_csv(os.path.join(ARCHIVE_FOLDER, ARCHIVE_METADATA_FILE), index=False)

    return filename

# --- Load Archive Metadata ---
def load_archive_metadata():
    ensure_archive_folder()
    path = os.path.join(ARCHIVE_FOLDER, ARCHIVE_METADATA_FILE)
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["Filename", "ProjectName", "Department", "CreatedBy", "Timestamp"])