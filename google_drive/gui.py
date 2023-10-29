import os
import threading
from tkinter import Button, Tk
from tkinter import messagebox, filedialog
import tkinter as tk
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']


# Function to authenticate Google Drive API
def authenticate_drive_api():
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


# Function to list all folders from Google Drive
def list_all_folders(service, folder_id=None):
    try:
        if folder_id is None:
            results = service.files().list(
                q="mimeType='application/vnd.google-apps.folder' and 'root' in parents",
                pageSize=1000,
                fields="files(id, name)").execute()
        else:
            results = service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                pageSize=1000,
                fields="files(id, name)").execute()
        items = results.get('files', [])
        return items
    except HttpError as error:
        return [f"An error occurred: {error}"]


# Function to list all files within a folder
def list_files_in_folder(service, folder_id):
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
            pageSize=1000,
            fields="files(id, name)").execute()
        items = results.get('files', [])
        return items
    except HttpError as error:
        return [f"An error occurred: {error}"]


# Function to download a file
def download_file(service, file_id, file_name):
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = request.execute()
        with open(file_name, 'wb') as f:
            f.write(file_stream)
        return True
    except HttpError as error:
        return False


# Function to upload a file to Google Drive
def upload_file(service, file_path, folder_id):
    try:
        file_metadata = {
            'name': file_path.split('/')[-1],
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path)
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        )
        request.execute()
        return True
    except HttpError as error:
        return False


# Create a fullscreen Tkinter GUI
def create_gui():
    root = tk.Tk()
    root.title("Google Drive Manager")
    root.attributes('-fullscreen', True)  # Make the window fullscreen

    # Listbox to display folders (with scrollbar)
    folder_listbox = tk.Listbox(root, selectmode=tk.SINGLE)
    folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Canvas to display files (with scrollbar)
    file_canvas = tk.Canvas(root)
    file_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    scrollbar1 = tk.Scrollbar(root, orient=tk.VERTICAL, command=folder_listbox.yview)
    scrollbar2 = tk.Scrollbar(root, orient=tk.VERTICAL, command=file_canvas.yview)
    scrollbar1.pack(side=tk.LEFT, fill=tk.Y)
    scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
    folder_listbox.config(yscrollcommand=scrollbar1.set)
    file_canvas.config(yscrollcommand=scrollbar2.set)

    # Google Drive API service
    service = authenticate_drive_api()

    # Function to update the folder Listbox
    def update_folder_listbox(folder_id=None):
        folder_listbox.delete(0, tk.END)  # Clear the Listbox
        if folder_id is None:
            root_folders = list_all_folders(service)
            for folder in root_folders:
                folder_listbox.insert(tk.END, folder['name'])
        else:
            folders = list_all_folders(service, folder_id)
            for folder in folders:
                folder_listbox.insert(tk.END, folder['name'])

    # Create IntVar to manage the state of each Checkbutton
    file_check_vars = []

    # Function to update the file Canvas
    def update_file_canvas(folder_id):
        for widget in file_canvas.winfo_children():
            widget.destroy()  # Clear the Canvas

        files = list_files_in_folder(service, folder_id)
        y_position = 10  # Initial Y position for the files

        for file in files:
            # Add a Checkbutton for each file
            var = tk.IntVar()  # Use IntVar to manage the state
            checkbutton = tk.Checkbutton(file_canvas, text=file['name'], variable=var)
            file_check_vars.append(var)  # Store the IntVar
            file_canvas.create_window(10, y_position, window=checkbutton, anchor='w')
            checkbutton.file_id = file['id']
            checkbutton.file_name = file['name']
            y_position += 30  # Adjust Y position for the next file

    # Store the current folder ID
    current_folder_id = None

    # Function to handle folder selection
    def on_folder_select(event):
        nonlocal current_folder_id  # Ensure we modify the variable outside the function
        selected_folder = folder_listbox.get(folder_listbox.curselection())
        selected_folder_id = [folder['id'] for folder in list_all_folders(service, current_folder_id) if folder['name'] == selected_folder]
        if selected_folder_id:
            current_folder_id = selected_folder_id[0]
            update_folder_listbox(current_folder_id)
            update_file_canvas(current_folder_id)

    folder_listbox.bind('<<ListboxSelect>>', on_folder_select)

    # Function to handle file uploads
    def upload_file_to_drive():
        file_path = filedialog.askopenfilename()
        if file_path:
            result = upload_file(service, file_path, current_folder_id)
            if result:
                print(f"Uploaded: {os.path.basename(file_path)}")
                # Refresh the file list
                update_file_canvas(current_folder_id)
            else:
                print(f"Failed to upload: {os.path.basename(file_path)}")

    # Create an "Upload" button
    upload_button = tk.Button(root, text="Upload", command=upload_file_to_drive)
    upload_button.pack(side=tk.BOTTOM, padx=10, pady=10)

    # Function to handle file downloads
    def download_selected_files():
        selected_files = [i for i, var in enumerate(file_check_vars) if var.get()]
        if selected_files:
            # Create a new thread for downloading selected files
            download_thread = threading.Thread(target=download_files, args=(service, selected_files))
            download_thread.start()

    # Function to download files in a separate thread
    def download_files(service, selected_files):
        for index in selected_files:
            checkbutton = file_canvas.winfo_children()[index]
            file_id = checkbutton.file_id
            file_name = checkbutton.file_name
            result = download_file(service, file_id, file_name)
            if result:
                print(f"Downloaded: {file_name}")
            else:
                print(f"Failed to download: {file_name}")

    # Create a "Download Selected" button
    download_button = tk.Button(root, text="Download Selected", command=download_selected_files)
    download_button.pack(side=tk.BOTTOM, padx=10, pady=10)

    # Function to handle going back up one folder level
    def go_back():
        nonlocal current_folder_id
        if current_folder_id:
            parent_folder_id = get_parent_folder_id(current_folder_id)
            if parent_folder_id:
                current_folder_id = parent_folder_id
                update_folder_listbox(current_folder_id)
                update_file_canvas(current_folder_id)

    # Create a "Back" button
    back_button = tk.Button(root, text="Back", command=go_back)
    back_button.pack(side=tk.BOTTOM, padx=10, pady=10)

    # Function to get the parent folder ID
    def get_parent_folder_id(folder_id):
        try:
            folder = service.files().get(fileId=folder_id, fields='parents').execute()
            parents = folder.get('parents', [])
            if parents:
                return parents[0]
        except HttpError as error:
            return None

    # List root folders in the initial folder Listbox
    update_folder_listbox(None)

    root.mainloop()


if __name__ == '__main__':
    authenticate_drive_api()

    create_gui()