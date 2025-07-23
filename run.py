import sys

MISSING = []
for pkg in [
    "flask",
    "flask_sqlalchemy",
    "flask_login",
    "werkzeug",
    "zstandard",
    "pyserial",
    "reedsolo",
    "crcmod",
    "cryptography",
    "markdown",
]:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        MISSING.append(pkg)

if MISSING:
    missing_list = ", ".join(MISSING)
    print(
        f"Missing required packages detected: {missing_list}.\n"
        "Attempting to install from requirements.txt..."
    )
    try:
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
    except Exception:
        sys.exit(
            "Automatic installation failed. Please run 'pip install -r requirements.txt'"
        )
    # re-check imports after installation
    REMAINING = []
    for pkg in [
        "flask",
        "flask_sqlalchemy",
        "flask_login",
        "werkzeug",
        "zstandard",
        "pyserial",
        "reedsolo",
        "crcmod",
        "cryptography",
        "markdown",
    ]:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            REMAINING.append(pkg)
    if REMAINING:
        remaining_list = ", ".join(REMAINING)
        sys.exit(
            f"Failed to install required packages: {remaining_list}.\n"
            "Please install them manually using 'pip install -r requirements.txt'."
        )

from openbbs import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
