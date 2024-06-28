
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
from promptflow.evals.evaluators import RelevanceEvaluator, GroundednessEvaluator, CoherenceEvaluator

# add custom metric
from custom_evaluators.completeness import CompletenessEvaluator


# Define helper methods
def load_jsonl(path):
    with open(path, "r") as f:
        return [json.loads(line) for line in f.readlines()]

def copilot_qna(*, chat_input, **kwargs):
    from copilot_flow.copilot import get_chat_response

    result = get_chat_response(chat_input)
    # turn generator response into a string for evaluation
    answer = "".join(str(item) for item in result["reply"])
    parsedResult = {
        "answer": answer
    }
    return parsedResult

def run_evaluation(name, dataset_path):
    
    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_OPENAI_EVALUATION_DEPLOYMENT"]
    )

    # Initializing Evaluators
    completeness_eval = CompletenessEvaluator(model_config)

    # Running Relevance Evaluator on single input row
    completeness_score = completeness_eval(
        answer="The Alpine Explorer Tent is the most waterproof.",
        truth="From the our product list,"
        " the alpine explorer tent is the most waterproof."
        " The Adventure Dining Table has higher weight.",
        question="Which tent is the most waterproof?",
    )
    print("testing completeness score on dummy input: ", completeness_score)

    data_path = str(pathlib.Path.cwd() / dataset_path)
    output_path = str(pathlib.Path.cwd() / "evaluation/eval_results/eval_results.jsonl")

    result = evaluate(
        target=copilot_qna,
        evaluation_name=name,
        data=data_path,
        evaluators={
            "completeness": completeness_eval
        },
        evaluator_config={
            # only provide additional input fields that target and data do not have
            "completeness": {"question": "${data.chat_input}", "answer": "${target.answer}"}
        }
    )
    
    tabular_result = pd.DataFrame(result.get("rows"))
    tabular_result.to_json(output_path, orient="records", lines=True) 

    return result, tabular_result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-name", help="evaluation name used to log the evaluation to AI Studio", type=str)
    parser.add_argument("--dataset-path", help="Test dataset to use with evaluation", type=str)
    args = parser.parse_args()

    evaluation_name = args.evaluation_name if args.evaluation_name else "test-sdk-copilot"
    dataset_path = args.dataset_path if args.dataset_path else "./evaluation/evaluation_dataset_small.jsonl"
    
    result, tabular_result = run_evaluation(name=evaluation_name, dataset_path=dataset_path)

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")