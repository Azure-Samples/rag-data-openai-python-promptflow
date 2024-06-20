import os
# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

def get_client() -> MLClient:
  # check if env variables are set and initialize client from those
  client = MLClient(DefaultAzureCredential(), os.environ["AZURE_SUBSCRIPTION_ID"], os.environ["AZURE_RESOURCE_GROUP"], os.environ["AZUREAI_PROJECT_NAME"])
  if client:
    return client
  
  raise Exception("Necessary values for subscription, resource group, and project are not defined")


def get_ai_studio_url_for_deploy(client: MLClient, endpoint_name: str, deployment_name) -> str:
    studio_base_url = "https://ai.azure.com"
    deployment_url = (
        f"{studio_base_url}/projectdeployments/realtime/{endpoint_name}/{deployment_name}/detail?wsid=/subscriptions/{client.subscription_id}/resourceGroups/{client.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{client.workspace_name}&deploymentName={deployment_name}"
    )

    return deployment_url