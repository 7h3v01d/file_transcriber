# File Transcriber v1.4 - CORRECTED
# Adds inclusion and exclusion lists for file selection

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import chardet
import fnmatch # New import for robust wildcard matching

class FileTranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transcriber v1.4 by Leon Priest")
        self.root.geometry("800x700") # Increased window height
        self.root.configure(bg="#f0f4f8")
        
        # Style configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=10, font=("Helvetica", 12))
        self.style.configure("TLabel", background="#f0f4f8", font=("Helvetica", 12))
        self.style.configure("TEntry", font=("Helvetica", 12))
        self.style.configure("Treeview", font=("Helvetica", 11))
        self.style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Variables
        self.source_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.max_lines = tk.StringVar(value="1000")
        self.status = tk.StringVar(value="Ready to transcribe files")
        self.selected_files = set()
        
        # Inclusion and Exclusion variables with examples
        self.include_list = tk.StringVar(value="*.py, *.gitignore, *.ini, *.j2, *.json, *.log, *.toml, *.yaml, *.md")
        self.exclude_list = tk.StringVar(value="*env*,__pycache__, *.rar, *.zip, *.whl, *markdown, *.txt, *.pyc")

        # Header
        ttk.Label(
            self.main_frame,
            text="File Transcriber",
            font=("Helvetica", 16, "bold"),
            foreground="#2c3e50"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Source Folder Section
        ttk.Label(self.main_frame, text="Source Folder:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(self.main_frame, textvariable=self.source_folder, width=50).grid(row=2, column=0, padx=5, sticky="ew")
        ttk.Button(self.main_frame, text="Browse", command=self.browse_source).grid(row=2, column=1, padx=5)

        # File Selection Treeview
        ttk.Label(self.main_frame, text="Select Files/Folders:").grid(row=3, column=0, sticky="w", pady=5)
        self.tree = ttk.Treeview(self.main_frame, height=10, selectmode="extended")
        self.tree.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        self.tree["columns"] = ("fullpath",)
        self.tree.column("#0", width=400, minwidth=200)
        self.tree.column("fullpath", width=0, stretch=False)
        self.tree.heading("#0", text="File/Folder")
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        # Scrollbar for Treeview
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=4, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Inclusion List Section
        ttk.Label(self.main_frame, text="Include (e.g., *.py,*.txt):").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(self.main_frame, textvariable=self.include_list, width=50).grid(row=6, column=0, padx=5, sticky="ew")
        
        # Exclusion List Section
        ttk.Label(self.main_frame, text="Exclude (e.g., *env*,__pycache__):").grid(row=7, column=0, sticky="w", pady=5)
        ttk.Entry(self.main_frame, textvariable=self.exclude_list, width=50).grid(row=8, column=0, padx=5, sticky="ew")

        # Output File Section
        ttk.Label(self.main_frame, text="Output Text File:").grid(row=9, column=0, sticky="w", pady=5)
        ttk.Entry(self.main_frame, textvariable=self.output_file, width=50).grid(row=10, column=0, padx=5, sticky="ew")
        ttk.Button(self.main_frame, text="Browse", command=self.browse_output).grid(row=10, column=1, padx=5)

        # Max Lines Section
        ttk.Label(self.main_frame, text="Max Lines per File:").grid(row=11, column=0, sticky="w", pady=5)
        ttk.Entry(self.main_frame, textvariable=self.max_lines, width=10).grid(row=12, column=0, padx=5, sticky="w")
        ttk.Label(self.main_frame, text="(Suggested line limit per output file)", font=("Helvetica", 10, "italic")).grid(row=12, column=0, sticky="w", padx=(120, 0))

        # Buttons Frame
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.grid(row=13, column=0, columnspan=2, pady=20)

        # Transcribe Button
        ttk.Button(
            buttons_frame,
            text="Transcribe Selected Files",
            command=self.transcribe_files,
            style="Accent.TButton"
        ).grid(row=0, column=0, padx=5)

        # Status Label
        ttk.Label(
            self.main_frame,
            textvariable=self.status,
            foreground="#34495e",
            font=("Helvetica", 10, "italic")
        ).grid(row=14, column=0, columnspan=2, pady=10)

        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(4, weight=1)

        # Custom button style for accent
        self.style.configure("Accent.TButton", background="#3498db", foreground="#ffffff")
        self.style.map("Accent.TButton",
            background=[("active", "#2980b9")],
            foreground=[("active", "#ffffff")]
        )

    def browse_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_folder.set(folder)
            self.status.set("Source folder selected")
            self.populate_tree(folder)

    def populate_tree(self, folder):
        self.tree.delete(*self.tree.get_children())
        self.selected_files.clear()
        parent = self.tree.insert("", "end", text=os.path.basename(folder), values=(folder,), open=True)
        self._populate_tree_recursive(folder, parent)

    def _populate_tree_recursive(self, folder, parent):
        try:
            for item in sorted(os.listdir(folder)):
                full_path = os.path.join(folder, item)
                if os.path.isdir(full_path):
                    node = self.tree.insert(parent, "end", text=item, values=(full_path,), open=False)
                    self._populate_tree_recursive(full_path, node)
                else:
                    self.tree.insert(parent, "end", text=item, values=(full_path,))
        except Exception as e:
            self.status.set(f"Error reading folder: {str(e)}")

    def on_tree_select(self, event):
        self.selected_files.clear()
        selected_items = self.tree.selection()
        for item in selected_items:
            full_path = self.tree.item(item, "values")[0]
            if os.path.isdir(full_path):
                # If a folder is selected, add all files within it recursively
                self._collect_files_recursive(full_path)
            else:
                # Apply filtering for single file selection
                if self._should_include_file(full_path):
                    self.selected_files.add(full_path)

    # Helper method to check if a file should be included
    def _should_include_file(self, file_path):
        include_patterns = [p.strip() for p in self.include_list.get().split(',') if p.strip()]
        exclude_patterns = [p.strip() for p in self.exclude_list.get().split(',') if p.strip()]
        
        file_name = os.path.basename(file_path)
        
        # Check exclusion first
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return False
        
        # Check inclusion
        # If no inclusion patterns are specified, all files are potentially included
        if not include_patterns:
            return True
            
        for pattern in include_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        
        return False

    def _collect_files_recursive(self, folder):
        try:
            # Check if the folder itself should be excluded
            if self._should_exclude_folder(folder):
                return
            
            for item in os.listdir(folder):
                full_path = os.path.join(folder, item)
                if os.path.isdir(full_path):
                    self._collect_files_recursive(full_path)
                else:
                    # Check if the file should be included based on the lists
                    if self._should_include_file(full_path):
                        self.selected_files.add(full_path)
        except Exception as e:
            self.status.set(f"Error collecting files: {str(e)}")

    # Helper method to check if a folder should be excluded
    def _should_exclude_folder(self, folder_path):
        exclude_patterns = [p.strip() for p in self.exclude_list.get().split(',') if p.strip()]
        folder_name = os.path.basename(folder_path)
        
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(folder_name, pattern):
                return True
        return False


    def browse_output(self):
        file = filedialog.asksaveasfilename(
            title="Select Output Text File",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if file:
            self.output_file.set(file)
            self.status.set("Output file selected")

    def detect_encoding(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(20000) # Read a chunk for detection
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except:
            return 'utf-8'

    def read_file_content(self, file_path):
        try:
            encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='ignore') as file:
                return file.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def get_output_filename(self, base_path, index):
        if index == 0:
            return base_path
        base, ext = os.path.splitext(base_path)
        return f"{base}({index}){ext}"

    def _generate_file_map_string(self):
        """
        Generates the file map string for selected files.
        """
        root_dir = self.source_folder.get()
        if not root_dir:
            return "Error: No source folder selected.\n"

        # Create a set of all paths that need to be visible in the tree
        all_visible_paths = set(self.selected_files)
        for path in self.selected_files:
            parent = os.path.dirname(path)
            while len(parent) >= len(root_dir) and parent != root_dir:
                all_visible_paths.add(parent)
                parent = os.path.dirname(parent)
        
        tree_lines = [f"File Map for: {os.path.basename(root_dir)}", "=" * 20, ""]
        
        # Start the recursive build
        self._build_map_recursive(tree_lines, root_dir, all_visible_paths, "")
        
        return "\n".join(tree_lines)

    def _build_map_recursive(self, tree_lines, current_path, all_visible_paths, prefix):
        """
        Recursively builds the tree structure string.
        """
        try:
            # Get only visible children (folders and files)
            children = [
                child for child in os.listdir(current_path)
                if os.path.join(current_path, child) in all_visible_paths or os.path.isdir(os.path.join(current_path, child))
            ]
            
            # Filter and sort children
            children_to_display = sorted([
                child for child in children if os.path.join(current_path, child) in all_visible_paths
            ])

        except OSError:
            return

        for i, child_name in enumerate(children_to_display):
            is_last = (i == len(children_to_display) - 1)
            connector = "└── " if is_last else "├── "
            child_path = os.path.join(current_path, child_name)
            
            tree_lines.append(f"{prefix}{connector}{child_name}")
            
            if os.path.isdir(child_path):
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._build_map_recursive(tree_lines, child_path, all_visible_paths, new_prefix)

    def transcribe_files(self):
        output_file = self.output_file.get()
        try:
            max_lines = int(self.max_lines.get())
            if max_lines <= 0:
                raise ValueError("Max lines must be a positive number")
        except ValueError:
            self.status.set("Error: Invalid max lines value")
            messagebox.showerror("Error", "Please enter a valid positive number for max lines.")
            return

        # Re-evaluate selected files with the current filters before transcription
        self.selected_files.clear()
        selected_items = self.tree.selection()
        if not selected_items:
            self.status.set("Error: No folder/files selected.")
            messagebox.showerror("Error", "Please select a folder or files from the tree view.")
            return

        for item in selected_items:
            full_path = self.tree.item(item, "values")[0]
            if os.path.isdir(full_path):
                self._collect_files_recursive(full_path)
            else:
                if self._should_include_file(full_path):
                    self.selected_files.add(full_path)

        if not self.selected_files:
            self.status.set("Error: No files selected or all files filtered out.")
            messagebox.showerror("Error", "No files were selected or they were all filtered out by the inclusion/exclusion lists. Please check your patterns.")
            return

        if not output_file:
            self.status.set("Error: Select output file")
            messagebox.showerror("Error", "Please select an output file.")
            return

        self.status.set("Transcribing files...")
        self.root.update()

        try:
            current_lines = 0
            file_index = 0
            outfile = open(self.get_output_filename(output_file, file_index), 'w', encoding='utf-8')
            
            # 1. Generate and write the file map first
            file_map_content = self._generate_file_map_string()
            outfile.write(file_map_content)
            outfile.write("\n\n" + "="*20 + "\n\n")
            current_lines += file_map_content.count('\n') + 4

            # 2. Transcribe the contents of each file
            for file_path in sorted(list(self.selected_files)):
                relative_path = os.path.relpath(file_path, self.source_folder.get())
                content = self.read_file_content(file_path)
                
                header = f"--- Start of: {relative_path} ---\n\n"
                footer = f"\n--- End of: {relative_path} ---\n\n"
                
                entry_content = header + content + footer
                entry_lines = entry_content.count('\n')

                if current_lines > 0 and current_lines + entry_lines > max_lines:
                    outfile.close()
                    file_index += 1
                    outfile = open(self.get_output_filename(output_file, file_index), 'w', encoding='utf-8')
                    current_lines = 0

                outfile.write(entry_content)
                current_lines += entry_lines

            outfile.close()
            self.status.set(f"Files transcribed successfully into {file_index + 1} file(s)!")
            messagebox.showinfo("Success", f"Files have been transcribed successfully into {file_index + 1} file(s)!")
        except Exception as e:
            self.status.set(f"Error during transcription: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            if 'outfile' in locals() and not outfile.closed:
                outfile.close()


def main():
    root = tk.Tk()
    app = FileTranscriberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()