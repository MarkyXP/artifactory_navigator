from datetime import datetime, timedelta
from textwrap import dedent
from typing import List

import win32com.client as win32
from artifactory import ArtifactoryPath

from app.core.config import CONFIG


def _af_items_to_html_table(items: List[ArtifactoryPath]):
    fmt_items = [
        f"<tr><td>{item.name}</td><td>{item.stat().sha256}</td></tr>" for item in items
    ]
    rows = "\n        ".join(fmt_items)
    html = dedent(
        f""" \
        <table
            style="border-collapse:collapse; border-top: 1px solid #cccccc; border-bottom: 1px solid #cccccc;"
            cellspacing="0" cellpadding="0" border="0" align="center" width="640">
            <tbody>
                <tr>
                    <td style="font-family:Arial>Document Name</td>
                    <td style="font-family:Arial>Document SHA256</td>
                </tr>
                {rows}
            </tbody>
        </table>
        """
    )
    return html


def generate_dst_email(
    recipient_name: str,
    recipient_email: str,
    recipient_company: str,
    retention_time: int,
    zip_filename: str,
    af_items : List[ArtifactoryPath],
    download_link : str,
):
    # Calculate the expiry date
    expirydate = (datetime.now + timedelta(retention_time)).strftime("%-d/%b/%Y")

    # Create an instance of Outlook
    outlook = win32.Dispatch("outlook.application")

    # Create a new email item
    mail = outlook.CreateItem(0)  # 0: olMailItem

    with open(CONFIG.SHIPPING_TOOL_EMAIL_BODY_LOCATION, "r") as f:
        email_body: str = f.read()
    email_body = email_body.replace("$Name", recipient_name)
    email_body = email_body.replace("$ExpiryTime", expirydate)
    email_body = email_body.replace("$FileSHATable", _af_items_to_html_table(af_items))
    email_body = email_body.replace("$Filename", zip_filename)
    email_body = email_body.replace("$URL", download_link)

    # Set email properties
    mail.To = recipient_email  # Replace with the recipient's email address
    mail.Subject = f"File download from Leica BioSystems for {recipient_company}"
    mail.HTMLBody = email_body
    # mail.CC = "lbsmel.hw-engineeringrelease@leicabiosystems.com"
    # mail._oleobj_.Invoke(*(64209, 0, 8, 0, "mark2@lbs.com"))

    # Display the email (does not send it)
    mail.Display(True)  # Set to True if you want the window to be modal
