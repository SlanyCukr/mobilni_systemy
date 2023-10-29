import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']


class GoogleDriveAPI:
    def __init__(self):
        self.service = self.authenticate_drive_api()

    def authenticate_drive_api(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return build('drive', 'v3', credentials=creds)

    def list_all_folders(self, folder_id=None):
        try:
            if folder_id is None:
                results = self.service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and 'root' in parents",
                    pageSize=1000,
                    fields="files(id, name)").execute()
            else:
                results = self.service.files().list(
                    q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                    pageSize=1000,
                    fields="files(id, name)").execute()
            items = results.get('files', [])
            return items
        except HttpError as error:
            return [f"An error occurred: {error}"]

    def list_files_in_folder(self, folder_id):
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
                pageSize=1000,
                fields="files(id, name)").execute()
            items = results.get('files', [])
            return items
        except HttpError as error:
            return [f"An error occurred: {error}"]

    def download_file(self, file_id, file_name):
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_stream = request.execute()
            with open(file_name, 'wb') as f:
                f.write(file_stream)
            return True
        except HttpError as error:
            return False

    def upload_file(self, file_path, folder_id):
        try:
            file_metadata = {
                'name': file_path.split('/')[-1],
                'parents': [folder_id]
            }
            media = MediaFileUpload(file_path.split('/')[-1])
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            )
            request.execute()
            return True
        except HttpError as error:
            return False

    def get_parent_folder_id(self, folder_id):
        try:
            folder = self.service.files().get(fileId=folder_id, fields='parents').execute()
            parents = folder.get('parents', [])
            if parents:
                return parents[0]
        except HttpError as error:
            return None
