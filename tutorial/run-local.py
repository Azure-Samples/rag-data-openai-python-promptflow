import os
from dotenv import load_dotenv

load_dotenv()

import requests
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

query = "Are the trailwalker shoes waterproof?"
endpoint_name = "tutorial-endpoint"

client = MLClient(
    DefaultAzureCredential(),
    os.getenv("AZURE_SUBSCRIPTION_ID"),
    os.getenv("AZURE_RESOURCE_GROUP"),
    os.getenv("AZUREAI_PROJECT_NAME"),
)


scoring_url = client.online_endpoints.get(endpoint_name).scoring_uri

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {client._credential.get_token('https://ml.azure.com').token}",
    "Accept": "application/json",
}

response = requests.post(
    scoring_url,
    headers=headers,
    json={"chat_input": query},
)
(print(response.json()["reply"]))
