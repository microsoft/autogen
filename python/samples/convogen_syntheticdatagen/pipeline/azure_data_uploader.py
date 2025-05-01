import os
import json
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

token_credential = DefaultAzureCredential()

class AzureDataUploader:
    def __init__(self, config):
        self.config = config
        # local path to the data that needs to be uploaded
        self.data_dir_path = config["local_data_path"]
        self.file_extensions = config["file_extensions"] if "file_extensions" in config else ["tsv"]
        self.account_name = config["azure_account_name"]
        self.azure_blob_path = config["azure_blob_path"]
        self.azure_container = config["azure_container"]

    
    def upload_data_to_azure(self):
        # Create a BlobServiceClient object
        blob_service_client = BlobServiceClient(
            account_url=f"https://{self.account_name}.blob.core.windows.net",
            credential=token_credential
        )

        # Get a reference to the container where the files will be uploaded
        container_client = blob_service_client.get_container_client(self.azure_container)

        # Iterate over the files in the data directory
        file_upload_count = 0

        for root, dirs, files in os.walk(self.data_dir_path):
            for file in files:
                # Check if the file has the specified extension
                if file.endswith(tuple(self.file_extensions)):
                    # Get the local file path
                    local_file_path = os.path.join(root, file)

                    # Get the blob name (relative path from the data directory)
                    blob_name = os.path.join(self.azure_blob_path, os.path.relpath(local_file_path, self.data_dir_path))
                    print(blob_name)
                    try:
                        # Upload the file to Azure Blob Storage
                        with open(local_file_path, "rb") as data:
                            container_client.upload_blob(name=blob_name, data=data)

                        file_upload_count += 1
                        # delete the file after uploading
                        os.remove(local_file_path)
                    except Exception as e:
                        print(f"Error uploading file {local_file_path} to Azure Blob Storage: {e}")
        print(f"Data uploaded to Azure Blob Storage. Total files uploaded = {file_upload_count}")