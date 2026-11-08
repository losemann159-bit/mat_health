# Health Journal

Track gym sessions, compare recent workouts, plan exercises and review food intake alongside estimated calorie burn.

## Run locally

Use Windows with Python 3. In a fresh checkout, run the following PowerShell commands from the project folder. The first command creates an empty journal only if one does not already exist.

```powershell
if (!(Test-Path -LiteralPath workouts.json)) { Copy-Item -LiteralPath journal.example.json -Destination workouts.json }
python server.py
```

Open [the local journal](http://127.0.0.1:8766/). On Windows, double-click `OPEN_TRACKER.pyw` to run the journal in the background.

## Journal data

The local server reads `workouts.json`. The journal's **Export journal** link downloads a copy of those records, including saved dishes and their photos. Workout Builder plans are stored in the browser where they were created. The chat recording helper and server keep backups of journal updates in `backups/`.

The current app uses a local Python server. Hosting the live journal on Netlify requires an authenticated replacement for `/api/workouts` and persistent storage for your records. Keep personal data outside the publish directory.
