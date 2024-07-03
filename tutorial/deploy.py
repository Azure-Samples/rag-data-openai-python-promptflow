# <deploy>
import os
from dotenv import load_dotenv
load_dotenv()

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import ManagedOnlineEndpoint, ManagedOnlineDeployment, Model, Environment, BuildContext

client = MLClient(DefaultAzureCredential(), os.getenv("AZURE_SUBSCRIPTION_ID"), os.getenv("AZURE_RESOURCE_GROUP"), os.getenv("AZUREAI_PROJECT_NAME"))
endpoint_name = "tutorial-endpoint" 
deployment_name = "tutorial-deployment"

endpoint = ManagedOnlineEndpoint(
    name=endpoint_name,
    properties={
        "enforce_access_to_default_secret_stores": "enabled" # for secret injection support
    },
    auth_mode="aad_token" # using aad auth instead of key-based auth
)

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to the directory, appending the script directory to the relative path
copilot_path = os.path.join(script_dir, "copilot_flow")
deployment = ManagedOnlineDeployment(
    name=deployment_name,
    endpoint_name=endpoint_name,
    model=Model(
        name="copilot_flow_model",
        path=copilot_path, # path to promptflow folder
        properties=[ # this enables the chat interface in the endpoint test tab
            ["azureml.promptflow.source_flow_id", "basic-chat"],
            ["azureml.promptflow.mode", "chat"],
            ["azureml.promptflow.chat_input", "chat_input"],
            ["azureml.promptflow.chat_output", "reply"]
        ]
    ),
    environment=Environment(
        build=BuildContext(
            path=copilot_path,
        ),
        inference_config={
            "liveness_route": {
                "path": "/health",
                "port": 8080,
            },
            "readiness_route": {
                "path": "/health",
                "port": 8080,
            },
            "scoring_route":{
                "path": "/score",
                "port": 8080,
            },
        },
    ),
    instance_type="Standard_DS3_v2",
    instance_count=1,
    environment_variables={
        "PRT_CONFIG_OVERRIDE": f"deployment.subscription_id={client.subscription_id},deployment.resource_group={client.resource_group_name},deployment.workspace_name={client.workspace_name},deployment.endpoint_name={endpoint_name},deployment.deployment_name={deployment_name}",
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'AZURE_SEARCH_ENDPOINT':  os.getenv('AZURE_SEARCH_ENDPOINT'),
        'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION'),
        'AZURE_OPENAI_CHAT_DEPLOYMENT': os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT'),
        'AZURE_OPENAI_EVALUATION_DEPLOYMENT': os.getenv('AZURE_OPENAI_EVALUATION_DEPLOYMENT'),
        'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
        'AZUREAI_SEARCH_INDEX_NAME': os.getenv('AZUREAI_SEARCH_INDEX_NAME')
    }
)

# 1. create endpoint
created_endpoint = client.begin_create_or_update(endpoint).result() # result() means we wait on this to complete

# 2. create deployment
created_deployment = client.begin_create_or_update(deployment).result()

# 3. update endpoint traffic for the deployment
endpoint.traffic = {deployment_name: 100} # 100% of traffic
client.begin_create_or_update(endpoint).result()
# </deploy>

# <report>
def get_ai_studio_url_for_deploy(client: MLClient, endpoint_name: str, deployment_name) -> str:
    studio_base_url = "https://ai.azure.com"
    deployment_url = (
        f"{studio_base_url}/projectdeployments/realtime/{endpoint_name}/{deployment_name}/detail?wsid=/subscriptions/{client.subscription_id}/resourceGroups/{client.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{client.workspace_name}&deploymentName={deployment_name}"
    )

    return deployment_url

print("\n ~~~Deployment details~~~")
print(f"Your online endpoint name is: {endpoint_name}")
print(f"Your deployment name is: {deployment_name}")

print("\n ~~~Test in the Azure AI Studio~~~")
print("\n Follow this link to your deployment in the Azure AI Studio:")
print(get_ai_studio_url_for_deploy(client=client, endpoint_name=endpoint_name, deployment_name=deployment_name))
# </report>
