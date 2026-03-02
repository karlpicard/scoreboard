# Simple Live Scoreboard

This is a minimal Flask-based application that tracks a single score in a SQLite database. Users can update the score live and viewers see updates in real time via websockets.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py            # defaults to port 6050
```

### Reset Script

To completely wipe the database and restart the server, use the provided `reset.sh` script. It kills any existing server on the chosen port, removes `score.db` and `changes.log`, and launches a fresh instance.

```bash
chmod +x reset.sh
./reset.sh           # uses default port 6050
./reset.sh 5000      # specify a different port
```

Or specify a different port:

```bash
# via environment variable
PORT=5001 python app.py

# or command-line
python app.py --port 5001 --host 127.0.0.1
```
Then open `http://localhost:5000` in a browser. You can add more players or features as needed.
 
Changes are recorded to a JSON-lines logfile at `changes.log` in the project root. Each line is a JSON object like:

```
{"ts":"2026-03-02T12:00:00Z","event":"score_changed","data":{...}}
```

#### Future Enhancements
Future enhancements are tracked under design/TO_DO.md 