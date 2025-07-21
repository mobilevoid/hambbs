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
- Basic COM/VaraHF radio interface with optional KISS framing
- REST API for threads/messages and lightweight offline UI
- Local SQLite storage with sync log

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

### CLI usage

The `bbs.py` script provides basic commands:

```bash
python bbs.py list            # list threads
python bbs.py new "Title"     # create thread
python bbs.py post <thread> "message" --author bob
python bbs.py sync pull --since 2023-01-01T00:00:00
python bbs.py sync push package.tar.zst
```

## Notes

This project is still a prototype. Radio communication now supports the VaraHF modem over TCP and includes a basic KISS TNC compatibility layer. File attachments are compressed but not encrypted.
