import subprocess
import sys


def run_updater():
    sys.argv
    if len(sys.argv) == 1:
        print("Running updater!")
        updater_path = r"af_updater.exe"
        # Only works on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        # Launch the process
        process = subprocess.Popen(
            [updater_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startupinfo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        # Detach from the process
        # process.close()
        # Exit python
        sys.exit()
