# Copilot application that implements RAG

This is a sample copilot that application that implements RAG via custom Python code, and can be used with the Azure AI Studio. This sample aims to provide a starting point for an enterprise copilot grounded in custom data that you can further customize to add additional intelligence or capabilities.  

Following the below steps, you will: set up your development environment, create or reference your Azure AI resources, explore prompts, build an index containing product information, run your copilot, evaluate it, and deploy your copilot to a managed endpoint.

> [!IMPORTANT]
> We do not guarantee the quality of responses produced by these samples or their suitability for use in your scenarios, and responses will vary as development of the samples is ongoing. You must perform your own validation the outputs of the application and its suitability for use within your company.

## Step 1: Set up your development environment

### Option 1: Explore sample with Codespaces

- To get started quickly with this sample, you can use a pre-built Codespaces development environment. **Click the button below** to open this repo in GitHub Codespaces, and then continue the readme!
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure/aistudio-azd-ragChatApp?quickstart=1)

- Once you've launched Codespaces you can proceed to step 2.

### Option 2: Develop in your own environment

#### Develop in a curated cloud environment
If you intend to develop your own code following this sample, we recommend you use the **Azure AI curated VS Code development environment**.

- You can get started with this cloud environment from the Azure AI Studio by following these steps: [Work with Azure AI projects in VS Code](https://learn.microsoft.com/azure/ai-studio/how-to/develop-in-vscode)
- Once you are set up, follow the steps below. This is a Linux environment.

#### Develop locally
- If you prefer to develop locally, simply follow the steps below

#### Environment set up steps
1. Create a new Python virtual environment to safely install the SDK packages:

- On MacOS and Linux run:

   ``` bash
   python3 -m venv .venv
   ```

   ``` bash
   source .venv/bin/activate
   ```

- On Windows run:

   ``` bash
   py -3 -m venv .venv
   ```

   ``` bash
   .venv\scripts\activate
   ```

2. Now that your virtual environment is activated, install the SDK packages
    - First, navigate to the src directory. This is where you will do the majority of your work.

    ```bash
    cd src
    ```
    - Next, install the requirements in your venv. Note: this may take several minutes the first time you install.
    ``` bash
    pip install -r requirements.txt
    ```

3. If you haven't already done so, run `az login` to authenticate to Azure in your terminal.
    - Note: if you are running from within a Codespace or the curated VS Code cloud container, you will need to use `az login --use-device-code`

## Step 2: Provision or reference Azure AI resources
Use the provision script to provision new or reference existing Azure AI resources to use in your application.

We have a process to help you easily provision the resources you need to run this sample. You can either create new resources, or specify existing resources.

You can find the details you need for existing resources in the top-right project picker of the Azure AI Studio in the project view.

> [!NOTE]
> If you are viewing this README from within the curated VS Code cloud environment, there is a config.json file in your project directory that will have your subscription, region and project details that you can bring to the provision.yaml file.

1. **Check your quota** for model deployments

    To ensure you have quota to provision the model deployments you want, you can either check the Quota page in the Azure AI Studio, or the Quotas page at [oai.azure.com](https://oai.azure.com/), for a given region.

    You can also try running our experimental script to check quota in your subscription. You can modify it to fit your requirements.

    > [!NOTE]
    > Note: this script is a tentative to help locating quota, but it might provide numbers that are not accurate. The Azure AI Studio or the [Azure OpenAI portal](https://oai.azure.com/), and our [docs of quota limits](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-limits) would be the source of truth.

    ```bash
    python provisioning/check_quota.py --subscription-id <your-subscription-id>
    ```

2. **Open the _provision.yaml_ file** that is located in the `provisioning` directory
    1. There are notes in the file to help you.
3. **Input all your desired fields**
    1. Note that you can either specify existing resources, or your desired names for new resources. If you are specifying existing resources, you can find the details you need in the Azure AI Studio project view.
    1. Make sure you select a location and deployments you have quota for.
1. **Run the _provision.py_ script**
    1. If you want to see the provisioning plan (what _would_ be provisioned given your `provision.yaml` specifications, without actually provisioning anything), run the below script with the `--show-only` flag.
    1. This script will output a .env in your src/ directory with all of your specified resources, which will be referenced by the rest of the sample code.

    ``` bash
    # Note: make sure you run this command from the src/ directory so that your .env is written to the correct location (src/)
    python provisioning/provision.py --export-env .env
    ```

    The script will check whether the resources you specified exist, otherwise it will create them. It will then construct a .env for you that references the provisioned or referenced resources, including your keys. Once the provisioning is complete, you'll be ready to move to step 3.


## Step 3: Explore prompts

This sample repository contains a sample chat prompty file you can explore. This will let you verify your environment is set up to call your model deployments.

This pattern was covered in the [hello world prompting sample](https://github.com/Azure-Samples/ai-studio-hello-world), showing how the Prompty file format let's you streamline your LLM calls.

You can test your connection to your Azure Open AI model by running only the sample prompt. Try changing up the specified system prompt to see how the model behaves with additional prompting.

``` bash
cd ..
pf flow test --flow ./sample_flow --inputs query="why is the sky blue?"
```

Because we have more complex model orchestration logic for our RAG application, in the next steps, we will integrate our custom logic with Prompty to retrieve relevant documents and then query the LLM with additional context.

## Step 4: Create an index

Our goal is to ground the LLM in our custom data. To do this, we will use promptflow to create a search index based on the specified product data.

If you already have an index you'd like to use, skip to Step 4b.

### Step 4a: Create a new index

The following is a script to streamline index creation. It build the search index locally, and publishes it to your AI Studio project in the cloud.

``` bash
python -m indexing.build_index --index-name <desired_index_name>
```

Add the argument `--path-to-data` if you want to use different data than what is provided in the data directory of this sample.

### Step 4b: Set the index reference

**Once you have the index you want to use, add the below entry to your .env file.** Note that the copilot code relies on this environment variable.

``` text
AZUREAI_SEARCH_INDEX_NAME=<index-name>
```

## Step 5: Develop custom code

This sample includes custom code to add retrieval augmented generation (RAG) to our application.

The code follows the following general logic:

1. Uses an embedding model to embed the the user's query
1. Retrieves relevant documents from the search index, given the query
1. Integrates the document context into messages passed to chat completion model
1. Returns the response from the Azure Open AI model

You can modify this logic as appropriate to fit your use case.

## Step 6: Use prompt flow to test copilot code

Use the built-in prompt flow front end to locally serve your application, and validate your copilot performs as expected on sample inputs.

``` bash
pf flow test --flow ./copilot_flow --inputs chat_input="how much for the Trailwalker shoes cost?"
```

You can use the `--ui` flag to test interactively with a sample chat experience. Prompt flow locally serves a front end integrated with your code.

If you want to test with chat_history, you can use or update the sample input json file, and test like below:

```bash
pf flow test --flow ./copilot_flow --inputs ./copilot_flow/input_with_chat_history.json
```

## Step 7: Batch evaluate, iterate, evaluate again (eval compare in AI Studio)

Evaluation is a key part of developing a copilot application. Once you have validated your logic on a sample set of inputs, its time to test it on a larger set of inputs.

Evaluation relies on an evaluation dataset. In this case, we have an evaluation dataset with chat_input and truth, and then a target function that adds the LLM response and context to the evaluation dataset before running the evaluations.

The following script streamlines the evaluation process. Update the evaluation code to set your desired evaluation metrics, or optionally evaluate on custom metrics. You can also change where the evaluation results get written to.

We recommend viewing your evaluation results in the Azure AI Studio, to compare evaluation runs with different prompts, or even different models.
Note that this will configure your project with a Cosmos DB account for logging. It may take several minutes the first time you run an evaluation.



``` bash
python -m evaluation.evaluate --evaluation-name <evaluation_name>
```

Specify the `--dataset-path` argument if you want to provide a different evaluation dataset.

If you do not want to log evaluation results to your AI Studio project, you can modify the _evaluation.py_ script to not pass the azure_ai_project parameter.

## Step 8: Deploy application to AI Studio

Use the deployment script to deploy your application to Azure AI Studio. This will deploy your app to a managed endpoint in Azure, that you can test, integrate into a front end application, or share with others.

You can make any changes to deployment specifications to fit your use case.
> [!NOTE]
> If you made any custom changes to your .env not covered in this README, make sure you reference them in the deploy.py script before you deploy so that they are available in the deployed environment.

``` bash
python -m deployment.deploy --endpoint-name <endpoint_name> --deployment-name <deployment_name>
```

If you get a quota error for the VM size during deployment, you can check VM availability on the Azure ML tab of the Quota page in the Azure AI Studio (the quota page is located on the home page left nav).

- You can then update the instance_type specified in the deploy.py script to match a size you have quota for. There is a comment with [helpful documentation for supported instance types for deployment](https://learn.microsoft.com/en-us/azure/machine-learning/reference-managed-online-endpoints-vm-sku-list?view=azureml-api-2).

Once you create an endpoint, you can re-deploy or update an existing deployment on that same endpoint.

## Step 9: Verify your deployment

We recommend you test your application in the Azure AI Studio. The previous step outputted a handy link to your deployment. If you don't use the link, simply navigate to the Deployments tab in your project, and select your new deployment.

Navigate to the Test tab, and try asking a question in the chat interface. You should see the response come back and you have verified your deployment!

If you prefer to test your deployed endpoint locally, you can invoke it with a sample question.

``` bash
python -m deployment.invoke --endpoint-name <endpoint_name> --deployment-name <deployment_name>
```

The invoke script uses a default query, but you can also pass your own query with the `--query` argument in the command above.
