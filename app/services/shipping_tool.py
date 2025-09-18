from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from azure.storage.blob import (
    AccountSasPermissions,
    BlobServiceClient,
    ResourceTypes,
    generate_account_sas,
)

from app.core.config import CONFIG

AZURE_KEY = ""
STORAGE_ACCOUNT_NAME = "docshippingtoolauto"
STORAGE_ACCOUNT_CONTAINER = "dstauto"

def upload(
    src: Path,
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


def get_access_token(dst_file_name: str, expiry_days: int = 7):
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
    return container_client.get_blob_client(dst_file_name).url
