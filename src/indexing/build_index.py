import os
# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

from azure.ai.ml.entities import Index

from promptflow.rag.config import LocalSource, AzureAISearchConfig, EmbeddingsModelConfig, ConnectionConfig
from promptflow.rag import build_index

from helper_functions import get_client

# build the index using the product catalog docs from data/3-product-info
def build_aisearch_index(index_name, path_to_data):

  client = get_client()

  # Use the same index name when registering the index in AI Studio
  index_path = build_index(
      name=index_name,  # name of your index
    vector_store="azure_ai_search",  # the type of vector store - in this case it is Azure AI Search. Users can also use "azure_cognitive search"
    embeddings_model_config=EmbeddingsModelConfig(
      model_name=os.environ['AZURE_OPENAI_EMBEDDING_DEPLOYMENT'],
      deployment_name=os.environ['AZURE_OPENAI_EMBEDDING_DEPLOYMENT'],
      connection_config=ConnectionConfig(
        subscription_id=client.subscription_id,
        resource_group_name=client.resource_group_name,
        workspace_name=client.workspace_name,
        connection_name=os.environ['AZURE_OPENAI_CONNECTION_NAME']
      )
    ),
    input_source=LocalSource(input_data=path_to_data),  # the location of your files/folders
    index_config=AzureAISearchConfig(
        ai_search_index_name=index_name, # the name of the index store inside the azure ai search service
        ai_search_connection_config=ConnectionConfig(
            subscription_id=client.subscription_id,
            resource_group_name=client.resource_group_name,
            workspace_name=client.workspace_name,
            connection_name=os.environ['AZURE_SEARCH_CONNECTION_NAME']
          )
      ),
      tokens_per_chunk = 800, # Optional field - Maximum number of tokens per chunk
      token_overlap_across_chunks = 0, # Optional field - Number of tokens to overlap between chunks
  )
  print(f"Local Path: {index_path}")

  # register the index so that it shows up in the cloud project
  client.indexes.create_or_update(Index(name=index_name, path=index_path))

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("--index-name", help="index name to use when creating the AI Search index", type=str)
  parser.add_argument("--path-to-data", help="path to data for creating search index", type=str)
  args = parser.parse_args()
  index_name = args.index_name if args.index_name else None
  path_to_data = args.path_to_data if args.path_to_data else None

  if not index_name:
    index_name = "product-info-index"
  if not path_to_data:
    path_to_data = "./indexing/data/product-info/"
  
  build_aisearch_index(index_name, path_to_data)