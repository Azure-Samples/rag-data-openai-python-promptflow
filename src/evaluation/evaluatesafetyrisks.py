
import json
import pathlib

# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
from pprint import pprint

from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from promptflow.evals.evaluators import  ViolenceEvaluator, SexualEvaluator, SelfHarmEvaluator, HateUnfairnessEvaluator


# Define helper methods
def load_jsonl(path):
    with open(path, "r") as f:
        return [json.loads(line) for line in f.readlines()]

def copilot_qna(*, chat_input, **kwargs):
    from copilot_flow.copilot import get_chat_response

    result = get_chat_response(chat_input)
    parsedResult = {
        "answer": str(result["reply"]),
        "context": str(result["context"])
    }
    return parsedResult

def run_evaluation(name, dataset_path):
    project_scope = {
        "subscription_id": os.environ.get("AZURE_SUBSCRIPTION_ID"),
        "resource_group_name": os.environ.get("AZURE_RESOURCE_GROUP"),
        "project_name": os.environ.get("AZUREAI_PROJECT_NAME"),
    }

    violence_eval = ViolenceEvaluator(project_scope=project_scope)
    sexual_eval = SexualEvaluator(project_scope=project_scope)
    selfharm_eval = SelfHarmEvaluator(project_scope=project_scope)
    hateunfairness_eval = HateUnfairnessEvaluator(project_scope=project_scope)
    # Initializing Evaluators
    
    # Evaluate the default vs the improved system prompt to see if the improved prompt
    # performs consistently better across a larger set of inputs
    path = str(pathlib.Path.cwd() / dataset_path)

    output_path = str(pathlib.Path.cwd() / "./evaluation/eval_results/eval_results.jsonl")

    result = evaluate(
        # target=copilot_qna,
        evaluation_name=name,
        data=path,
        evaluators={
            "violence": violence_eval,
            "self_harm": selfharm_eval,
            "sexual": sexual_eval,
            "hate_unfairnes": hateunfairness_eval
        },
        # optionally specify input fields if they are different
        evaluator_config={
            "violence": {"question": "${data.question}"},
            "self_harm": {"question": "${data.question}"},
            "sexual": {"question": "${data.question}"},
            "hate_unfairnes": {"question": "${data.question}"}
        },
        output_path=output_path
    )
    
    tabular_result = pd.DataFrame(result.get("rows"))

    return result, tabular_result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-name", help="evaluation name used to log the evaluation to AI Studio", type=str)
    parser.add_argument("--dataset-path", help="Test dataset to use with evaluation", type=str)
    args = parser.parse_args()

    evaluation_name = args.evaluation_name if args.evaluation_name else "test-sdk-copilot"
    dataset_path = args.dataset_path if args.dataset_path else "./evaluation/adv_qa_pairs.jsonl"

    result, tabular_result = run_evaluation(name=evaluation_name,
                              dataset_path=dataset_path)

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")
