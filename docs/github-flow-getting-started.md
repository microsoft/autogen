## Prerequisites

- Access to gpt3.5-turbo or preferably gpt4 - [Get access here](https://learn.microsoft.com/en-us/azure/ai-services/openai/overview#how-do-i-get-access-to-azure-openai)
- [Setup a Github app](#how-do-i-setup-the-github-app)
- [Install the Github app](https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app)
- [Create labels for the dev team skills](#which-labels-should-i-create)

### How do I setup the Github app?

- [Register a Github app](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app).
- Setup the following permissions
    - Repository 
        - Contents - read and write
        - Issues - read and write
        - Metadata - read only
        - Pull requests - read and write
- Subscribe to the following events:
    - Issues
    - Issue comment
- Allow this app to be installed by any user or organization
- Add a dummy value for the webhook url, we'll come back to this setting
- After the app is created, generate a private key, we'll use it later for authentication to Github from the app

### Which labels should I create?

In order for us to know which skill and persona we need to talk with, we are using Labels in Github Issues

The default bunch of skills and personnas are as follows:
- PM.Readme
- PM.BootstrapProject
- Do.It
- DevLead.Plan
- Developer.Implement

Once you start adding your own skills, just remember to add the corresponding Label!

## How do I run this locally?

Codespaces are preset for this repo.

Create a codespace and once the codespace is created, make sure to fill in the `local.settings.json` file.

There is a `local.settings.template.json` you can copy and fill in, containing comments on the different config values.

Hit F5 and go to the Ports tab in your codespace, make sure you make the `:7071` port publically visible. [How to share port?](https://docs.github.com/en/codespaces/developing-in-codespaces/forwarding-ports-in-your-codespace?tool=vscode#sharing-a-port-1)

Copy the local address (it will look something like https://foo-bar-7071.preview.app.github.dev) and append `/api/github/webhooks` at the end. Using this value, update the Github App's webhook URL and you are ready to go!

Before you go and have the best of times, there is one last thing left to do [load the WAF into the vector DB](#load-the-waf-into-qdrant)



## How do I deploy this to Azure?

This repo is setup to use  [azd](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/overview) to work with the Azure bits. `azd` is installed in the codespace.

Let's start by logging in to Azure using
```bash
azd auth login
```

After we've logged in, we need to create a new environment and setup the OpenAI and GithubApp config.

```bash
azd env new dev
azd env set -e dev GH_APP_ID replace_with_gh_app_id
azd env set -e dev GH_APP_INST_ID replace_with_inst_id
azd env set -e dev GH_APP_KEY replace_with_gh_app_key
azd env set -e dev OAI_DEPLOYMENT_ID replace_with_deployment_id
azd env set -e dev OAI_EMBEDDING_ID replace_with_embedding_id
azd env set -e dev OAI_ENDPOINT replace_with_oai_endpoint
azd env set -e dev OAI_KEY replace_with_oai_key
azd env set -e dev OAI_SERVICE_ID replace_with_oai_service_id
azd env set -e dev OAI_SERVICE_TYPE AzureOpenAI
```

Now that we have all that setup, the only thing left to do is run

```
azd up -e dev
```

and wait for the azure components to be provisioned and the app deployed.

As the last step, we also need to [load the WAF into the vector DB](#load-the-waf-into-qdrant)

### Load the WAF into Qdrant. 

If you are running the app locally, we have [Qdrant](https://qdrant.tech/) setup in the Codespace and if you are running in Azure, Qdrant is deployed to ACA.
The loader is a project in the `util` folder, called `seed-memory`. We need to fill in the `appsettings.json` file in the `config` folder with the OpenAI details and the Qdrant endpoint, then just run the loader with `dotnet run` and you are ready to go.