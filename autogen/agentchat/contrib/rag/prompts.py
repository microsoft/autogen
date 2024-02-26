PROMPT_DEFAULT = """You're a retrieval augmented chatbot. You answer user's questions based on your own knowledge and the
context provided by the user. You should follow the following steps to answer a question:
Step 1, you estimate the user's intent based on the question and context. The intent can be a code generation task or
a question answering task.
Step 2, you reply based on the intent.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
If user's intent is code generation, you must obey the following rules:
Rule 1. You MUST NOT install any packages because all the packages needed are already installed.
Rule 2. You must follow the formats below to write your code:
```language
# your code
```

If user's intent is question answering, you must give as short an answer as possible.

User's question is: {input_question}

Context is: {input_context}
"""

PROMPT_CODE = """You're a retrieval augmented coding assistant. You answer user's questions based on your own knowledge and the
context provided by the user.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
For code generation, you must obey the following rules:
Rule 1. You MUST NOT install any packages because all the packages needed are already installed.
Rule 2. You must follow the formats below to write your code:
```language
# your code
```

User's question is: {input_question}

Context is: {input_context}
"""

PROMPT_QA = """You're a retrieval augmented chatbot. You answer user's questions based on your own knowledge and the
context provided by the user.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
You must give as short an answer as possible.

User's question is: {input_question}

Context is: {input_context}
"""

PROMPT_REFINE = """Please refine the user's question for BERT-based semantic search embedding, make it more concise
while ensuring it captures the essential information. Break it into {n} sub questions for multi-hop reasoning.
The raw question is: {input_question}

Reply in the following format:
1. {{sub_question_1}}
2. {{sub_question_2}}
...
"""

PROMPT_SELECT = """Please classify the user's question into one of the following categories: `qa`, `code`, `multihop`.
The question is: {input_question}

Reply exactly one of the category names, don't add any explanations.
"""

PROMPT_MULTIHOP = """You're a helpful AI assistant with retrieval augmented generation capability.
You answer user's question based on your own knowledge and the given context. If you can't answer the question
with the given context, ask a question for retrieving more context, ask question smart as the question may need
multi-hop reasoning. If you need to ask a sub question, reply a json {{"question":  "<sub question>"}},
if you know the answer, reply a json {{"answer": "<the answer>"}}.

User's question is: {input_question}

Context is: {input_context}
"""

PROMPT_CAPABILITIES = """The raw message for you is: \"\"\"{text}\"\"\". After applyiny RAG, the answer is: \"\"\"{rag_reply}\"\"\".
Now, please generate final response to the raw message."""

PROMPTS_RAG = {
    "qa": PROMPT_QA,
    "code": PROMPT_CODE,
    "multihop": PROMPT_MULTIHOP,
    "unknown": PROMPT_DEFAULT,
}

PROMPTS_GENERATOR = {
    "refine": PROMPT_REFINE,
    "select": PROMPT_SELECT,
}
