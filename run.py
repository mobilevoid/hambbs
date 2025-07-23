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
    sys.exit(
        f"Missing required packages: {missing_list}. "
        "Run `pip install -r requirements.txt` to install them."
    )

from openbbs import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
