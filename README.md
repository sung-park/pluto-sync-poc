# Start the Backend Server

Make sure you're in the project root directory.

```
uvicorn server.main:app --reload
```

This will launch:
- a REST API (e.g. `/notify`, `/upload`, `/status`)
- a raw TCP socket server on port `9000`

# Start the Watch Simulator (Qt GUI)

In a separate terminal, run:

```
python scripts/simulate_tcp_watch_qt.py
```
This opens a GUI-based simulator that mimics the behavior of a Watch5 client.

![image](https://github.com/user-attachments/assets/161a75f9-df08-4fd0-8e55-acd0a885fd8c)
