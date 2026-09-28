"""
Azure Storage Service for uploading files and generating access links with SAS tokens.
"""

import pathlib
from datetime import datetime, timedelta, timezone

from artifactory import ArtifactoryPath
from azure.storage.blob import (
    AccountSasPermissions,
    BlobServiceClient,
    ResourceTypes,
    generate_account_sas,
)

from app.core.config import CONFIG

AF_SESSION: ArtifactoryPath = None


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
        account_url=f"https://{CONFIG.DST_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=CONFIG.DST_AZURE_KEY,
    )
    container_client = blob_service_client.get_container_client(
        CONFIG.DST_STORAGE_ACCOUNT_CONTAINER
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
        account_name=CONFIG.DST_STORAGE_ACCOUNT_NAME,
        account_key=CONFIG.DST_AZURE_KEY,
        resource_types=ResourceTypes(object=True),
        permission=AccountSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(days=expiry_days),
    )
    # Create blob client
    blob_service_client = BlobServiceClient(
        account_url=f"https://{CONFIG.DST_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=sas_token,
    )
    # Create a container client for the blob
    container_client = blob_service_client.get_container_client(
        CONFIG.DST_STORAGE_ACCOUNT_CONTAINER
    )
    blob_client = container_client.get_blob_client(dst_file_name)
    return dst_file_name + blob_client._query_str
