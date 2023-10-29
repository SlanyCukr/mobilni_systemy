import os
import tkinter as tk
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

    def download_files(self, selected_files):
        for index in selected_files:
            checkbutton = self.file_canvas.winfo_children()[index]
            file_id = checkbutton.file_id
            file_name = checkbutton.file_name
            result = self.drive_api.download_file(file_id, file_name)
            if result:
                print(f"Downloaded: {file_name}")
            else:
                print(f"Failed to download: {file_name}")

    def go_back(self):
        if self.current_folder_id:
            parent_folder_id = self.drive_api.get_parent_folder_id(self.current_folder_id)
            if parent_folder_id:
                self.current_folder_id = parent_folder_id
                self.update_folder_listbox(self.current_folder_id)
                self.update_file_canvas(self.current_folder_id)
