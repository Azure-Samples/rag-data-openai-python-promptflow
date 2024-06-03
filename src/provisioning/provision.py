"""Provision Azure AI resources for you."""

import logging
import os
import sys
import re
import argparse
from pydantic import BaseModel, field_validator
from omegaconf import OmegaConf
from collections import OrderedDict
import requests
import traceback
import uuid

# from azure.ai.ml.entities import Project, Hub
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.resource import ResourceManagementClient

# from azure.ai.ml.entities import Project,Hub
from azure.ai.ml.entities import (
    Hub,  # TODO: need to replace with Hub
    Project,  # TODO: need to replace with Project
    AzureOpenAIConnection,
    AzureAISearchConnection,
)

from typing import Any, Optional, Union


def get_arg_parser(parser: argparse.ArgumentParser = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(__doc__)

    parser.add_argument(
        "--verbose",
        help="Enable verbose logging",
        action="store_true",
    )
    parser.add_argument(
        "--yaml-spec",
        help="point to a provision.yaml spec file",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "provision.yaml"),
    )
    parser.add_argument(
        "--show-only",
        help="Don't provision but only show provisioning plan",
        action="store_true",
    )
    parser.add_argument(
        "--export-env",
        help="Export environment variables into a file",
        default=os.path.join(os.path.dirname(__file__), ".env"),
    )

    return parser


#################################
# Resource provisioning classes #
#################################


class AzureScopedResource(BaseModel):
    subscription_id: str
    resource_group_name: str
    location: str

    def scope(self) -> str:
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}"

    @field_validator("subscription_id", "resource_group_name", "location")
    @classmethod
    def validate_references(cls, v: str) -> str:
        if "<" in v or ">" in v:
            raise ValueError(
                f"Invalid value '{v}', did you forget to provide your own?"
            )
        return v


class RBACRoleAssignment(BaseModel):
    resource: AzureScopedResource
    role_definition_id: str
    object_id: str

    def scope(self) -> str:
        return (
            self.resource.scope()
            + f"/roleAssignments/{self.role_definition_id}/<object_id>/{self.object_id}"
        )

    @classmethod
    def get_self_client_id(cls) -> str:
        # run shell command
        # az ad signed-in-user show --query id -o tsv
        # to get the principal ID of the current user
        shell_command = "az ad signed-in-user show --query id -o tsv"
        # return os.popen(shell_command).read().strip()
        # use subprocess instead of os.popen
        try:
            import subprocess

            return (
                subprocess.run(shell_command, shell=True, capture_output=True)
                .stdout.decode()
                .strip()
            )
        except:
            raise Exception(
                f"Failed to get the object ID of the current user, please make sure you have logged in with Azure CLI.: {traceback.format_exc()}"
            )

    def get_bearer_token(self) -> str:
        credential = DefaultAzureCredential()
        bearer_token_provider = get_bearer_token_provider(
            credential, "https://management.azure.com/.default"
        )
        return bearer_token_provider()

    def exists(self) -> bool:
        try:
            # GET https://management.azure.com/{scope}/providers/Microsoft.Authorization/roleAssignments/{roleAssignmentName}?api-version=2022-04-01
            headers = {
                "Authorization": f"Bearer {self.get_bearer_token()}",
                # "Content-Type": "application/json",
            }
            response = requests.get(
                url=f"https://management.azure.com/{self.resource.scope()}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01",
                headers=headers,
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get role assignments: {response.text}")

            # returns the list of all assignments for the results, that we have to parse
            for role_assignment in response.json()["value"]:
                logging.debug(f"checking role_assignment: {role_assignment}")
                if (
                    role_assignment["properties"]["roleDefinitionId"].endswith(
                        self.role_definition_id
                    )
                    and role_assignment["properties"]["principalId"] == self.object_id
                ):
                    logging.debug(f"Role assignment exists: {role_assignment}")
                    return True
            return False
        except:
            logging.debug(
                f"Failed to check if role assignment exists: {traceback.format_exc()}"
            )
            return False

    def create(self):
        logging.info(
            f"Assigning role {self.role_definition_id} to object_id {self.object_id} on scope {self.resource.scope()}..."
        )
        headers = {
            "Authorization": f"Bearer {self.get_bearer_token()}",
            # "Content-Type": "application/json",
        }
        response = requests.put(
            url=f"https://management.azure.com/{self.resource.scope()}/providers/Microsoft.Authorization/roleAssignments/{str(uuid.uuid4())}?api-version=2022-04-01",
            headers=headers,
            json={
                "properties": {
                    "roleDefinitionId": f"{self.resource.scope()}/providers/Microsoft.Authorization/roleDefinitions/{self.role_definition_id}",
                    "principalId": self.object_id,
                }
            },
        )
        if response.status_code == 409 and "RoleAssignmentExists" in response.text:
            logging.info("Role assignment already exists.")
            return
        if response.status_code != 200:
            raise Exception(
                f"Status_code={response.status_code}, failed to assign role: {response.text}"
            )


class ResourceGroup(AzureScopedResource):
    def exists(self) -> bool:
        """Check if the resource group exists."""
        # use ResourceManagementClient
        client = ResourceManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            response = client.resource_groups.get(self.resource_group_name)
            return True
        except Exception as e:
            return False

    def create(self) -> Any:
        """Create a resource group."""
        client = ResourceManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        response = client.resource_groups.create_or_update(
            resource_group_name=self.resource_group_name,
            parameters={"location": self.location},
        )
        return response


class AzureAIHub(AzureScopedResource):
    hub_name: str

    def scope(self):
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{self.hub_name}"

    def exists(self) -> bool:
        """Check if the resource exists."""
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        try:
            created_hub = ml_client.workspaces.get(self.hub_name)
            logging.debug(f"hub found: {created_hub}")
            return True
        except Exception as e:
            logging.debug(f"hub not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Hub {self.hub_name}...")
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        hub = Hub(
            name=self.hub_name,
            location=self.location,
            resource_group=self.resource_group_name,
        )
        response = ml_client.workspaces.begin_create(hub).result()
        return response


class AzureAIProject(AzureScopedResource):
    hub_name: str
    project_name: str

    def scope(self):
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.MachineLearningServices/workspaces/{self.hub_name}/projects/{self.project_name}"

    def exists(self) -> bool:
        """Check if the resource exists."""
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        try:
            created_hub = ml_client.workspaces.get(self.hub_name)
            created_project = ml_client.workspaces.get(self.project_name)
            logging.debug(f"project found: {created_project}")
            return True
        except Exception as e:
            logging.debug(f"project not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Project {self.project_name}...")
        ml_client = MLClient(
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group_name,
            credential=DefaultAzureCredential(),
        )

        hub = ml_client.workspaces.get(self.hub_name)

        project = Project(
            name=self.project_name,
            hub_id=hub.id,
            location=hub.location,
            resource_group=hub.resource_group,
        )
        response = ml_client.workspaces.begin_create(project).result()

        return response


class AzureAISearch(AzureScopedResource):
    search_resource_name: str

    def scope(self):
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.Search/searchServices/{self.search_resource_name}"

    def exists(self) -> bool:
        """Check if the resource exists."""
        client = SearchManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            resource = client.services.get(
                resource_group_name=self.resource_group_name,
                search_service_name=self.search_resource_name,
            )
            logging.debug(f"search found: {resource}")
            return True
        except Exception as e:
            logging.debug(f"search not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating AI Search {self.search_resource_name}...")
        client = SearchManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        search = client.services.begin_create_or_update(
            resource_group_name=self.resource_group_name,
            search_service_name=self.search_resource_name,
            service={
                "location": self.location,
                # "properties": {"hostingMode": "default", "partitionCount": 1, "replicaCount": 3},
                "sku": {"name": "standard"},
                # "tags": {"app-name": "My e-commerce app"},
            },
        ).result()
        return search


class AzureOpenAIResource(AzureScopedResource):
    aoai_resource_name: str
    kind: Optional[str] = "OpenAI"

    def scope(self) -> str:
        return f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group_name}/providers/Microsoft.CognitiveServices/accounts/{self.aoai_resource_name}"

    def exists(self) -> bool:
        """Check if the resource exists."""
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )

        try:
            account = client.accounts.get(
                resource_group_name=self.resource_group_name,
                account_name=self.aoai_resource_name,
            )
            logging.debug(f"aoai found: {account}")
            return True
        except Exception as e:
            logging.debug(f"aoai not found: {e}")
            return False

    def create(self) -> Any:
        """Create the resource"""
        logging.info(f"Creating Azure OpenAI {self.aoai_resource_name}...")
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(), subscription_id=self.subscription_id
        )
        account = client.accounts.begin_create(
            resource_group_name=self.resource_group_name,
            account_name=self.aoai_resource_name,
            account={
                "sku": {"name": "S0"},
                "kind": self.kind,
                "location": self.location,
                "properties": {
                    # to hit api directly via endpoint
                    "custom_sub_domain_name": self.aoai_resource_name
                },
            },
        ).result()
        return account


class AzureOpenAIDeployment(BaseModel):
    resource: AzureOpenAIResource
    name: str
    model: str
    version: Optional[str] = None
    capacity: Optional[int] = 10

    def scope(self):
        return self.resource.scope() + f"/deployments/{self.name}"

    def exists(self) -> bool:
        """Check if the deployment exists."""
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(),
            subscription_id=self.resource.subscription_id,
        )

        try:
            deployment = client.deployments.get(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
                deployment_name=self.name,
            )
            logging.debug(f"aoai deployment found: {deployment}")
            return True
        except Exception as e:
            logging.debug(f"aoai deployment not found: {e}")
            return False

    def create(self) -> Any:
        """Create the deployment"""
        logging.info(f"Creating Azure OpenAI deployment {self.name}...")
        client = CognitiveServicesManagementClient(
            credential=DefaultAzureCredential(),
            subscription_id=self.resource.subscription_id,
        )
        deployment = client.deployments.begin_create_or_update(
            resource_group_name=self.resource.resource_group_name,
            deployment_name=self.name,
            account_name=self.resource.aoai_resource_name,
            deployment={
                "properties": {
                    "model": {
                        "format": "OpenAI",
                        "name": self.model,
                        "version": self.version,
                    }
                },
                "sku": {"capacity": self.capacity, "name": "Standard"},
            },
        ).result()
        return deployment


class ConnectionSpec(BaseModel):
    hub: AzureAIHub
    resource: Union[AzureAISearch, AzureOpenAIResource]
    name: str
    auth: str

    def scope(self):
        return self.hub.scope() + f"/connections/{self.name}"

    def exists(self) -> bool:
        """Check if the connection in AI Hub exists."""
        try:
            ml_client = MLClient(
                subscription_id=self.hub.subscription_id,
                resource_group_name=self.hub.resource_group_name,
                workspace_name=self.hub.hub_name,
                credential=DefaultAzureCredential(),
            )
            created_connection = ml_client.connections.get(self.name)
            logging.debug(f"connection found: {created_connection}")
            return True
        except Exception as e:
            logging.debug(f"connection not found: {e}")
            return False

    def create(self) -> Any:
        """Create the connection in AI Hub."""
        ml_client = MLClient(
            subscription_id=self.hub.subscription_id,
            resource_group_name=self.hub.resource_group_name,
            workspace_name=self.hub.hub_name,
            credential=DefaultAzureCredential(),
        )
        if isinstance(self.resource, AzureAISearch):
            # get search client
            rsc_client = SearchManagementClient(
                credential=DefaultAzureCredential(),
                subscription_id=self.resource.subscription_id,
            )

            # get resource endpoint and keys
            resource = rsc_client.services.get(
                resource_group_name=self.resource.resource_group_name,
                search_service_name=self.resource.search_resource_name,
            )

            # TODO: need better
            resource_target = (
                f"https://{self.resource.search_resource_name}.search.windows.net"
            )

            # get keys
            rsc_keys = rsc_client.admin_keys.get(
                resource_group_name=self.resource.resource_group_name,
                search_service_name=self.resource.search_resource_name,
            )

            # specify connection
            connection_config = AzureAISearchConnection(
                endpoint=resource_target,
                api_key=rsc_keys.primary_key,  # using key-based auth
                name=self.name,
            )

            # create connection
            return ml_client.connections.create_or_update(workspace_connection=connection_config)
        if isinstance(self.resource, AzureOpenAIResource):
            rsc_client = CognitiveServicesManagementClient(
                credential=DefaultAzureCredential(),
                subscription_id=self.resource.subscription_id,
            )

            # get endpoint
            resource_target = rsc_client.accounts.get(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
            ).properties.endpoints["OpenAI Language Model Instance API"]

            # get keys
            rsc_keys = rsc_client.accounts.list_keys(
                resource_group_name=self.resource.resource_group_name,
                account_name=self.resource.aoai_resource_name,
            )

            # specify connection
            connection_config = AzureOpenAIConnection(
                azure_endpoint=resource_target,
                api_key=rsc_keys.key1,  # using key-based auth
                name=self.name,
            )

            # create connection
            return ml_client.connections.create_or_update(
                workspace_connection=connection_config
            )
        else:
            raise ValueError(f"Unknown connection type: {self.resource.type}")


#####################
# Provisioning Plan #
#####################


class ProvisioningPlan:
    def __init__(self):
        self.steps = OrderedDict()

    def _add_step(self, key, resource):
        if key in self.steps:
            # disregard duplicates
            logging.debug(f"discarding duplicate key {key}")
        else:
            logging.debug(f"adding key {key} to provisioning plan")
            self.steps[key] = resource

    def add_resource(self, resource: Any):
        key = resource.scope()
        self._add_step(key, resource)

    def remove_existing(self):
        """Remove existing resources from the plan."""
        remove_keys = []
        for k in self.steps:
            if self.steps[k].exists():
                logging.info(
                    f"Resource {self.steps[k].__class__.__name__}={k} already exists, skipping."
                )
                remove_keys.append(k)
            else:
                logging.info(
                    f"Resource {self.steps[k].__class__.__name__}={k} does not exist, will be added to plan."
                )

        for k in remove_keys:
            del self.steps[k]

    def provision(self):
        """Provision resources in the plan."""
        for k in self.steps:
            logging.info(f"Provisioning resource {k}...")
            self.steps[k].create()

    def get_main_ai_hub(self):
        for k in self.steps:
            if isinstance(self.steps[k], AzureAIHub):
                return self.steps[k]
        return None

    def get_main_ai_project(self):
        for k in self.steps:
            if isinstance(self.steps[k], AzureAIProject):
                return self.steps[k]
        return None


########
# MAIN #
########


def build_provision_plan(config) -> ProvisioningPlan:
    """Depending on values in config, creates a provisioning plan."""
    plan = ProvisioningPlan()

    # Azure AI Hub
    if config.ai is None:
        raise ValueError("No AI resources in config.")
    plan.add_resource(
        ResourceGroup(
            subscription_id=config.ai.subscription_id,
            resource_group_name=config.ai.resource_group_name,
            location=config.ai.location,
        )
    )
    ai_hub = AzureAIHub(
        subscription_id=config.ai.subscription_id,
        resource_group_name=config.ai.resource_group_name,
        hub_name=config.ai.hub_name,
        location=config.ai.location,
    )
    plan.add_resource(ai_hub)

    assert (
        config.ai.hub_name != config.ai.project_name
    ), "AI hub_name cannot be the same as project_name"

    # Azure AI Project
    plan.add_resource(
        AzureAIProject(
            subscription_id=config.ai.subscription_id,
            resource_group_name=config.ai.resource_group_name,
            hub_name=config.ai.hub_name,
            project_name=config.ai.project_name,
            location=config.ai.location,
        )
    )

    # Search resource
    if hasattr(config, "search") and config.search is not None:
        search_subscription_id = (
            config.search.subscription_id
            if hasattr(config.search, "subscription_id")
            else config.ai.subscription_id
        )
        search_resource_group_name = (
            config.search.resource_group_name
            if hasattr(config.search, "resource_group_name")
            else config.ai.resource_group_name
        )
        search_location = (
            config.search.location
            if hasattr(config.search, "location")
            else config.ai.location
        )
        plan.add_resource(
            ResourceGroup(
                subscription_id=search_subscription_id,
                resource_group_name=search_resource_group_name,
                location=search_location,
            )
        )
        search = AzureAISearch(
            subscription_id=search_subscription_id,
            resource_group_name=search_resource_group_name,
            search_resource_name=config.search.search_resource_name,
            location=search_location,
        )
        plan.add_resource(search)
        plan.add_resource(
            ConnectionSpec(
                hub=ai_hub,
                name=config.search.connection_name,
                auth="key",
                resource=search,
            )
        )

    # AOAI resource
    aoai_subscription_id = (
        config.aoai.subscription_id
        if hasattr(config.aoai, "subscription_id")
        else config.ai.subscription_id
    )
    aoai_resource_group_name = (
        config.aoai.resource_group_name
        if hasattr(config.aoai, "resource_group_name")
        else config.ai.resource_group_name
    )
    aoai_location = (
        config.aoai.location if hasattr(config.aoai, "location") else config.ai.location
    )
    plan.add_resource(
        ResourceGroup(
            subscription_id=aoai_subscription_id,
            resource_group_name=aoai_resource_group_name,
            location=aoai_location,
        )
    )
    aoai = AzureOpenAIResource(
        subscription_id=aoai_subscription_id,
        resource_group_name=aoai_resource_group_name,
        aoai_resource_name=config.aoai.aoai_resource_name,
        location=aoai_location,
        kind=config.aoai.kind if hasattr(config.aoai, "kind") else "OpenAI",
    )
    plan.add_resource(aoai)
    plan.add_resource(
        ConnectionSpec(
            hub=ai_hub, name=config.aoai.connection_name, auth="key", resource=aoai
        )
    )
    if hasattr(config.aoai, "auth") and config.aoai.auth.mode == "aad":
        plan.add_resource(
            RBACRoleAssignment(
                resource=aoai,
                role_definition_id=config.aoai.auth.role,
                object_id=RBACRoleAssignment.get_self_client_id(),
            )
        )

    if hasattr(config.aoai, "deployments") and config.aoai.deployments:
        for deployment in config.aoai.deployments:
            plan.add_resource(
                AzureOpenAIDeployment(
                    resource=aoai,
                    name=deployment.name,
                    model=deployment.model,
                    version=(
                        deployment.version if hasattr(deployment, "version") else None
                    ),
                    capacity=(
                        deployment.capacity if hasattr(deployment, "capacity") else 10
                    ),
                )
            )

    return plan


def build_environment(environment_config, ai_project, env_file_path):
    """Get endpoints and keys from the config into the environment (dotenv)."""
    # connect to AI Hub
    ml_client = MLClient(
        subscription_id=ai_project.subscription_id,
        resource_group_name=ai_project.resource_group_name,
        workspace_name=ai_project.hub_name,
        credential=DefaultAzureCredential(),
    )

    # load dotenv vars as a dictionary
    from dotenv import dotenv_values

    dotenv_vars = dotenv_values(
        dotenv_path=env_file_path,
        verbose=False,
    )

    # overwrite values
    dotenv_vars["AZURE_SUBSCRIPTION_ID"] = ai_project.subscription_id
    dotenv_vars["AZURE_RESOURCE_GROUP"] = ai_project.resource_group_name
    dotenv_vars["AZUREAI_HUB_NAME"] = ai_project.hub_name
    dotenv_vars["AZUREAI_PROJECT_NAME"] = ai_project.project_name

    for key in environment_config.variables.keys():
        conn_str = environment_config.variables[key]

        # write constants directly
        if not conn_str.startswith("azureml://"):
            dotenv_vars[key] = conn_str
            continue

        # regex extract connection name and type from
        # "azureml://connections/NAME/SUFFIX"
        try:
            # suffix can be either /target or /credentials/key
            name, suffix = re.match(
                r"azureml://connections/([^/]+)/(.*)", conn_str
            ).groups()
            # name, type = re.match(r"azureml://connections/(.*)/(.*)", conn_str).groups()
        except AttributeError:
            logging.critical(f"Invalid connection string: {conn_str}")
            continue

        logging.info(f"Getting connection {name}...")

        # get connection
        connection = ml_client.connections.get(name, populate_secrets=True)
        ml_client.connections.get
        if suffix == "target":
            # get target endpoint
            dotenv_vars[key] = connection.target
        elif suffix == "credentials/key":
            # get key itself
            # value = connection.credentials.get(key="api_key")
            value = connection.api_key
            dotenv_vars[key] = value or ""
            if value is None:
                logging.error(f"Key {name} not found in connection {conn_str}")
                continue
        else:
            raise NotImplementedError(
                f"Unsupported connection string: {conn_str} (expecting suffix /target or /credentials/key, got {suffix})"
            )

    # write to file
    with open(env_file_path, "w") as f:
        for key in dotenv_vars:
            f.write(f"{key}={dotenv_vars[key]}\n")


def main():
    """Provision Azure AI resources for you."""
    parser = get_arg_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # exclude azure.* from logging
    logging.getLogger("azure.core").setLevel(logging.WARNING)
    logging.getLogger("azure.identity").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    yaml_spec = OmegaConf.load(args.yaml_spec)
    provision_plan = build_provision_plan(yaml_spec)

    # save ai_project for commodity
    ai_project = provision_plan.get_main_ai_project()

    # remove from the plan resources that already exist
    provision_plan.remove_existing()

    if provision_plan.steps == {}:
        logging.info("All resources already exist, nothing to do.")
    else:
        print("Here's the resulting provisioning plan:")
        for step_key in provision_plan.steps:
            print(
                f"- {provision_plan.steps[step_key].__class__.__name__} : {str(provision_plan.steps[step_key])}"
            )

    if not args.show_only:
        # provision all resources remaining
        provision_plan.provision()
    else:
        logging.info("That's the plan!")
    
    if args.export_env:
        logging.info(f"Building environment into {args.export_env}")
        build_environment(yaml_spec.environment, ai_project, args.export_env)

    if not args.show_only:
        logging.info("Provisioning complete.")

if __name__ == "__main__":
    main()