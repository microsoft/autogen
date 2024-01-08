# AutoGen Deploy -- Running Your AutoGen Agents as a Service

## Overview

This sample shows how to run your AutoGen agents as a service and respond
to client requests on demand.

## Prerequisites

We currently use RabbitMQ as the message broker. Using docker:

```bash
docker run -d --rm -p 5672:5672 --name autogen-deploy-broker rabbitmq:alpine
```

For other ways to install RabbitMQ, see [RabbitMQ Installation](https://www.rabbitmq.com/download.html).

Other brokers will be supported in the future.

## Install

```bash
pip install -r requirements.txt
```

## Running the Sample

First deploy two agents:

```bash
celery -A sample_service worker -l INFO
```

Then run a query:

```python
from sample_service import assistant, user_proxy

user_proxy.initiate_chat(
    assistant,
    message="What is the change YTD of the S&P 500?",
)
```

The agents are running as a service and will respond to the query.
