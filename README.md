# Health Journal

Track gym sessions, compare recent workouts, plan exercises and review food intake alongside estimated calorie burn.

## Run locally

Use Windows with Python 3. In a fresh checkout, run the following PowerShell commands from the project folder. The first command creates an empty journal only if one does not already exist.

```powershell
if (!(Test-Path -LiteralPath workouts.json)) { Copy-Item -LiteralPath journal.example.json -Destination workouts.json }
python server.py
```

Open [the local journal](http://127.0.0.1:8766/). On Windows, double-click `OPEN_TRACKER.pyw` to open the journal with its background checker. To run the checker without opening a browser, use `pythonw.exe OPEN_TRACKER.pyw --background`. It checks the local server every ten seconds and restarts its own server if it exits or fails three checks in a row. Restart events appear in `server.log`.

## Journal data

The local server reads `workouts.json`. The journal's **Export journal** link downloads a copy of those records, including saved dishes and their photos. Workout Builder plans are stored in the browser where they were created. The chat recording helper and server keep backups of journal updates in `backups/`.

The [hosted journal](https://mathealth.netlify.app/) serves the published data and menu photos from the production branch. The local server and its background checker run on Windows.
