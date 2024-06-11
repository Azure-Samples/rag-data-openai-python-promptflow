import os
import json
from promptflow.client import load_flow

class FriendlinessEvaluator:
    def __init__(self):
        current_dir = os.path.dirname(__file__)
        prompty_path = os.path.join(current_dir, "friendliness.prompty")
        self._flow = load_flow(source=prompty_path)

    def __call__(self, *, response: str, **kwargs):
        response =  self._flow(response=response)
        return json.loads(response)