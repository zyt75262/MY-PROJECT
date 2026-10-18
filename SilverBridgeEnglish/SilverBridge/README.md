# SilverBridge - English Edition

Ask for help with text, screenshots or audio. Volunteers can claim requests, reply, mark a solution and reopen requests. Requests synchronize between connected devices every three seconds. Local stories can also be recorded and shared with consent.

This is an independent application with its own interface, Python server and database. No access code is required.

## Start the app

1. Install Python 3.11 or newer. No extra Python packages are required. On Windows, enable Python on PATH during installation.
2. Extract the entire ZIP file, then open the `SilverBridge` folder. Do not run files from inside the ZIP viewer.
3. On Windows, double-click `start_windows.bat`. On macOS/Linux, run `bash start_macos_linux.sh` in this folder.
4. Keep the program window open. Open `http://127.0.0.1:8765` in your browser if it does not open automatically.

The browser address bar is the field at the top of the browser that displays a website address. Paste the address there and press Enter; do not enter it in a search box inside a webpage.

The startup scripts enable local-network sharing. You can also start from a terminal:

```bash
python app.py --share
```

For access only on the server computer:

```bash
python app.py
```

Stop the server with Ctrl+C in its program window. To copy text from that window without stopping it, select the text and use the right-click Copy command or the terminal's Copy menu. Restart with the same startup script; saved records remain.

## Use another device

Run the Python server on one computer. Connect the second device to the same local network and open the computer's IPv4 address shown in the startup window, with port 8765. For example, `http://192.168.1.8:8765` is only an example; use the actual address shown on your computer.

On a phone, `127.0.0.1` refers to the phone itself. All devices must use the same running server to see the same records. Running separate copies of the server creates separate databases.

Anyone who can connect can use shared features. There are no access codes or personal accounts. Using the app across different regions requires a publicly reachable server and HTTPS configuration. This package does not include a deployed online service. The optional `--public-host` setting supports an HTTPS reverse proxy; it does not create a public server by itself.

## Independent storage and backup

This app uses port 8765 by default and saves records in `local_data/community.sqlite3` within this folder. SilverBridge and BrightBite can run simultaneously on their respective ports, and closing one does not stop the other. Stop an older version of the same app before starting this edition, or choose a different port with `python app.py --share --port 8775`.

To back up records, stop this app and copy its `local_data` folder. Keep personal records out of public GitHub repositories. Startup does not depend on the other app's folder.

## Import records from an older edition

Skip this section if you do not need old records. Do not copy an entire combined database into this project.

1. Stop the old app and this app.
2. On Windows, double-click `import_old_data_windows.bat` in this folder.
3. Select the old app's `local_data/community.sqlite3` file.
4. The tool imports only the tables used by SilverBridge. It reads the source without modifying it. Start this app after import completes.

The target must have no records. If records already exist, import is cancelled without replacing them. To restore both independent apps, import separately in each app. You can also use a terminal:

```bash
python import_old_data.py "/path/to/old-app/local_data/community.sqlite3"
```

User-written requests, replies and stories retain their original language. Recipe IDs and internal category codes are preserved for compatibility; the interface displays English labels.

## Troubleshooting

- **Cannot connect to the Python server:** keep the startup window open and open the exact address shown there. A downloaded HTML file opened directly cannot connect to the correct service.
- **Another device cannot open the page:** start with `--share`, check the computer's IPv4 address, connect to the same network and allow Python through the private-network firewall. Guest Wi-Fi or device isolation may block connections.
- **Port already in use:** stop the previous instance or use a different `--port`; use that port in the browser address too.
- **Python is not found:** install Python 3.11 or newer, enable PATH, then reopen the terminal or startup script.
- **Data seems missing:** confirm that you started the intended folder and that all devices are using the same server address.

## Source files and validation

| File | Purpose |
| --- | --- |
| `app.py` | Startup and port settings |
| `community/server.py` | App-specific API and web server |
| `community/storage.py` | App-specific SQLite storage |
| `web/app.js` | Interface and interactions |
| `import_old_data.py` | Selective import from an older database |
| `tests/` | Automated checks |

Run the Python tests from this folder:

```bash
python -m unittest discover -s tests -v
```

Optional rendering-logic check: `node tests/ui_render.cjs`. Node is only required for this check, not to run the app. See `TEST_REPORT.md` for validation scope and `AUTHORS_AND_AI.md` for development attribution.

## Ask for help and respond

1. On device A, open **Ask for help**. Choose a topic, type a description and optionally attach a screenshot or audio. Select **Submit request**.
2. On device B, open the same server address and choose **Volunteer desk**. Requests appear automatically, normally within about three seconds while the page is active.
3. Select **I can help**, then **Write a reply**. Give clear steps and save the reply.
4. Device A opens **Help board**, reads the reply and selects **Problem solved** if the solution worked. Use **Still need help** to reopen a solved request.

Synchronization pauses during certain editing and audio-playback actions to protect the current interaction. You can also use Refresh. Requests and replies remain after a server restart.

Screenshots support PNG, JPEG and WebP up to 800 KB. Audio is limited to 45 seconds and 1.2 MB. Phone browsers may block microphone recording over local HTTP; use **Upload audio** to choose an existing file instead. There is no remote screen control, emergency alert service or notification after the page is closed or the device is locked.

## Share a local story

Open **Local stories**, then **Share a story**. Enter a title and text, optionally record audio, confirm that you have the storyteller's permission and share. Connected visitors can read or listen to shared stories. Older unshared drafts are not automatically published.
