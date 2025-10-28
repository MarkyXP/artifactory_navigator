import os
import textwrap

import wx

from app.core.config import CONFIG

def check_for_updates():
    # Ignore debugging
    if "DEBUG" in CONFIG.VERSION:
        return
    try:
        # Read the VERSION.txt file
        version_file_location = os.path.join(CONFIG.RELEASE_LOCATION, "VERSION.txt")
        with open(version_file_location, "r") as f:
            released_version = f.read().strip()
        # It is the latest release
        if CONFIG.VERSION == released_version:
            return
        app = wx.App(False)
        response = wx.MessageBox(textwrap.dedent(f"""\
                LBS Artifactory Navigator has been updated to version {released_version}.
                Please consider updating to the latest release.
            """).strip(),
            'Info',
            wx.OK | wx.ICON_WARNING
        )
        os.startfile(CONFIG.RELEASE_LOCATION)
    except Exception as _:
        # Couldn't open the version file - Just let them run.
        return