**Placeholder for FAQ document**

More information about how this projects runs?

This project leverages the devcontainer concept via your local system or you can use codespaces. Within this devcontainer/Codespaces you will have everything installed what you need.
We are running mulitple containers. The devcontainer + Qdrant container + Cosmos emulator container.

We also are leveraging Azure Services which you can easily deploy with Azure Developer CLI. To learn more about this: https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/overview

Another concept we are using are Dev Tunnels. This basic explainiting is that Dev Tunnel will create a secure tunnel for your Webhook to send message to your local system or codespace enviroment. 
If you want to learn more about this: https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/overview

Communication between agents:
If you are running this fully locally we are using memory streams and local storage. If you are running this combined with Azure we are using Azure Event Hub for the communication between the agents (Can extended to use other solutions/services).

Chathistory is being stored in CosmosDB (Can extended to use other solutions/services). Locally you can use the Cosmos DB emulator container or you can leverage an Azure CosmosDB deployment. 

