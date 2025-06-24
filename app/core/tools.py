import threading
from functools import wraps

def run_in_background(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread  # optionally return the thread if you want to check status
    return wrapper