import hashlib
import os
import tkinter as tk
from time import sleep
from tkinter import filedialog
import threading


class DriveManagerGUI:
    def __init__(self, drive_api):
        self.drive_api = drive_api
        self.root = tk.Tk()
        self.current_folder_id = None
        self.file_check_vars = []

        self.root.title("Google Drive Manager")
        self.root.attributes('-fullscreen', True)  # Make the window fullscreen

        # Listbox to display folders (with scrollbar)
        self.folder_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE)
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.folder_listbox.bind('<<ListboxSelect>>', self.on_folder_select)
        self.update_folder_listbox(None)

        # Canvas to display files (with scrollbar)
        self.file_canvas = tk.Canvas(self.root)
        self.file_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.scrollbar1 = tk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.folder_listbox.yview)
        self.scrollbar2 = tk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.file_canvas.yview)
        self.scrollbar1.pack(side=tk.LEFT, fill=tk.Y)
        self.scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.config(yscrollcommand=self.scrollbar1.set)
        self.file_canvas.config(yscrollcommand=self.scrollbar2.set)

        # Create a "Upload" button
        self.upload_button = tk.Button(self.root, text="Upload", command=self.upload_file_to_drive)
        self.upload_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        # Create a "Download Selected" button
        download_button = tk.Button(self.root, text="Download Selected", command=self.download_selected_files)
        download_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        # Create a "Back" button
        back_button = tk.Button(self.root, text="Back", command=self.go_back)
        back_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        # List root folders in the initial folder Listbox
        self.update_folder_listbox(None)

        self.download_folder = os.getcwd()  # Default download folder is the current working directory

        # Create a "Change Download Folder" button
        change_download_folder_button = tk.Button(self.root, text="Change Download Folder",
                                                  command=self.change_download_folder)
        change_download_folder_button.pack(side=tk.BOTTOM, padx=10, pady=10)

        # Dictionary to store file metadata
        self.downloaded_files = {}  # Format: {local_path: {'file_id': str, 'last_mod_time': float, 'md5_checksum': str, 'parent_folder_id': 'str'}}

        # Start the periodic check for file changes in a separate thread
        self.file_check_thread = threading.Thread(target=self.check_for_file_changes)
        self.file_check_thread.daemon = True  # Daemonize thread to close it when the main program closes
        self.file_check_thread.start()

        self.root.mainloop()

    def update_folder_listbox(self, folder_id=None):
        self.folder_listbox.delete(0, tk.END)  # Clear the Listbox
        if folder_id is None:
            root_folders = self.drive_api.list_all_folders()
            for folder in root_folders:
                self.folder_listbox.insert(tk.END, folder['name'])
        else:
            folders = self.drive_api.list_all_folders(folder_id)
            for folder in folders:
                self.folder_listbox.insert(tk.END, folder['name'])

    def update_file_canvas(self, folder_id):
        for widget in self.file_canvas.winfo_children():
            widget.destroy()  # Clear the Canvas

        files = self.drive_api.list_files_in_folder(folder_id)
        y_position = 10  # Initial Y position for the files

        for file in files:
            # Add a Checkbutton for each file
            var = tk.IntVar()  # Use IntVar to manage the state
            checkbutton = tk.Checkbutton(self.file_canvas, text=file['name'], variable=var)
            self.file_check_vars.append(var)  # Store the IntVar
            self.file_canvas.create_window(10, y_position, window=checkbutton, anchor='w')
            checkbutton.file_id = file['id']
            checkbutton.file_name = file['name']
            y_position += 30  # Adjust Y position for the next file

    def on_folder_select(self, event):
        selected_folder = self.folder_listbox.get(self.folder_listbox.curselection())
        selected_folder_id = [folder['id'] for folder in self.drive_api.list_all_folders(self.current_folder_id) if
                              folder['name'] == selected_folder]
        if selected_folder_id:
            self.current_folder_id = selected_folder_id[0]
            self.update_folder_listbox(self.current_folder_id)
            self.update_file_canvas(self.current_folder_id)

    def upload_file_to_drive(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            result = self.drive_api.upload_file(file_path, self.current_folder_id)
            if result:
                print(f"Uploaded: {os.path.basename(file_path)}")
                # Refresh the file list
                self.update_file_canvas(self.current_folder_id)
            else:
                print(f"Failed to upload: {os.path.basename(file_path)}")

    def download_selected_files(self):
        selected_files = [i for i, var in enumerate(self.file_check_vars) if var.get()]
        if selected_files:
            # Create a new thread for downloading selected files
            download_thread = threading.Thread(target=self.download_files, args=(selected_files,))
            download_thread.start()

    def change_download_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder = folder_selected
            print("Download folder changed to:", self.download_folder)

    def download_files(self, selected_files):
        for index in selected_files:
            checkbutton = self.file_canvas.winfo_children()[index]
            file_id = checkbutton.file_id
            file_name = checkbutton.file_name
            local_path = os.path.join(self.download_folder, file_name)
            result = self.drive_api.download_file(file_id, local_path)
            if result:
                print(f"Downloaded: {file_name}")
                self.downloaded_files[local_path] = {
                    'file_id': file_id,
                    'last_mod_time': os.path.getmtime(local_path),
                    'md5_checksum': self.calculate_md5(local_path),
                    'parent_folder_id': self.current_folder_id,
                }
            else:
                print(f"Failed to download: {file_name}")

    def check_for_file_changes(self):
        while True:
            for local_path, metadata in list(self.downloaded_files.items()):
                if os.path.exists(local_path):
                    current_mod_time = os.path.getmtime(local_path)
                    if current_mod_time > metadata['last_mod_time']:
                        current_md5 = self.calculate_md5(local_path)
                        if current_md5 != metadata['md5_checksum']:
                            print(f"File changed, uploading: {os.path.basename(local_path)}")
                            result = self.drive_api.upload_file(local_path, metadata['parent_folder_id'])
                            if result:
                                print(f"Uploaded: {os.path.basename(local_path)}")
                                self.downloaded_files[local_path]['last_mod_time'] = current_mod_time
                                self.downloaded_files[local_path]['md5_checksum'] = current_md5
                            else:
                                print(f"Failed to upload: {os.path.basename(local_path)}")
            sleep(10)  # Check every 10 seconds

    @staticmethod
    def calculate_md5(file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def go_back(self):
        if self.current_folder_id:
            parent_folder_id = self.drive_api.get_parent_folder_id(self.current_folder_id)
            if parent_folder_id:
                self.current_folder_id = parent_folder_id
                self.update_folder_listbox(self.current_folder_id)
                self.update_file_canvas(self.current_folder_id)
