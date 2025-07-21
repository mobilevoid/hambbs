# Hambbs User Guide

This guide provides an overview of running the server, using the web interface and the command line tools.

## Starting the Server

1. Install the dependencies listed in `requirements.txt`.
2. Run `python run.py` to start the Flask development server.
3. Navigate to `http://localhost:5000` in your browser.

On first launch you can sign up for a new account. Forums and posts are stored in a local SQLite database `openbbs.db`.

## Command Line Interface

The `bbs.py` tool offers several commands:

- `new` – create a new thread.
- `list` – list existing threads.
- `read THREAD_ID` – print messages in a thread.
- `post THREAD_ID MESSAGE` – add a message.
- `sync pull` and `sync push` – exchange data packages for offline synchronization.
- `queue post` and `outbox view` – queue messages for later push.
- `radio send` and `radio recv` – transmit data over a serial or VaraHF interface (optionally using the KISS protocol).

Run `python bbs.py --help` for all options.

## Offline Mode

The application exposes a lightweight REST API. The file `offline.html` in `openbbs/templates` demonstrates a minimal offline-capable UI that consumes this API. It can be saved and used in environments without the main web interface.

## Synchronization Packages

`SyncEngine` (exposed via `sync.py` and `/api/sync`) exports threads and messages into a compressed tarball. Use `bbs.py sync pull` to create a package or `bbs.py sync push <package>` to import one on another instance. All operations are recorded in `sync_log` for auditing.

## Radio Support

`radio.py` provides a simple COM port interface and a `VaraHFClient` for TCP connections to a VaraHF modem. When combined with the `KISSTnc` wrapper you can send and receive KISS encoded packets.

Example:

```bash
python bbs.py radio send COM3 "hello" --mode com --kiss
```

This sends a KISS framed packet on serial port `COM3`.

## Further Reading

See the project `README.md` for a feature summary and quick setup instructions.
