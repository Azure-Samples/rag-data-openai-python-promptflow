import json
import pathlib
import os
# set environment variables before importing any other code
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from pprint import pprint

from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from promptflow.evals.evaluators import RelevanceEvaluator, FluencyEvaluator, GroundednessEvaluator, CoherenceEvaluator

#custom metrics
from custom_evaluators import FriendlinessEvaluator, CompletenessEvaluator


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

def run_evaluation(eval_name, dataset_path):

    model_config = AzureOpenAIModelConfiguration(
        azure_deployment=os.environ["AZURE_OPENAI_EVALUATION_DEPLOYMENT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"]
    )

    # Initializing Evaluators
    groundedness_eval = GroundednessEvaluator(model_config)
    relevance_eval = RelevanceEvaluator(model_config)
    fluency_eval = FluencyEvaluator(model_config)
    coherence_eval = CoherenceEvaluator(model_config)

    #custom eval
    friendliness_eval = FriendlinessEvaluator()
    #completeness_eval = CompletenessEvaluator(model_config)
    
    # Evaluate the default vs the improved system prompt to see if the improved prompt
    # performs consistently better across a larger set of inputs
    path = str(pathlib.Path.cwd() / dataset_path)

    output_path = str(pathlib.Path.cwd() / "evaluation/eval_results/eval_results.jsonl")

    result = evaluate(
        target=copilot_qna,
        evaluation_name=eval_name,
        data=path,
        evaluators={
            "groundedness": groundedness_eval,
            "relevance": relevance_eval,
            "fluency": fluency_eval,
            "coherence": coherence_eval,
            "friendliness": friendliness_eval,
            #"completeness": completeness_eval
        },
        evaluator_config={
            "relevance": {"question": "${data.chat_input}"},
            "fluency": {"question": "${data.chat_input}"},
            "coherence": {"question": "${data.chat_input}"},
            "friendliness": {"response": "${target.answer}"},
            #"completeness": {"question": "${data.chat_input}"}
        },
        output_path=output_path  # not supported yet, this is a noop, see line 71
    )
    
    tabular_result = pd.DataFrame(result.get("rows"))
    # UPCOMING: this line will be handled by output_path in evaluate function
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

    result, tabular_result = run_evaluation(eval_name=evaluation_name,
                              dataset_path=dataset_path)

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")