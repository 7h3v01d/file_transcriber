# File Transcriber

**File Transcriber** is a **user-friendly desktop application** built with Python and Tkinter that helps you quickly extract and combine the contents of multiple text-based files from a folder (or selected subfolders) into one or more well-formatted output text files.

Perfect for:
- Preparing codebases for AI analysis (e.g., feeding to ChatGPT, Claude, Gemini, etc.)
- Creating documentation snapshots
- Backing up configuration files
- Collecting logs or scripts for review

## Features

- **Graphical folder selection** with tree view
- **Recursive file selection** (select folders or individual files)
- **Powerful include/exclude filtering** using wildcard patterns (`*.py`, `*env*`, `__pycache__`, etc.)
- **Automatic encoding detection** (using `chardet`)
- **File map / directory tree** visualization at the beginning of output
- **Split output** into multiple files when exceeding a maximum line count
- **Clean formatting** with clear start/end markers for each file
- **Modern, clean UI** with dark-friendly colors
- **Error handling** and user-friendly status messages

## Screenshots

<!-- You can replace these with actual screenshots -->
![Main Window](https://via.placeholder.com/800x600.png?text=File+Transcriber+Main+Window)
*Main application window with folder tree and include/exclude filters*

![Transcribe Result Example](https://via.placeholder.com/800x600.png?text=Example+Output+File)
*Example output file showing file map and file contents*

## Requirements

- **Python** 3.8+
- **Tkinter** (usually comes with Python)
- **chardet** (for encoding detection)

```bash
pip install chardet
```
---
## Installation
### Option 1: Run from source (recommended for developers)
1. Clone the repository:
```Bash
git clone https://github.com/YOUR_USERNAME/file-transcriber.git
cd file-transcriber
```
2. Install dependencies:
```Bash
pip install chardet
```
3. Run the application:
```Bash
python file_transcriber_v1.51.py
```
Option 2: Create a standalone executable (Windows/macOS/Linux)
Using PyInstaller:

```Bash
pip install pyinstaller
pyinstaller --onefile --windowed file_transcriber_v1.51.py
```
The executable will be created in the dist/ folder.

## Usage
1. Launch the application
2. Select source folder using the "Browse" button
3. Browse the file tree and select files or folders you want to include
  - Use Ctrl+Click or Shift+Click for multiple selection
  - Selecting a folder includes all matching files recursively
4. Adjust include/exclude patterns (comma-separated):
  - Include: *.py, *.md, *.json, *.yaml, *.toml
  - Exclude: *env*, __pycache__, *.log, *.pyc, *.zip
5. Choose output file location (.txt)
6. Set maximum lines per output file (default: 1000)
7. Click Transcribe Selected Files

The application will:
- Generate a clean directory tree (file map)
- Append content of each selected file with clear headers/footers
- Split into multiple files if needed (e.g. output.txt, output(1).txt, ...)

### Include / Exclude Patterns
Uses standard Unix-style wildcard matching (via fnmatch):
```text
Pattern	      Matches	                              Example Use Case
*.py	        All Python files	                    Include source code
*.md	        Markdown files	                      Documentation
*env*	        Any file/folder containing "env"	    Exclude virtual environments
__pycache__	  Exact folder name	                    Exclude compiled Python cache
*.pyc	        Compiled Python files	                Exclude bytecode
*.log	        Log files	                            Exclude logs
```
Tip: Leave the Include field empty to include all files that aren't excluded.

### Output Format Example
```text
File Map for: my_project
====================

├── README.md
├── src
│   ├── main.py
│   └── utils
│       └── helpers.py
└── config
    └── settings.yaml

====================

--- Start of: README.md ---

# My Awesome Project
...

--- End of: README.md ---

--- Start of: src/main.py ---

import utils.helpers
...

--- End of: src/main.py ---
```

## Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## Planned Features / Ideas
- Drag & drop folder support
- File preview pane
- Remember last used folder/output
- Export to Markdown code blocks
- Search/filter in tree view
- Progress bar during transcription
- Command-line interface (CLI) version

---
## License
This project is licensed under the MIT License - see the LICENSE file for details.

Author
Leon Priest</br>
Created: ~2023–2024</br>
Updated: 2025
