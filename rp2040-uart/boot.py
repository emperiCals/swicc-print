import os
try:
    files = os.listdir()
    if "update_main.py" in files:
        if "main.py" in files:
            os.remove("main.py")
        os.rename("update_main.py", "main.py")
except Exception:
    pass
