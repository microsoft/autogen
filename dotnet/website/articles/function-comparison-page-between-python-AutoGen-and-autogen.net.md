### Function comparison between Python AutoGen and AutoGen\.Net


#### Agentic pattern

| Feature | AutoGen | AutoGen\.Net |
| :---------------- | :------ | :---- |
| Code interpreter | run python code in local/docker/notebook executor | run csharp code in dotnet interactive executor |
| Single agent chat pattern | ✔️ | ✔️ |
| Two agent chat pattern | ✔️ | ✔️ |
| group chat (include FSM)| ✔️ | ✔️ (using workflow for FSM groupchat) |
| Nest chat| ✔️ | ✔️ (using middleware pattern)|
|Sequential chat | ✔️ | ❌ (need to manually create task in code) |
| Tool | ✔️ | ✔️ |


#### LLM platform support

ℹ️ Note 

``` Other than the platforms list below, AutoGen.Net also supports all the platforms that semantic kernel supports via AutoGen.SemanticKernel as a bridge ```

| Feature | AutoGen | AutoGen\.Net |
| :---------------- | :------ | :---- |
| OpenAI (include third-party) | ✔️ | ✔️ |
| Mistral |	✔️|	✔️|
| Ollama |	✔️|	✔️|
|Claude	|✔️	|✔️|
|Gemini (Include Vertex) | ✔️ | ✔️ |

#### Popular Contrib Agent support


| Feature | AutoGen | AutoGen\.Net |
| :---------------- | :------ | :---- |
| Rag Agent |	✔️|	❌ |
| Web surfer |	✔️|	❌ |
