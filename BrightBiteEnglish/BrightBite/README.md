# BrightBite - English Edition

Browse recipes, save favorites, generate meal plans with budget and dietary constraints, swap dishes, leave feedback and export plans. Ingredient-based notes explain body functions, nutrition and relevant health concerns.

This is an independent application with its own interface, Python server and database. No access code is required.

## Start the app

1. Install Python 3.11 or newer. No extra Python packages are required. On Windows, enable Python on PATH during installation.
2. Extract the entire ZIP file, then open the `BrightBite` folder. Do not run files from inside the ZIP viewer.
3. On Windows, double-click `start_windows.bat`. On macOS/Linux, run `bash start_macos_linux.sh` in this folder.
4. Keep the program window open. Open `http://127.0.0.1:8766` in your browser if it does not open automatically.

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

Run the Python server on one computer. Connect the second device to the same local network and open the computer's IPv4 address shown in the startup window, with port 8766. For example, `http://192.168.1.8:8766` is only an example; use the actual address shown on your computer.

On a phone, `127.0.0.1` refers to the phone itself. All devices must use the same running server to see the same records. Running separate copies of the server creates separate databases.

Anyone who can connect can use shared features. There are no access codes or personal accounts. Using the app across different regions requires a publicly reachable server and HTTPS configuration. This package does not include a deployed online service. The optional `--public-host` setting supports an HTTPS reverse proxy; it does not create a public server by itself.

## Independent storage and backup

This app uses port 8766 by default and saves records in `local_data/community.sqlite3` within this folder. SilverBridge and BrightBite can run simultaneously on their respective ports, and closing one does not stop the other. Stop an older version of the same app before starting this edition, or choose a different port with `python app.py --share --port 8776`.

To back up records, stop this app and copy its `local_data` folder. Keep personal records out of public GitHub repositories. Startup does not depend on the other app's folder.

## Import records from an older edition

Skip this section if you do not need old records. Do not copy an entire combined database into this project.

1. Stop the old app and this app.
2. On Windows, double-click `import_old_data_windows.bat` in this folder.
3. Select the old app's `local_data/community.sqlite3` file.
4. The tool imports only the tables used by BrightBite. It reads the source without modifying it. Start this app after import completes.

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

## Browse and save recipes

Open **Recipe library**. Choose the 112 source recipes or the 29 planning demonstration recipes, search by English recipe or ingredient name, and filter by category. Select **View recipe** for ingredients, preparation and nutrition notes. Use the heart button to save or unsave a recipe; saved recipes appear in **Favorites**.

Source numbers and duplicate titles are retained. Entry No. 113 is a non-food method and is excluded from the app. English recipe names, ingredients and preparation are displayed; the unchanged Chinese source is kept separately in `data/source_archive_zh.json` for reference. Herbal names without a verified identification use pinyin rather than an invented botanical translation. Historical efficacy claims and pediatric dosing are not endorsed as medical advice.

## Generate, change and export a plan

1. Open **Meal plan** and choose 1, 3 or 7 days.
2. Set the daily budget per person, dietary preference, allergen exclusions and available demonstration recipes. Prices remain in CNY and are demonstration estimates.
3. Select **Generate meal plan**. Favorites receive a preference bonus. Each day has breakfast, lunch and dinner with a staple, a protein dish and fruit or vegetables.
4. Switch day tabs to see each day. Use a dish's swap button to choose an eligible replacement. The original budget and exclusions remain enforced.
5. Select **View nutrition notes** under a dish to inspect body-function information and evidence links. A summary below the day's plan follows the actual selected dishes.
6. Leave feedback if desired and select **Export** to download an English text plan with health context.

Automatic planning uses only the 29 demonstration recipes that have prices. The 112 source recipes are available for browsing and favorites, but are not automatically included in budget optimization because reliable price and nutrient data are missing. Allergen filtering uses existing recipe labels; check actual ingredients, seasonings and preparation conditions separately.

## Understand body-function notes

Notes cover eyes, bones and teeth, digestion, muscles and tissue repair, blood and metabolic function when listed ingredients support a rule. They describe general nutrition roles, not measured nutrient intake or a disease-specific diet. Eye nutrition does not reduce myopia prescriptions or replace eye care. Unknown ingredients do not receive invented benefit labels.

See `docs/HEALTH_NOTES.md` for the rules and evidence, and `docs/ALGORITHM.md` for the planning model.
