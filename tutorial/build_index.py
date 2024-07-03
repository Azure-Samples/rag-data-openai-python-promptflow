import os
from dotenv import load_dotenv
load_dotenv()

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import Index

from promptflow.rag.config import LocalSource, AzureAISearchConfig, EmbeddingsModelConfig, ConnectionConfig
from promptflow.rag import build_index

client = MLClient(DefaultAzureCredential(), os.getenv("AZURE_SUBSCRIPTION_ID"), os.getenv("AZURE_RESOURCE_GROUP"), os.getenv("AZUREAI_PROJECT_NAME"))
import os

# append directory of the current script to data directory
script_dir = os.path.dirname(os.path.abspath(__file__))
data_directory = os.path.join(script_dir, "data/product-info/")

# Check if the directory exists
if os.path.exists(data_directory):
    files = os.listdir(data_directory) # List all files in the directory
    if files:
        print(f"Data directory '{data_directory}' exists and contains {len(files)} files.")
    else:
        print(f"Data directory '{data_directory}' exists but is empty.")
        exit()
else:
    print(f"Data directory '{data_directory}' does not exist.")
    exit()

index_name = "tutorial-index" # your desired index name
index_path = build_index(
    name=index_name,  # name of your index
    vector_store="azure_ai_search",  # the type of vector store - in this case it is Azure AI Search. Users can also use "azure_cognitive search"
    embeddings_model_config=EmbeddingsModelConfig(
    model_name=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
    deployment_name=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'),
    connection_config=ConnectionConfig(
        subscription_id=client.subscription_id,
        resource_group_name=client.resource_group_name,
        workspace_name=client.workspace_name,
        connection_name=os.getenv('AZURE_OPENAI_CONNECTION_NAME')
    )
    ),
    input_source=LocalSource(input_data=data_directory),  # the location of your files
    index_config=AzureAISearchConfig(
        ai_search_index_name=index_name, # the name of the index store inside the azure ai search service
        ai_search_connection_config=ConnectionConfig(
        subscription_id=client.subscription_id,
        resource_group_name=client.resource_group_name,
        workspace_name=client.workspace_name,
        connection_name=os.getenv('AZURE_SEARCH_CONNECTION_NAME')
        )
    ),
    tokens_per_chunk = 800, # Optional field - Maximum number of tokens per chunk
    token_overlap_across_chunks = 0, # Optional field - Number of tokens to overlap between chunks
)

# register the index so that it shows up in the cloud project
client.indexes.create_or_update(Index(name=index_name, path=index_path))