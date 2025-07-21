# OpenBBS

A simple Bulletin Board System implemented in Python using Flask. It provides user authentication and message posting with basic forum support.

## Features

- User signup and login
- Forums with threads and replies
- File attachments on posts with gzip compression
- SQLite database via SQLAlchemy
- Simple web interface using Bootstrap
- Synchronization API and CLI tools
- Search functionality for posts
- Basic COM/VARAHF radio interface (experimental)

## Setup

1. Create a Python virtual environment (optional but recommended)
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python run.py
```

Then open `http://localhost:5000` in your browser.

## Notes

This project is still a prototype. Radio communication via COM or VaraHF is experimental and only supports simple send/receive operations. File attachments are compressed but not encrypted.
