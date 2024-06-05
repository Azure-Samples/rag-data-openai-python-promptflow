import requests
from helper_functions import get_client

def invoke_deployment(endpoint_name: str, query: str, stream: bool = False):
    client = get_client()

    if stream:
        accept_header = "text/event-stream"
    else:
        accept_header = "application/json"

    scoring_url = client.online_endpoints.get(endpoint_name).scoring_uri

    headers = {
        "Content-Type": "application/json",
        "Authorization":  f"Bearer {client._credential.get_token('https://ml.azure.com').token}",
        "Accept": accept_header
    }

    response = requests.post(
        scoring_url,
        headers=headers,
        json={
            "chat_input": query,
            "stream": stream,
        },
    )

    if stream:
        for item in response.iter_lines(chunk_size=None):
            print(item)
    else:
        response = response.json()
        chatReply = response['reply']
        print(f"\n{chatReply}")
        # chatContext = response['context']
        # print(f"\n{chatContext}") # you can output context if you want


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", help="endpoint name to use when deploying or invoking the flow", type=str)
    parser.add_argument("--deployment-name", help="deployment name to use when deploying or invoking the flow", type=str)
    parser.add_argument("--query", help="pass the query you want to test the deployment with")
    parser.add_argument("--stream", help="Whether response from a particular implementation should be streamed or not", action="store_true")
    args = parser.parse_args()

    if not args.endpoint_name:
        raise("endpoint must be specified")

    query = "What can you tell me about the trailwalker shoes?"
    if args.query:
        query = args.query

    invoke_deployment(args.endpoint_name, query=query, stream=args.stream)