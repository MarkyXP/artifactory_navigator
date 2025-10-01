import textwrap

import win32com.client as win32

from app.core.config import CONFIG

def generate_dst_email(recipient_name, recipient_email, download_link):
    # Create an instance of Outlook
    outlook = win32.Dispatch('outlook.application')

    # Create a new email item
    mail = outlook.CreateItem(0)  # 0: olMailItem

    with open(CONFIG.SHIPPING_TOOL_EMAIL_BODY_LOCATION, "r") as f:
        email_body : str = f.read()
    email_body = email_body.replace("$Name", recipient_name)
    email_body = email_body.replace("$ExpiryTime", "$ExpiryTime_TMP")
    email_body = email_body.replace("$FileSHATable", "$FileSHATable_TMP")
    email_body = email_body.replace("$Filename", "$Filename_TMP")
    email_body = email_body.replace("$URL", download_link)

    # Set email properties
    mail.To = recipient_email  # Replace with the recipient's email address
    mail.Subject = f"File download from Leica BioSystems for {'Markerry'}"
    mail.HTMLBody  = email_body
    # mail.CC = None
    # mail._oleobj_.Invoke(*(64209, 0, 8, 0, "mark2@lbs.com"))

    # Display the email (does not send it)
    mail.Display(True)  # Set to True if you want the window to be modal

