# %%
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
import dspy
import dspy.evaluate
from dspy.datasets import HotPotQA
import asyncio

# %%
dspy.configure(lm=dspy.LM("openai/gpt-4.1-mini"))


# %%
def search_wikipedia(query: str) -> list[str]:
    results = dspy.ColBERTv2(url="http://20.102.90.50:2017/wiki17_abstracts")(query, k=3)
    return [x["text"] for x in results]


# %%
async def run_agent(task: str, instruction: str) -> str:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
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
        self.instruction = "You are a helpful assistant. Answer the question concisely."

    def forward(self, question: str) -> dspy.Prediction:
        # Use the current instruction (which can be optimized by MIPROv2)
        answer = asyncio.run(run_agent(task=question, instruction=self.instruction))
        return dspy.Prediction(answer=answer)


# %%
# Use small dataset for debugging
trainset = [x.with_inputs("question") for x in HotPotQA(train_seed=2024, train_size=3).train]
agent = Agent()

# Test a single example to debug
print("=== DEBUGGING SINGLE EXAMPLE ===")
example = trainset[0]
print(f"Question: {example.question}")
print(f"Expected answer: {example.answer}")

# Test the agent
prediction = agent.forward(example.question)
print(f"Agent prediction: {prediction}")
print(f"Agent answer: {prediction.answer}")

# Test both metrics
exact_score = dspy.evaluate.answer_exact_match(example, prediction)
lenient_score = lenient_answer_match(example, prediction)
print(f"Exact match score: {exact_score}")
print(f"Lenient match score: {lenient_score}")
print("=" * 50)

# %%
# Try compilation with the lenient metric
print("Starting compilation...")
tp = dspy.MIPROv2(
    metric=lenient_answer_match, auto="light", num_threads=1, max_bootstrapped_demos=1, max_labeled_demos=1
)
optimized_agent = tp.compile(agent, trainset=trainset)

# %%
print(f"Original instruction: {agent.instruction}")
print(f"Optimized instruction: {optimized_agent.instruction}")
