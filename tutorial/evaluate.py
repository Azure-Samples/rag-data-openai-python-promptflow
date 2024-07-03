import json
import os
# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

import pandas as pd

from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from promptflow.evals.evaluators import RelevanceEvaluator, GroundednessEvaluator, CoherenceEvaluator

# Helper methods
def load_jsonl(path):
    with open(path, "r") as f:
        return [json.loads(line) for line in f.readlines()]

def copilot_wrapper(*, chat_input, **kwargs):
    from copilot_flow.copilot import get_chat_response

    result = get_chat_response(chat_input)

    parsedResult = {
        "answer": str(result["reply"]),
        "context": str(result["context"])
    }
    return parsedResult

def run_evaluation(eval_name, dataset_path):

    model_config = AzureOpenAIModelConfiguration(
        azure_deployment=os.getenv("AZURE_OPENAI_EVALUATION_DEPLOYMENT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    # Initializing Evaluators
    relevance_eval = RelevanceEvaluator(model_config)
    groundedness_eval = GroundednessEvaluator(model_config)
    coherence_eval = CoherenceEvaluator(model_config)

    output_path = "./eval_results.jsonl"

    result = evaluate(
        target=copilot_wrapper,
        evaluation_name=eval_name,
        data=dataset_path,
        evaluators={
            "relevance": relevance_eval,
            "groundedness": groundedness_eval,
            "coherence": coherence_eval
        },
        evaluator_config={
            "relevance": {"question": "${data.chat_input}"},
            "coherence": {"question": "${data.chat_input}"},
        },
        # to log evaluation to the cloud AI Studio project
        azure_ai_project = {
            "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID"),
            "resource_group_name": os.getenv("AZURE_RESOURCE_GROUP"),
            "project_name": os.getenv("AZUREAI_PROJECT_NAME")
        }
    )

    tabular_result = pd.DataFrame(result.get("rows"))
    tabular_result.to_json(output_path, orient="records", lines=True)
    
    return result, tabular_result 

if __name__ == '__main__':
  eval_name = "tutorial-eval"
  dataset_path = "./eval_dataset.jsonl"
  
  result, tabular_result = run_evaluation(eval_name=eval_name,
                              dataset_path=dataset_path)
  
  from pprint import pprint
  pprint("-----Summarized Metrics-----")
  pprint(result["metrics"])
  pprint("-----Tabular Result-----")
  pprint(tabular_result)
  pprint(f"View evaluation results in AI Studio: {result['studio_url']}")