# A2: Retrieval Augmented Code Generation and Question Answering with AutoGen

We utilize Retrieval-augmented Chat in two scenarios. The first scenario aids in generating code based on a given codebase. While LLMs possess strong coding abilities, they are unable to use packages or APIs that are not included in their training data, e.g., private codebase, or have trouble using trained ones that are frequently updated after training. Hence, Retrieval Augmented Code Generation is considered to be highly valuable. The second scenario is to do QA on the Natural Questions dataset. This enables us to obtain comparative evaluation metrics for the performance of our system.

## Scenario 1: Evaluation on Natural Questions QA dataset.

In this case, we evaluate Retrieval-augmented Chat's end-to-end question answering performance with the Natural Questions dataset. We collect 5,332 nonredundant context documents and 6,775 queries from the HuggingFace [Dataset](https://huggingface.co/datasets/thinkall/NaturalQuestionsQA). First, we create a document collection based on all the context corpus and store them in the vector database. Then we answer the questions with Retrieval-augmented Chat.

- Results on all the questions with Azure OpenAI gpt-35-turbo are as below:
```
Average F1: 25.88%
Average Recall: 66.65%
```

- Results on the first 500 questions with `Update Context` replaced by `I don't know` are as below:
```
Average F1: 22.79%
Average Recall: 62.59%
```

The F1 score and Recall score are significantly higher than the results showed in [this paper](https://arxiv.org/pdf/2307.16877v1.pdf). It also mentions that recall shows a stronger correlation with human-judged correctness than EM and F1.

To reproduce the results, configure the LLM endpoints and run [this notebook](NaturalQuestionsQA-gpt35turbo.ipynb).

## Scenario 2: Code generation leveraging latest APIs from the codebase

In this case, the question is *"How can I use FLAML to perform a classification task and use spark to do parallel training. Train 30 seconds and force cancel jobs if time limit is reached."*.

FLAML is an open-source Python library for efficient AutoML and tuning. It was open-sourced in December 2020, and is included in the training data of GPT-4. However, the question requires the use of Spark-related APIs, which was added in December 2022 and is not included in the GPT-4 training data. As a result, the original GPT-4 model is unable to generate the correct code, as it lacks knowledge of Spark-related APIs. Instead, it creates a non-existent parameter, $spark$, and sets it to $True$. However, with Retrieval-augmented Chat, we provide the latest reference documents as context. Then, GPT-4 generates the correct code blocks by setting $use\_spark$ and $force\_cancel$ to $True$.

To reproduce this case and find more examples, please check out [this notebook](../../notebook/agentchat_RetrieveChat.ipynb).
