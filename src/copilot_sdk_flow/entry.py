# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------
from typing import TypedDict

# set environment variables before importing any other code
from dotenv import load_dotenv, find_dotenv
print(find_dotenv())
load_dotenv(override=True)

class ChatResponse(TypedDict):
    context: dict
    reply: str

from promptflow.core import tool
# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need

@tool
def flow_entry_copilot_sdk(chat_input: str, stream=False, chat_history: list = []) -> ChatResponse:
    print("hello in entry")
    from chat import chat_completion
    # Call the async chat function with a single question and print the response
    if stream:
        result = chat_completion([{"role": "user", "content": chat_input}], stream=True)
        for r in result:
            print(r)
            print("\n")
    else:
        result = chat_completion([{"role": "user", "content": chat_input}], stream=False)
        print(result)
    
    return result
