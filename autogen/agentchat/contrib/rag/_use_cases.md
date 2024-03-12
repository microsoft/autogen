## Use Cases and Feature Requests

These use cases and feature requests are collected from the UI demo in huggingface space, github issues, discord chats and customer feedbacks from other products.

1. Summarize a given document. (Users may upload one or more files)
    - What is this file about?
    - Summarize the methods in file methods.pdf

    The key here is that we need to retrieve contents based on the file names instead of the content, but we only have embeddings for the content chunks for now.

2. Questions based on the contents.
    - Tell me what is something? (something could be any concept in the given documents, for instances,  a case number of a law file, a method in a paper, etc.)

    - How can I make something? (the document could be a manual or instruction book)

    The current RetrieveChat works quite well on these kind of question because it usually can retrieves high relevant context.

3. Code generation tasks.
    - How can I train a classification model with FLAML and do parallel training with spark? ( This is a feature request from Data Science in Microsoft Fabric )

    - How do I set up a group chat with AutoGen? (Similar questions have been asked many times in AutoGen discord. Some users actually asked ChatGPT to generate sample code of AutoGen, and ran into issues.)

    The generated code barely has no bugs. And it could be very difficult to automatically correct it based on the code execution results.

    Code generation is a highly asked feature for many products: NL2SQL (kusto, cosmos, …), AutoML (flaml, pandas, spark…)

    - Retrieve python functions in coding-based QA

4. Multi-hop reasoning.
    - Datasets such as 2WikiMultihopQA
    - Complex questions in real product.

    - Retrieve from multiple sources for a question
    multiple retrievers are needed to answer one question and they each need to retrieve info from a different source

    Some questions can be answered by retrieving different context in parallel, for example: Which film came out first, Blind Shaft or The Mask Of Fu Manchu?

    Many more needs a sequential retrieving: Who is the mother of the director of film Polish-Russian War (Film)?

5. Multi-round conversation with pronouns
    - what's autogen
    - what's flaml
    - what's the common authors of the two?
    - List three papers they have co-authored?

6. Support different/customized vector databases
7. Support using existing collections in a vector database
8. Support different/customized retrieve/re-rank algorithms
9. Support QA with ability to UPDATE CONTEXT
10. Support EcoAssistant
11. Support RAG as a tool like in OpenAI Assistant
