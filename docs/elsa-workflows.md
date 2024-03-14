# SemanticKernel Activity Provider for Elsa Workflows 3.x

The project supports running [Microsoft Semantic Kernel](https://github.com/microsoft/semantic-kernel) Skills as workflows using [Elsa Workflows](https://v3.elsaworkflows.io).  You can build the workflows as .NET code or in the visual designer.
To run the designer:

```bash
> cd WorkflowsApp
> cp .env_example .env
# Edit the .env file to choose your AI model, add your API Endpoint, and secrets.
> . ./.env
> dotnet build
> dotnet run
# Open browser to the URI in the console output
```

By Default you can use "admin" and "password" to login. Please review [Workflow Security](https://v3.elsaworkflows.io/docs/installation/aspnet-apps-workflow-server) for into on securing the app, using API tokens, and more.

To [invoke](https://v3.elsaworkflows.io/docs/guides/invoking-workflows) a workflow, first it must be "Published". If your workflow has a trigger activity, you can use that. When your workflow is ready, click the "Publish" button. You can also execute the workflow using the API. Then, find the Workflow Definition ID. From a command line, you can use "curl":

```bash
> curl --location 'https://localhost:5001/elsa/api/workflow-definitions/{workflow_definition_id}/execute' \
--header 'Content-Type: application/json' \
--header 'Authorization: ApiKey {api_key}' \
--data '{
}'
```

Once you have the app runing locally, you can login (admin/password - see the [Elsa Workflows](https://v3.elsaworkflows.io) for info about securing). Then you can click "new workflow" to begin building your workflow with semantic kernel skills.

1. Drag workflow Activity blocks into the designer, and examine the settings.
2. Connect the Activities to specify an order of operations.
3. You can use Workfflow Variables to pass state between activities.
   1. Create a Workflow Variable, "MyVariable"
   2. Click on the Activity that you want to use to populate the variable.
   3. In the Settings box for the Activity, Click "Output"
   4. Set the "Output" to the variable chosen.
   5. Click the Activity that will use the variable. Click on "Settings".
   6. Find the text box representing the variable that you want to populate, in this case usually "input".
   7. Click the "..." widget above the text box, and select "javascript"
   8. Set the value of the text box to

   ```javascript
   `${getMyVariable()}`
   ```

   9. Run the workflow.

## Run via codespaces

The easiest way to run the project is in Codespaces. Codespaces will start a qdrant instance for you.

1. Create a new codespace from the *code* button on the main branch.
2. Once the code space setup is finished, from the terminal:

```bash
> cd cli
cli> cp ../WorkflowsApp/.env_example . 
# Edit the .env file to choose your AI model, add your API Endpoint, and secrets.
cli> bash .env
cli> dotnet build
cli> dotnet run --file util/ToDoListSamplePrompt.txt do it
```

You will find the output in the *output/* directory.
