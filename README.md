# OpenBBS

A simple Bulletin Board System implemented in Python using Flask. It provides user authentication and message posting with basic forum support.

Additional usage information is available in [docs/USAGE.md](docs/USAGE.md).

## Features

- User signup and login
- Forums with threads and replies
- File attachments on posts with encrypted gzip compression
- SQLite database via SQLAlchemy
- Simple web interface using Bootstrap
- Synchronization API and CLI tools
- Search functionality for posts
- Basic COM/VaraHF radio interface with optional KISS framing
- Support for VARA Terminal's KISS serial mode via `VaraKISS`
- REST API for threads/messages and lightweight offline UI
- Local SQLite storage with sync log
- Thread owners can grant moderator status via signed ownership tokens
- Keyboard shortcuts for quick actions and "/" to focus the search box
- Optional dark mode toggle for better readability

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

Radio communication supports the VaraHF modem over TCP and includes a KISS TNC compatibility layer. The `VaraKISS` helper lets you talk to VARA Terminal in its KISS serial mode. File attachments are encrypted and compressed for safe transfer.
