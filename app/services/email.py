import win32com.client as win32


def generate_dst_email(recipient_name, recipient_email, download_link):
    # Create an instance of Outlook
    outlook = win32.Dispatch('outlook.application')

    # Create a new email item
    mail = outlook.CreateItem(0)  # 0: olMailItem

    # Set email properties
    mail.To = recipient_email  # Replace with the recipient's email address
    mail.Subject = 'Subject of the Email'
    mail.Body = 'This is the body of the email. You can edit it before sending.'

    # Display the email (does not send it)
    mail.Display(True)  # Set to True if you want the window to be modal

