# Copilot application that implements RAG

## Step 1: Set up your Azure AI project

### Step 1a: Use a cloud development environment

#### Explore sample with Codespaces

- To get started quickly with this sample, you can use a pre-built Codespaces development environment. **Click the button below** to open this repo in GitHub Codespaces, and then continue the readme!
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces)

- Once you've launched Codespaces you can proceed to step 2.

#### Start developing in an Azure AI curated VS Code development environment

- If you intend to develop your own code following this sample, we recommend you use the **Azure AI curated VS Code development environment**. It comes preconfigured with the Azure AI SDK packages that you will use to run this sample.
- You can get started with this cloud environment from the Azure AI Studio by following these steps: [Work with Azure AI projects in VS Code](https://learn.microsoft.com/azure/ai-studio/how-to/develop-in-vscode)

:grey_exclamation: **Important: If you are viewing this README from within this cloud VS Code environment, you can proceed directly to step 2!** This case will apply to you if you launched VS Code from an Azure AI Studio project. The Azure AI SDK packages including prompt flow are already installed.

### Step 1b: Alternatively, set up your local development environment

1. Clone the code sample locally. Fork the repo if you intend to build off of it for custom solutions.

``` bash
git clone https://github.com/Azure-Samples/rag-data-openai-python-promptflow.git
cd src
```

1. Next, create a new Python virtual environment where we can safely install the SDK packages:

- On MacOS and Linux run:

   ``` bash
   python3 --version
   python3 -m venv .venv
   ```

   ``` bash
   source .venv/bin/activate
   ```

- On Windows run:

   ``` bash
   py -3 --version
   py -3 -m venv .venv
   ```

   ``` bash
   .venv\scripts\activate
   ```

1. Now that your environment is activated, install the SDK packages

``` bash
pip install -r copilot_sdk_flow/requirements.txt
```

### Step 1c: Use the provision script to provision or reference Azure AI resources

The *provision.py* script will help provision the resources you need to run this sample. You specify your desired resources in the provision.yaml - there are notes in that file to help you. The script will check whether the resources you specified exist, otherwise it will create them. It will then construct a .env for you that references the provisioned or attached resources, including your keys. Once the provisioning is complete, you'll be ready to move to step 2.

:grey_exclamation: **Important: If you are viewing this README from within the cloud VS Code environment, the provisioning script will already have your subscription, hub and project details, and will extract other existing resources to set up your environment.**

``` bash
python provision.py --config provision.yaml --export-env .env --provision
```

## Step 2: Explore prompts

This sample repository contains a sample chat prompty file you can explore. This will let you verify your environment is set up to call your model deployments.

This pattern was covered in the [hello world prompting sample](https://github.com/Azure-Samples/ai-studio-hello-world), showing how the Prompty file format let's you streamline your LLM calls.

You can test your connection to your Azure Open AI model by running only the sample prompt. Try changing up the specified system prompt to see how the model behaves with additional prompting.

``` bash
pf flow test --flow ./sample-prompting --inputs question="why is the sky blue?"
```

Because we have more complex model orchestration logic for our RAG application, in the next steps, we will integrate our custom logic with prompty to retrieve relevant documents and then query the LLM with additional context.

## Step 3: Create an index

Our goal is to ground the LLM in our custom data. To do this, we will use promptflow to create a search index based on the specified product data.
The following is a script to streamline index creation. It build the search index locally, and publishes it to your AI Studio project in the cloud.

``` bash
python build_index.py --index-name <desired_index_name>
```

Add the argument `--path-to-data` if you want to use different data than what is provided in the data directory of this sample.

## Step 4: Develop custom code

This sample includes custom code to add retrieval augmented generation (RAG) to our application.

The code follows the following general logic:

1. Uses an embedding model to embed the the user's query
1. Retrieves relevant documents from the search index, given the query
1. Integrates the document context into messages passed to chat completion model
1. Returns the response from the Azure Open AI model

You can modify this logic as appropriate to fit your use case.

## Step 5: Use prompt flow to test copilot code

Use the built-in prompt flow front end to locally serve your application, and validate your copilot performs as expected on sample inputs.

``` bash
pf flow test --flow ./product-flow --inputs question="which tent is the most waterproof?"
```

You can use the `--ui` flag to test interactively with a sample chat experience. Prompt flow locally serves a front end integrated with your code.

## Step 6: Batch evaluate, iterate, evaluate again (eval compare in AI Studio)

Evaluation is a key part of developing a copilot application. Once you have validated your logic on a sample set of inputs, its time to test it on a larger set of inputs.
The following script streamlines the evaluation process. Update the evaluation code to set your desired evaluation metrics, or optionally evaluate on custom metrics.

View your evaluation results in the Azure AI Studio to compare evaluations runs with different prompts, or even different models.
You will need to provide an evaluation dataset. In this case, we have an evaluation dataset with question and truth, and then a target function that adds the LLM response and context to the evaluation dataset before running the evaluations.

``` bash
python evaluate.py --evaluation-name <evaluation_name> --dataset-path <dataset_path>
```

Specify the `--dataset-path` argument if you want to provide a different evaluation dataset.

## Step 7: Deploy application to AI Studio

Use the deployment script to deploy your application to Azure AI Studio. This will deploy your app to a managed endpoint in Azure, that you can test, integrate into a front end application, or share with others.
There will be a handy link outputted in the terminal for you to follow to see your deployment in the Azure AI Studio.

``` bash
python deploy.py --deployment-name <deployment_name>
```

You can make any changes to deployment specifications to fit your use case.

## Step 8: Verify your deployment

We recommend you follow the deployment link from the previous step to the test your application in the cloud. If you prefer to test your endpoint locally, you can invoke it.

``` bash
python invoke.py --deployment-name <deployment_name>
```

Add the `--stream` argument if you want the response to be streamed.
