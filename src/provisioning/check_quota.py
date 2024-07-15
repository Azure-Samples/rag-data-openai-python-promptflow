import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
import argparse
from tabulate import tabulate

# list of candidate models we need
CANDIDATE_MODELS = [
    {"name": "gpt-35-turbo", "version": "1106", "sku": "Standard", "kind": "OpenAI"},
    {"name": "gpt-35-turbo", "version": "0301", "sku": "Standard", "kind": "OpenAI"},
    {"name": "gpt-35-turbo", "version": "0613", "sku": "Standard", "kind": "OpenAI"},
    {"name": "gpt-4", "version": "turbo-2024-04-09", "sku": "Standard", "kind": "OpenAI"},
    {"name": "gpt-4o", "version": "2024-05-13", "sku": "Standard", "kind": "OpenAI"},
]

# list of regions in which to look for candidate models
CANDIDATE_LOCATIONS = [
    "australiaeast",
    "eastus",
    "eastus2",
    "francecentral",
    "norwayeast",
    "swedencentral",
    "uksouth",
]

# copied from https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits
REGIONAL_QUOTA_LIMITS = {
    # gpt-4
    ("australiaeast", "Standard", "gpt-4"): 40,
    ("eastus", "Standard", "gpt-4"): 0,
    ("eastus2", "Standard", "gpt-4"): 0,
    ("francecentral", "Standard", "gpt-4"): 20,
    ("norwayeast", "Standard", "gpt-4"): 0,
    ("swedencentral", "Standard", "gpt-4"): 40,
    ("uksouth", "Standard", "gpt-4"): 0,
    # gpt-35-turbo
    ("australiaeast", "Standard", "gpt-35-turbo"): 300,
    ("eastus", "Standard", "gpt-35-turbo"): 240,
    ("eastus2", "Standard", "gpt-35-turbo"): 300,
    ("francecentral", "Standard", "gpt-35-turbo"): 240,
    ("norwayeast", "Standard", "gpt-35-turbo"): 0,
    ("swedencentral", "Standard", "gpt-35-turbo"): 300,
    ("uksouth", "Standard", "gpt-35-turbo"): 240,
}


def fetch_quota(client, locations, models):
    """Fetch the quota for the specified models in the specified locations.

    Args:
        client (CognitiveServicesManagementClient): The client to use to fetch the quota.
        locations (list): The list of locations to search for the models.
        models (list): The list of models to search for, see CANDIDATE_MODELS
    """
    fetched_quotas_table = []

    for location in locations:
        print(f"Fetching quotas for the candidate models in {location}")
        for model in client.models.list(location=location):
            for _model in models:
                if (
                    model.model.name == _model["name"]
                    and (
                        model.model.version == _model["version"]
                        or _model["version"] == "*"
                    )
                    and (model.kind == _model["kind"] or _model["kind"] == "*")
                ):
                    for sku in model.model.skus:
                        if sku.name == _model["sku"] or _model["sku"] == "*":
                            # print(model.serialize())
                            quota = REGIONAL_QUOTA_LIMITS.get(
                                (location, sku.name, model.model.name), 0
                            )
                            fetched_quotas_table.append(
                                {
                                    "model": model.model.name,
                                    "version": model.model.version,
                                    "kind": model.kind,
                                    "location": location,
                                    "sku": sku.name,
                                    "quota": quota,
                                    "remaining_quota": quota,
                                }
                            )
    return fetched_quotas_table


def fetch_deployments(client):
    """Fetch the deployments for the specified models in the specified locations.

    Args:
        client (CognitiveServicesManagementClient): The client to use to fetch the deployments.
    """
    deployments_table = []

    for account in client.accounts.list():
        print(f"Fetching deployments for the account {account.name}...")
        resource_group = account.id.split("/")[4]
        for deployment in client.deployments.list(
            resource_group_name=resource_group,
            account_name=account.name,
        ):
            deployments_table.append(
                {
                    "account": account.name,
                    "location": account.location,
                    "resource_group": resource_group,
                    "deployment": deployment.name,
                    "model": deployment.properties.model.name,
                    "version": deployment.properties.model.version,
                    "sku": deployment.sku.name,
                    "used_capacity": deployment.sku.capacity,
                }
            )
            # print(deployments_table[-1])
    return deployments_table


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--subscription-id",
        help="Azure subscription id",
        type=str,
        default=os.environ["AZURE_SUBSCRIPTION_ID"]
    )
    args = parser.parse_args()

    # get a client
    client = CognitiveServicesManagementClient(
        credential=DefaultAzureCredential(),
        subscription_id=args.subscription_id,
    )

    # Fetch the quota for the candidate models in the candidate locations
    print("Fetching quotas for the candidate models in the candidate locations")
    fetched_quotas_table = fetch_quota(client, CANDIDATE_LOCATIONS, CANDIDATE_MODELS)
    # print(json.dumps(fetched_quotas_table, indent=4))

    # Fetch the deployments for the candidate models
    print("Fetching existing deployments in your subscription for the candidate models")
    fetched_deployments_table = fetch_deployments(client)
    # print(json.dumps(fetched_deployments_table, indent=4))

    # substract the capacity of the deployments from the quota
    for quota in fetched_quotas_table:
        for deployment in fetched_deployments_table:
            # capacity is segmented per model per location
            # different model versions are merged into a single model capacity
            if (
                quota["model"] == deployment["model"]
                and quota["location"] == deployment["location"]
                and quota["sku"] == deployment["sku"]
            ):
                quota["remaining_quota"] -= deployment["used_capacity"]
                if "used_at" not in quota:
                    quota["used_at"] = []
                quota["used_at"].append(
                    deployment["deployment"]
                    + "@"
                    + deployment["version"]
                    + ":"
                    + str(deployment["used_capacity"])
                )

    # show table in a readable format
    print(tabulate(fetched_quotas_table, headers="keys", tablefmt="pretty"))


if __name__ == "__main__":
    main()