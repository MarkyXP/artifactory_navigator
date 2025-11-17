from datetime import datetime, timedelta
import textwrap
from typing import List

import win32com.client as win32
from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.core import telemetry


def _af_items_to_html_table(items: List[ArtifactoryPath]):
    fmt_items = [
        f"""
            <tr>
                <td style='font-size:8px; border-bottom: 1px solid #ddd'>
                {item.name}
                </td>
                <td style='font-size:8px; border-bottom: 1px solid #ddd'>
                    {item.stat().sha256.lower()}
                </td>
            </tr>"""
        for item in items
    ]
    rows = "\n        ".join(fmt_items)
    html = textwrap.dedent(
        f""" \
        <table style="font-family:Arial, Helvetica, sans-serif; font-size:10px; color:#656565; padding-left: 5px; padding-right: 5px;" bgcolor="#f6f6f6" height="80" valign="middle" align="center" width="640">
            <colgroup>
                <col/><col/>
            </colgroup>
            <tr>
                <th style="border-bottom: 1px solid #ddd">Document Enclosed</th>
                <th style="border-bottom: 1px solid #ddd">SHA-256 Checksum</th>
            </tr>
            {rows}
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
    af_items: List[ArtifactoryPath],
    download_link: str,
):
    # Calculate the expiry date
    expirydate = (datetime.now() + timedelta(retention_time)).strftime(
        "%A, %d %B %Y %H:%M:%S %p"
    )

    # Create an instance of Outlook
    try:
        outlook = win32.Dispatch("outlook.application")

        # Create a new email item
        mail = outlook.CreateItem(0)  # 0: olMailItem

        with open(CONFIG.SHIPPING_TOOL_EMAIL_BODY_LOCATION, "r") as f:
            email_body: str = f.read()
        email_body = email_body.replace("$Name", recipient_name)
        email_body = email_body.replace("$ExpiryTime", expirydate)
        email_body = email_body.replace("$FileSHATable", _af_items_to_html_table(af_items))
        email_body = email_body.replace("$FileName", zip_filename)
        email_body = email_body.replace("$URL", download_link)
        email_body = email_body.replace("$YEAR", datetime.now().strftime("%Y"))

        # Set email properties
        mail.To = recipient_email  # Replace with the recipient's email address
        mail.Subject = f"File download from Leica BioSystems for {recipient_company}"
        mail.HTMLBody = email_body
        for account in outlook.Session.Accounts:
            if account.DisplayName == "lbsmel.hw-engineeringrelease@leicabiosystems.com":
                mail._oleobj_.Invoke(*(64209, 0, 8, 0, account))  # Property 64209 is "SendUsingAccount"
                break
        else:
            mail.CC = "lbsmel.hw-engineeringrelease@leicabiosystems.com"
        # Display the email
        mail.Display()
    except Exception as e:
        import traceback
        import wx
        telemetry.log("ERROR:\t"+traceback.format_exc())
        #app = wx.App(False)
        wx.MessageBox(
            f"Error generating the DST email: {e}",
            'Info',
            wx.OK | wx.ICON_WARNING
        )
        
