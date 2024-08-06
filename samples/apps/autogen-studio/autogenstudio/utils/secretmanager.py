import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from ..datamodel import Skill
from typing import List

def _get_secrets_from_azure():
    """
        Get secrets from Azure Key Vault

        Returns:
            List of secrets from Azure Key Vault.
    """
    KVUri = os.environ['AZURE_KEYVAULT_URL']

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KVUri, credential=credential)

    secret_names = [secret.name for secret in client.list_properties_of_secrets()]
    secrets = [client.get_secret(secret_name).value for secret_name in secret_names]
    
    return secrets

def get_secrets_from_cloud(secret_providers: List[str]):
    """
        Get secrets from cloud providers
        Args:
            secret_providers: List of cloud providers to get secrets from. For example: export CLOUD_SECRET_PROVIDERS=azure,aws

        Returns:
            List of secrets from all specified cloud providers

    """
    secrets = []
    for provider in secret_providers:
        if provider == "azure":
            secrets.extend(_get_secrets_from_azure())
        # more providers can be added here

    return secrets

def get_secrets_from_file(filepath):
    """
        Get secrets from a file
        Args: 
            filepath: Path to the file containing secret keys in env variable

        Returns:
            List of secrets from the file.
    """
    secrets=[]
    env_keys=[]
    with open(filepath, "r") as f:
        env_keys = f.read().split()
    
    for key in env_keys:
        secrets.append(os.environ[key])

    return secrets
    
def get_secrets_from_skills(dbmanager):
    """
        Get secrets from skills in the database
        Args:
            dbmanager: Database manager object

        Returns:
            List of secrets from skills in the database
    """
    secrets = []
    for skill in dbmanager.get(model_class=Skill).data:
        for secret in skill.secrets:
            if secret['value'] != (None or ''):
                secrets.append(secret['value'])
    
    return secrets