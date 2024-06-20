import os, uuid
# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

from azure.ai.ml.entities import ManagedOnlineEndpoint, ManagedOnlineDeployment, Model, Environment, BuildContext
from azure.identity import DefaultAzureCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.authorization.models import RoleAssignmentCreateParameters

from helper_functions import get_client, get_ai_studio_url_for_deploy

def deploy_flow(endpoint_name, deployment_name):

    client = get_client()

    # check if endpoint exists, create endpoint object if not
    try:
        endpoint = client.online_endpoints.get(endpoint_name)
    
    except Exception as e:
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            properties={
              "enforce_access_to_default_secret_stores": "enabled" # if you want secret injection support
            },
            auth_mode="aad_token" # using aad auth instead of key-based auth
        )

    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=Model(
            name="copilot_flow_model",
            path="./copilot_flow", # path to promptflow folder
            properties=[ # this enables the chat interface in the endpoint test tab
                ["azureml.promptflow.source_flow_id", "basic-chat"],
                ["azureml.promptflow.mode", "chat"],
                ["azureml.promptflow.chat_input", "chat_input"],
                ["azureml.promptflow.chat_output", "reply"]
            ]
        ),
        environment=Environment(
            build=BuildContext(
                path="./copilot_flow",
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
        # instance type comes with associated cost.
        # make sure you have quota for the specified instance type
        # See more details here: https://learn.microsoft.com/azure/machine-learning/reference-managed-online-endpoints-vm-sku-list
        instance_type="Standard_DS3_v2",
        instance_count=1,
        environment_variables={
            "PRT_CONFIG_OVERRIDE": f"deployment.subscription_id={client.subscription_id},deployment.resource_group={client.resource_group_name},deployment.workspace_name={client.workspace_name},deployment.endpoint_name={endpoint_name},deployment.deployment_name={deployment_name}",
            # the following is enabled by secret injection
            # make sure your environment variables here match the environment variables your code depends on
            'AZURE_OPENAI_ENDPOINT': os.environ['AZURE_OPENAI_ENDPOINT'],
            'AZURE_SEARCH_ENDPOINT':  os.environ['AZURE_SEARCH_ENDPOINT'],
            'AZURE_OPENAI_API_VERSION': os.environ['AZURE_OPENAI_API_VERSION'],
            'AZURE_OPENAI_CHAT_DEPLOYMENT': os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT'],
            'AZURE_OPENAI_EVALUATION_DEPLOYMENT': os.environ['AZURE_OPENAI_EVALUATION_DEPLOYMENT'],
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': os.environ['AZURE_OPENAI_EMBEDDING_DEPLOYMENT'],
            'AZUREAI_SEARCH_INDEX_NAME': os.environ['AZUREAI_SEARCH_INDEX_NAME']
        }
    )

    # 1. create endpoint
    endpoint = client.begin_create_or_update(endpoint).result() # result() means we wait on this to complete

    # 2. create deployment
    deployment = client.begin_create_or_update(deployment).result()

    # 3. update endpoint traffic for the deployment
    endpoint.traffic = {deployment_name: 100} # 100% of traffic
    endpoint = client.begin_create_or_update(endpoint).result()

    # 4. provide endpoint access to Azure Open AI resource
    create_role_assignment(
        scope=f"/subscriptions/{os.environ["AZURE_SUBSCRIPTION_ID"]}/resourceGroups/{os.environ["AZURE_RESOURCE_GROUP"]}/providers/Microsoft.CognitiveServices/accounts/{os.environ["AZURE_OPENAI_CONNECTION_NAME"]}",
        role_name="Cognitive Services OpenAI User",
        principal_id=endpoint.identity.principal_id
        )

    # 5. provide endpoint access to Azure AI Search resource
    create_role_assignment(
        scope=f"/subscriptions/{os.environ["AZURE_SUBSCRIPTION_ID"]}/resourceGroups/{os.environ["AZURE_RESOURCE_GROUP"]}/providers/Microsoft.Search/searchServices/{os.environ["AZURE_SEARCH_CONNECTION_NAME"]}",
        role_name="Search Index Data Contributor",
        principal_id=endpoint.identity.principal_id
        )
    
    output_deployment_details(
        client=client,
        endpoint_name=endpoint_name,
        deployment_name=deployment_name
        )

def create_role_assignment(scope, role_name, principal_id):
    
    # Get credential
    credential = DefaultAzureCredential()

    # Instantiate the authorization management client
    auth_client = AuthorizationManagementClient(
        credential=credential,
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"]
        )
    
    roles = list(auth_client.role_definitions.list(
        scope,
        filter="roleName eq '{}'".format(role_name)))
    
    assert len(roles) == 1
    role = roles[0]
    
    # Create role assignment properties
    parameters = RoleAssignmentCreateParameters(
        role_definition_id=role.id,
        principal_id=principal_id,
        principal_type="ServicePrincipal"
        )
    
    # Create role assignment
    role_assignment = auth_client.role_assignments.create(
        scope=scope,
        role_assignment_name=uuid.uuid4(),
        parameters=parameters
        )
    
    return role_assignment

def output_deployment_details(client, endpoint_name, deployment_name) -> str:
    print("\n ~~~Deployment details~~~")
    print(f"Your online endpoint name is: {endpoint_name}")
    print(f"Your deployment name is: {deployment_name}")
    
    print("\n ~~~Test in the Azure AI Studio~~~")
    print("\n Follow this link to your deployment in the Azure AI Studio:")
    print(get_ai_studio_url_for_deploy(client=client, endpoint_name=endpoint_name, deployment_name=deployment_name))
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", help="endpoint name to use when deploying or invoking the flow", type=str)
    parser.add_argument("--deployment-name", help="deployment name used to deploy to a managed online endpoint in AI Studio", type=str)
    args = parser.parse_args()

    endpoint_name = args.endpoint_name if args.endpoint_name else f"rag-copilot-endpoint"
    deployment_name = args.deployment_name if args.deployment_name else f"rag-copilot-deployment"

    deploy_flow(endpoint_name, deployment_name)