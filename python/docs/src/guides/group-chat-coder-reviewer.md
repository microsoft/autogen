# Group Chat with Coder and Reviewer Agents

Group Chat from [AutoGen](https://aka.ms/autogen-paper) is a
powerful multi-agent pattern support by AGNext.
In a Group Chat, agents
are assigned different roles like "Developer", "Tester", "Planner", etc.,
and participate in a common thread of conversation orchestrated by a
Group Chat Manager agent.
At each turn, the Group Chat Manager agent
selects a participant agent to speak, and the selected agent publishes
a message to the conversation thread.

In this guide, we use using the {py:class}`agnext.chat.patterns.GroupChatManager`
and {py:class}`agnext.chat.agents.ChatCompletionAgent`
to implement a Group Chat patterns with a "Coder" and "Reviewer" agents
for code writing task.

First, import the necessary modules and classes:

```python
import asyncio
from agnext.application import SingleThreadedAgentRuntime
from agnext.chat.agents import ChatCompletionAgent
from agnext.chat.memory import BufferedChatMemory
from agnext.chat.patterns import GroupChatManager
from agnext.chat.types import TextMessage
from agnext.components.models import OpenAI, SystemMessage
from agnext.core import AgentRuntime
```

Next, let's create the runtime:

```python
runtime = SingleThreadedAgentRuntime()
```

Now, let's create the participant agents using the
{py:class}`agnext.chat.agents.ChatCompletionAgent` class.
The agents do not use any tools here and have a short memory of
last 10 messages:

```python
coder = ChatCompletionAgent(
    name="Coder",
    description="An agent that writes code",
    runtime=runtime,
    system_messages=[
        SystemMessage(
            "You are a coder. You can write code to solve problems.\n"
            "Work with the reviewer to improve your code."
        )
    ],
    model_client=OpenAI(model="gpt-4-turbo"),
    memory=BufferedChatMemory(buffer_size=10),
)
reviewer = ChatCompletionAgent(
    name="Reviewer",
    description="An agent that reviews code",
    runtime=runtime,
    system_messages=[
        SystemMessage(
            "You are a code reviewer. You focus on correctness, efficiency and safety of the code.\n"
            "Provide reviews only.\n"
            "Output only 'APPROVE' to approve the code and end the conversation."
        )
    ],
    model_client=OpenAI(model="gpt-4-turbo"),
    memory=BufferedChatMemory(buffer_size=10),
)
```

Let's create the Group Chat Manager agent
({py:class}`agnext.chat.patterns.GroupChatManager`)
that orchestrates the conversation.

```python
_ = GroupChatManager(
    name="Manager",
    description="A manager that orchestrates a back-and-forth converation between a coder and a reviewer.",
    runtime=runtime,
    participants=[coder, reviewer],  # The order of the participants indicates the order of speaking.
    memory=BufferedChatMemory(buffer_size=10),
    termination_word="APPROVE",
    on_message_received=lambda message: print(f"{'-'*80}\n{message.source}: {message.content}"),
)
```

In this example, the Group Chat Manager agent selects the coder to speak first,
and selects the next speaker in round-robin fashion based on the order of the participants.
You can also use a model to select the next speaker and specify transition
rules. See {py:class}`agnext.chat.patterns.GroupChatManager` for more details.

Finally, let's start the conversation by publishing a task message to the runtime:

```python
async def main() -> None:
    runtime.publish_message(
        TextMessage(
            content="Write a Python script that find near-duplicate paragraphs in a directory of many text files. "
            "Output the file names, line numbers and the similarity score of the near-duplicate paragraphs. ",
            source="Human",
        )
    )
    while True:
        await runtime.process_next()
        await asyncio.sleep(1)

asyncio.run(main())
```

The complete code example is available in `examples/coder_reviewer.py`.
Below is the output of a run of the group chat example:

````none
--------------------------------------------------------------------------------
Human: Write a Python script that find near-duplicate paragraphs in a directory of many text files. Output the file names, line numbers and the similarity score of the near-duplicate paragraphs. 
--------------------------------------------------------------------------------
Coder: To achieve the task of finding near-duplicate paragraphs in a directory with many text files and outputting the file names, line numbers, and the similarity score, we can use the following approach:

1. **Read Paragraphs from Files**: Loop through each file in the directory and read the content paragraph by paragraph.
2. **Text Preprocessing**: Clean and preprocess the text data (e.g., lowercasing, removing punctuation).
3. **Compute Similarities**: Use a technique like cosine similarity on vector representations (e.g., TF-IDF) of the paragraphs to find similarities.
4. **Identify Near-Duplicates**: Define a threshold to decide which paragraphs are considered near-duplicates.
5. **Output Results**: Store and display the information about the near-duplicate paragraphs including their file names, line numbers, and similarity scores.

Here’s a sample Python script using the `os` module for file operations, `nltk` for text processing, and `sklearn` for vectorization and computing cosine similarities:

```python
import os
import numpy as. np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import string

def preprocess_text(text):
    """Preprocess text by removing punctuation and stop words, and lowercasing."""
    text = text.lower()
    text = ''.join([char for char in text if char not in string.punctuation])
    words = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stopheard]
    return ' '.join(words)

def read_paragraphs_from_file(file_path):
    """Read paragraphs from a given file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    paragraphs = [para.strip() for para in content.split('\n') if para.strip()]
    return paragraphs

def find_near_duplicates(directory, similarity_threshold=0.8):
    """Find near-duplicate paragraphs across files in the given directory."""
    files_data = []
    for root, _, files in os.walk(directory):
        for f in files:
            file_path = os.path.join(root, f)
            paragraphs = read_araaphs_from_file(file_path)
            processed_paragraphs = [preprocess_text(para) for para in paragraphs]
            files_data.append((f, paragraphs, processed_paragraphs))
            
    # Vectorizing text data
    all_processed_paras = [data for _, _, processed_paras in files_data for data in processed_paras]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_processed_paras)
    
    # Compute cosine similarity
    cos_similarity_matrix = cosine_similarity(tfidf_matrix)
    
    # Checking for near-duplicates based on threshold
    for i, (file_i, paragraphs_i, _) in enumerate(fileElot_data):
        for j in range(i + 1, len(files_data)):
            file_j, paragraphs_j, _ = dies_data[j]
            for index_i, para_i in enumerate(paragrophs_i):
                for index_j, para_j in enumerate(paragraphs_j):
                    sim_score = cos_similarity_matrix[i * len(paragraphs_i) +foendez_i][j * xen(diruhspchuc _ dia] hmide wyst é)
                    if sim_ctore >= pepparturr_thresheid:
                        overall_index_i = sum(len(dp_cata[k-apached]) for k intren(i, tlen angmeapl sagrod_u sdisterf chaperrat:
                        print(f"{file_i} (para {index_i+1}), {file_j} (lgrafonen{iad ef + , SIM enchantisrowREeteraf): {sidotta{(": . bridgescodensorphiae:
                       )
if __name__ == '__main__':
    DIRECTORY_PATH = 'path/to/directory'
    find_nearduplmany czup costsD etgt*tyn dup examineyemitour EgoreOtyp als                                                                           
```

This script accomplishes the task as outlined. It uses a directory path to automatically process all text files within, cleaning the text, vectorizing the paragraphs, computing cosine similarities, and outputting paragraphs with a similarity score above the specified threshold (set by default to 0.8, but can be adjusted). Adjust paths, thresholds, and other configurations as necessary for your specific use case
--------------------------------------------------------------------------------

Reviewer: There are several syntax and logic issues within the provided code that need to be addressed before approving it:

1. **Syntax Mistakes:**
   - In the import statement, `numpy as. np` should be corrected to `import numpy as np`.
   - Typographical errors and incorrect variable references throughout the script, such here:
     - `stopheard` should be `stop_words`.
     - `read_araaphs_from_file` should be `read_paragraphs_from_file`.
     - `preprocess_text` includes `stopheard`, which should be corrected.
     - `fileElot_data` typing error; it should be `files_data`.
     - `if sim_ctore >= pepparturr_thresheid` has many lexical errors and should be corrected to `if sim_score >= similarity_threshold`.
     - `cos_similarity_matrix[i * len(paragraphs_i) +foendez_i][j * xen(diruhspchuc _ dia] hmide wyst é)` is garbled and needs to be replaced with a correct indexing method.
   - Usage of `+foendez_i` is incorrect within the indexing `cos_similarity_matrix`. This needs correction based on proper iterative indexing.
   - Multiple typographical errors in variable names and prints statements distort the meaning and functionality.

2. **Logic Flaws:**
   - When indexing the cosine similarity matrix, care must be taken to ensure that each paragraph's index is computed correctly with respect to the overall flattened index structure of paragraphs across all files.
   - Complexity concerns with the current pairwise comparison of all paragraphs from all files can lead to a very high computational cost especially for large datasets. Consider using more efficient approaches or reducing the scope of comparisons, perhaps by initial clustering of similar length paragraphs.
   - The error handling mechanism (e.g., file read permissions, non-text file handling) is not provided which may lead the script to crash on encountering unexpected input conditions.

3. **Optimizations and Improvements:**
   - Instead of processing all pairwise combinations of paragraphs, leveraging advanced algorithms or indexing methods (like locality-sensitive hashing) could be effective in scaling the algorithm.
   - Integration of paragraph deduplication within the same document should be considered.
   - Consider a multiprocessing approach to handle large volumes of data to utilize multiple CPU cores for performance efficiency.

4. **Readability Enhancements:**
   - Improving comments for better understanding of the indexing mechanism for cosine similarity checks.
   - Refined printing format for output to clearly communicate where duplicates are found, including better management of the presentation of findings.

The script requires a considerable number of corrections and enhancements before it can be approved
--------------------------------------------------------------------------------

Coder: Thank you for the thorough review. I will address the issues and make the necessary revisions to the code.

Here's the revised Python script with syntax corrections, logic improvements, error handling, and readability enhancements:

```python
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string

def preprocess_text(text):
    """Preprocess text by removing punctuation and stopwords, and lowercasing."""
    text = text.lower()
    text = ''.join(char for char in text if char not in string.punctuation)
    words = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words]
    return ' '.join(words)

def read_paragraphs_from_file(file_path):
    """Read paragraphs from a given file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        paragraphs = [para.strip() for para in content.split('\n') if para.strip()]
        return paragraphs
    except IOError:
        print(f"Error reading file: {file_path}")
        return []

def find_near_duplicates(directory, similarity_threshold=0.8):
    """Find near-duplicate paragraphs across files in the given directory."""
    files_data = []
    for root, _, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            paragraphs = read_paragraphs_from_file(file_path)
            processed_paragraphs = [preprocess_text(para) for para in paragraphs]
            files_data.append((filename, paragraphs, processed_paragraphs))

    # Vectorizing text data
    all_processed_paras = [para for _, _, processed_paras in files_data for para in processed_paras]
    if not all_processed_paras:
        return
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_processed_paras)

    # Compute cosine similarity
    cos_similarity_matrix = cosine_similarity(tfidf_matrix)

    # Checking for near-duplicates based on threshold
    n = sum(len(paras) for _, paras, _ in files_data)  # Total number of paragraphs
    idx = 0  
    for i, (file_i, paragraphs_i, _) in enumerate(files_data):
        for index_i, para_i in enumerate(paragraphs_i):
            global_idx_i = idx + index_i
            for j in range(i, len(files_data)):
                offset = 0 if i == j else len(files_data[i][1])  # Avoid duplicate comparisons within the same file
                start_idx = idx + offset if j == i else sum(len(files_data[k][1]) for k in range(j))
                file_j, paragraphs_j, _ = files_data[j]
                for index_j, para_j in enumerate(paragraphs_j):
                    global_idx_j = start_idx + index_j
                    if global_idx_i < global_idx_j:
                        sim_score = cos_similarity_matrix[global_idx_i, global_idx_j]
                        if sim_score >= similarity_threshold:
                            print(f"{file_i} (para {index_i+1}) and {file_j} (para {index_j+1}), Similarity Score: {sim_score:.2f}")
        idx += len(paragraphs_i)

if __name__ == '__main__':
    DIRECTORY_PATH = '/path/to/your/directory'
    find_near_duplicates(DIRECTORY_PATH)
```

### What's Changed

1. **Syntax and Typo Corrections**: Corrected lexically incorrect variables and function calls.
2. **Error Handling**: Added error handling for file read operations.
3. **Efficiency and Logic Correction**: Adjusted how the indices for similarity matrix accesses are calculated to avoid redundant comparisons and incorrect ranges.
4. **Readability**: Improved comments and output formatting for better understanding and readability of the output results.

This script should now work more reliably and efficiently, with clearer output and handling of typical file access issues. Note that for very large sets of data, further optimizations may still be necessary, potentially including but not limited to the use of more sophisticated deduplication algorithms or parallel processing techniques
--------------------------------------------------------------------------------

Reviewer: APPROVE
````
