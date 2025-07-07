# %%
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
import dspy
import dspy.evaluate
from dspy.datasets import HotPotQA
import asyncio
import requests
from lxml import html

# %%
dspy.configure(lm=dspy.LM("openai/gpt-4.1-mini"))


# %%
def search_wikipedia(query: str) -> list[str]:
    """Search Wikipedia using the API and return relevant article excerpts"""
    base_url = 'https://en.wikipedia.org/w/api.php'
    
    # First, search for relevant pages
    search_params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': query,
        'srlimit': 3  # Get top 3 results
    }
    
    try:
        search_response = requests.get(base_url, params=search_params).json()
        
        if 'query' not in search_response or 'search' not in search_response['query']:
            return [f"No Wikipedia results found for: {query}"]
        
        results = []
        
        for page in search_response['query']['search']:
            page_title = page['title']
            
            # Get the page content
            content_params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts',
                'exintro': True,  # Only get the intro section
                'explaintext': True,  # Plain text, no HTML
                'exsectionformat': 'plain'
            }
            
            content_response = requests.get(base_url, params=content_params).json()
            
            if 'query' in content_response and 'pages' in content_response['query']:
                for page_id, page_data in content_response['query']['pages'].items():
                    if 'extract' in page_data and page_data['extract']:
                        # Limit extract length to avoid too much text
                        extract = page_data['extract']
                        if len(extract) > 500:
                            extract = extract[:500] + "..."
                        results.append(f"Title: {page_title}\n{extract}")
        
        return results if results else [f"No content found for query: {query}"]
        
    except Exception as e:
        return [f"Error searching Wikipedia: {str(e)}"]


# %%
async def run_agent(task: str, instruction: str) -> str:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-mini")
    agent = AssistantAgent(
        "my_agent",
        model_client=model_client,
        system_message=instruction,
        tools=[search_wikipedia],
        max_tool_iterations=100,
    )
    response = await agent.run(task=task)
    assert isinstance(response.messages[-1], TextMessage), "Expected a TextMessage response"
    await model_client.close()
    return response.messages[-1].content


# %%
# Test the Wikipedia search function
test_query = "Smyrnium plant"
print("Testing Wikipedia search with query:", test_query)
search_results = search_wikipedia(test_query)
for i, result in enumerate(search_results, 1):
    print(f"\n--- Result {i} ---")
    print(result[:200] + "..." if len(result) > 200 else result)

# %%
# Define lenient metric for debugging
def lenient_answer_match(example, pred, trace=None):
    """More lenient matching that handles common variations"""
    if not hasattr(pred, "answer") or not hasattr(example, "answer"):
        print(f"Missing answer attribute - pred: {hasattr(pred, 'answer')}, example: {hasattr(example, 'answer')}")
        return False

    pred_answer = str(pred.answer).lower().strip()
    expected_answer = str(example.answer).lower().strip()

    print(f"Comparing: '{pred_answer}' vs '{expected_answer}'")

    # Exact match
    if pred_answer == expected_answer:
        print("✓ Exact match!")
        return True

    # Check if prediction contains the expected answer
    if expected_answer in pred_answer:
        print("✓ Contains expected answer!")
        return True

    # For yes/no questions, be more flexible
    if expected_answer in ["yes", "no"]:
        if expected_answer in pred_answer:
            print("✓ Yes/No match!")
            return True

    print("✗ No match found")
    return False


# %%
class Agent(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        # Store the instruction as a module parameter that can be optimized
        self.instruction = ""

    def forward(self, question: str) -> dspy.Prediction:
        # Use the current instruction (which can be optimized by MIPROv2)
        answer = asyncio.run(run_agent(task=question, instruction=self.instruction))
        return dspy.Prediction(answer=answer)


# %%
trainset = [x.with_inputs("question") for x in HotPotQA(train_seed=2024, train_size=500).train]
agent = Agent()


# %%
# Try compilation with the lenient metric
print("Starting compilation...")
tp = dspy.MIPROv2(
    metric=lenient_answer_match,
    # metric=dspy.evaluate.answer_exact_match,  # Use exact match for initial compilation
    auto="light",
    num_threads=24,
)
optimized_agent = tp.compile(agent, trainset=trainset)

# %%
print(f"Original instruction: {agent.instruction}")
print(f"Optimized instruction: {optimized_agent.instruction}")
