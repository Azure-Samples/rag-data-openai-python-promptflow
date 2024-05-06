
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionChunk

import os
import jinja2
import pathlib
from typing import Iterable

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

templateLoader = jinja2.FileSystemLoader(pathlib.Path(__file__).parent.resolve())
templateEnv = jinja2.Environment(loader=templateLoader)
system_message_template = templateEnv.get_template("system-message.jinja2")

def get_documents(query, num_docs=2):
    index_name = os.environ["AZUREAI_SEARCH_INDEX_NAME"]
    #  retrieve documents relevant to the user's question from Cognitive Search
    search_client = SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"]),
        index_name=index_name)

    aoai_client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],    
        api_version=os.environ["AZURE_OPENAI_API_VERSION"]
    )

    # generate a vector embedding of the user's question
    embedding = aoai_client.embeddings.create(input=query,
                                            model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"])
    embedding_to_query = embedding.data[0].embedding

    context = ""
    # use the vector embedding to do a vector search on the index
    vector_query = VectorizedQuery(vector=embedding_to_query, k_nearest_neighbors=num_docs, fields="contentVector")
    results = search_client.search(
        search_text="",
        vector_queries=[vector_query],
        select=["id", "content"])

    for result in results:
        context += f"\n>>> From: {result['id']}\n{result['content']}"

    return context


def chat_completion(messages: list[dict], stream: bool = False,
                          session_state: any = None, context: dict[str, any] = {}):
    # get search documents for the last user message in the conversation
    user_message = messages[-1]["content"]
    documents = get_documents(user_message, context.get("num_retrieved_docs", 2))

    system_message = system_message_template.render(context=context)

    # make a copy of the context and modify it with the retrieved documents
    context = dict(context)
    context['documents'] = documents

    # add retrieved documents as context to the system prompt
    system_message = system_message_template.render(context=context)

    messages.insert(0, {"role": "system", "content": system_message})

    aoai_client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],    
        api_version=os.environ["AZURE_OPENAI_API_VERSION"]
    ) 

    # add context in the returned response
    if not stream:
        # call Azure OpenAI with the system prompt and user's question
        chat_completion = aoai_client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            messages=messages, temperature=context.get("temperature", 0.7),
            stream=stream,
            max_tokens=800)

        return dict(context=context,
                    reply=chat_completion.choices[0].message.content)
    else:
        streamed_chat_completion: Iterable[ChatCompletionChunk] = aoai_client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
            messages=messages, temperature=context.get("temperature", 0.7),
            stream=stream,
            max_tokens=800)
        
        return dict(context=context, 
                    reply=read_out_stream(streamed_chat_completion))

def read_out_stream(response):
    for chunk in response:
        if len(chunk.choices) > 0 and not chunk.choices[0].delta.content is None:
            yield chunk.choices[0].delta.content