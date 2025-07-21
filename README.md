# OpenBBS

A simple Bulletin Board System implemented in Python using Flask. It provides user authentication and message posting with basic forum support.

## Features

- User signup and login
- Forums with threads and replies
- File attachments on posts
- SQLite database via SQLAlchemy
- Simple web interface using Bootstrap

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

This project is still a prototype. Advanced features such as COM/VaraHF integration, data synchronization, and encrypted file storage are not implemented.
