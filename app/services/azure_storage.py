import pathlib
import subprocess
import textwrap
import threading
from datetime import datetime, timedelta, timezone

from artifactory import ArtifactoryPath
from azure.storage.blob import (AccountSasPermissions, BlobServiceClient,
                                ResourceTypes, generate_account_sas)

from app.core.config import CONFIG

AF_SESSION: ArtifactoryPath = None
AZURE_KEY = ""
STORAGE_ACCOUNT_NAME = ""
STORAGE_ACCOUNT_CONTAINER = ""


def _get_azure_details():
    """
    Connects to Artifactory, downloads the DST Settings, decrypts the Azure Key,
    and stores the DST settings temporarily

    Note: The get_azure_details thread should be called, not this function.
    """
    global STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_CONTAINER, AZURE_KEY
    _session = AF_SESSION.session
    response = _session.get(CONFIG.AZURE_DST_SETTINGS)
    jresp = response.json()
    if response.status_code != 200:
        return 
    STORAGE_ACCOUNT_NAME = jresp["Azure"]["storageAccountName"]
    STORAGE_ACCOUNT_CONTAINER = jresp["Azure"]["storageContainerName"]
    _encrypted_key = jresp["Azure"]["storageAccountKey"]
    key_location = (
        r"app\services\DSTFile"
        if pathlib.Path(r"app\services\DSTFile").exists()
        else "DSTFile"
    )
    decrypt_cmd = textwrap.dedent(
        """\
        $key = Get-Content """
        + key_location
        + """
        $data = \""""
        + _encrypted_key
        + """\"
        $decrypted = $data | ConvertTo-SecureString -key $key | ForEach-Object { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) }
        $decrypted
    """
    ).strip()
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= (
        subprocess.STARTF_USESHOWWINDOW
    )  # suppresses the new window when launching PowerShell
    result = subprocess.run(
        ["powershell", "-Command", decrypt_cmd],
        capture_output=True,  # Captures stdout and stderr
        text=True,  # Returns output as a string instead of bytes
        startupinfo=startupinfo,
    )
    AZURE_KEY = result.stdout


get_azure_details = threading.Thread(target=_get_azure_details, daemon=True)


def upload(
    src: pathlib.Path,
    dst_file_name: str,
    sender_email: str,
    recipient_name: str,
    recipient_email: str,
    recipient_company: str,
):
    """
    Uploads a file to Azure Blob Storage with custom metadata.

    Args:
        config_file: Path to the JSON config file containing Azure settings.
        src: Path to the file to upload.
        dst_file_name: Name of the file once uploaded (can be used to rename).
        key: Azure Storage Account Key.
        meta_sender: Metadata: Sender.
        meta_name: Metadata: Name.
        meta_company: Metadata: Company.
        meta_email_address: Metadata: Email Address.
    """
    # Create blob client
    blob_service_client = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=AZURE_KEY,
    )
    container_client = blob_service_client.get_container_client(
        STORAGE_ACCOUNT_CONTAINER
    )
    # Set metadata
    metadata = {
        "LeicaSender": sender_email,
        "DestName": recipient_name,
        "DestCompany": recipient_company,
        "DestEmail": recipient_email,
    }
    blob_client = container_client.get_blob_client(dst_file_name)
    # Upload file with metadata
    with open(src, "rb") as data:
        blob_client.upload_blob(data, overwrite=True, metadata=metadata)

    return blob_client.url


def get_access_link_w_token(dst_file_name: str, expiry_days: int = 7) -> str:
    # Generate the temporary SAS token
    sas_token = generate_account_sas(
        account_name=STORAGE_ACCOUNT_NAME,
        account_key=AZURE_KEY,
        resource_types=ResourceTypes(object=True),
        permission=AccountSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(days=expiry_days),
    )
    # Create blob client
    blob_service_client = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=sas_token,
    )
    # Create a container client for the blob
    container_client = blob_service_client.get_container_client(
        STORAGE_ACCOUNT_CONTAINER
    )
    blob_client = container_client.get_blob_client(dst_file_name)
    return dst_file_name + blob_client._query_str
