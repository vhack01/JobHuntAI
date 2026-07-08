from datetime import datetime

_logs = []

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)  # Also output to server console
    _logs.append(line)
    if len(_logs) > 500:
        _logs.pop(0)

def get_logs():
    return _logs

def clear_logs():
    global _logs
    _logs = []
