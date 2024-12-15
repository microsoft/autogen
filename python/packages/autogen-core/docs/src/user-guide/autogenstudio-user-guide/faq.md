---
myst:
  html_meta:
    "description lang=en": |
      FAQ for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# FAQ

## Q: How do I specify the directory where files(e.g. database) are stored?

A: You can specify the directory where files are stored by setting the `--appdir` argument when running the application. For example, `autogenstudio ui --appdir /path/to/folder`. This will store the database (default) and other files in the specified directory e.g. `/path/to/folder/database.sqlite`.

## Q: Can I use other models with AutoGen Studio?

Yes. AutoGen standardizes on the openai model api format, and you can use any api server that offers an openai compliant endpoint. In the AutoGen Studio UI, each agent has an `model_client` field where you can input your model endpoint details including `model`, `api key`, `base url`, `model type` and `api version`. For Azure OpenAI models, you can find these details in the Azure portal. Note that for Azure OpenAI, the `model name` is the deployment id or engine, and the `model type` is "azure".
For other OSS models, we recommend using a server such as vllm, LMStudio, Ollama, to instantiate an openai compliant endpoint.

## Q: The server starts but I can't access the UI

A: If you are running the server on a remote machine (or a local machine that fails to resolve localhost correctly), you may need to specify the host address. By default, the host address is set to `localhost`. You can specify the host address using the `--host <host>` argument. For example, to start the server on port 8081 and local address such that it is accessible from other machines on the network, you can run the following command:

```bash
autogenstudio ui --port 8081 --host 0.0.0.0
```

## Q: Can I export my agent workflows for use in a python app?

Yes. In the Team Builder view, you select a team and download its specification. This file can be imported in a python application using the `TeamManager` class. For example:

```python

from autogenstudio.teammanager import TeamManager

tm = TeamManager()
result_stream =  tm.run(task="What is the weather in New York?", team_config="team.json") # or wm.run_stream(..)

```

<!-- ## Q: Can I deploy my agent workflows as APIs?

Yes. You can launch the workflow as an API endpoint from the command line using the `autogenstudio` commandline tool. For example:

```bash
autogenstudio serve --workflow=workflow.json --port=5000
```

Similarly, the workflow launch command above can be wrapped into a Dockerfile that can be deployed on cloud services like Azure Container Apps or Azure Web Apps. -->

## Q: Can I run AutoGen Studio in a Docker container?

A: Yes, you can run AutoGen Studio in a Docker container. You can build the Docker image using the provided [Dockerfile](https://github.com/microsoft/autogen/blob/autogenstudio/samples/apps/autogen-studio/Dockerfile) and run the container using the following commands:

```bash
FROM python:3.10

WORKDIR /code

RUN pip install -U gunicorn autogenstudio

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    AUTOGENSTUDIO_APPDIR=/home/user/app

WORKDIR $HOME/app

COPY --chown=user . $HOME/app

CMD gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind "0.0.0.0:8081"
```

Using Gunicorn as the application server for improved performance is recommended. To run AutoGen Studio with Gunicorn, you can use the following command:

```bash
gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind
```
