from google_drive.drive_manager_gui import DriveManagerGUI
from google_drive.google_drive_api import GoogleDriveAPI

if __name__ == "__main__":
    drive_api = GoogleDriveAPI()
    gui = DriveManagerGUI(drive_api)
