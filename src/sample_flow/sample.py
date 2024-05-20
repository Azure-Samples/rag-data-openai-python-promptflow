# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path

from promptflow.core import tool, Prompty
# The inputs section will change based on the arguments of the tool function, after you save the code
# Adding type to arguments and return value will help the system show the types properly
# Please update the function name/signature per need

@tool
def entry(query: str) -> str:

    # path to prompty (requires absolute path for deployment)
    path_to_prompty = f"{Path(__file__).parent.absolute().as_posix()}/sample.prompty"
    # load prompty as a flow
    flow = Prompty.load(path_to_prompty)
    
    # execute the flow as function
    result = flow(query=query)
    return result
