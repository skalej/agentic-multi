import datetime, json

def log(title: str, data=None):
    """Simple colored console logger for agents."""
    time = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n[{time}] {title}")
    if data is not None:
        try:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print(data)
