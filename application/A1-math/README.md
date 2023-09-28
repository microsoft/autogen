# A1 Math Evaluation


## Scenario 1:  Autonomous problem-solving
For the quantitative evaluation, we sample 120 level-5 problems from the MATH dataset (20 problem from 6 categories excluding geometry) to test the correctness of these systems. We do not include Auto-GPT in this evaluation since it cannot access results from code executions and doesn't solve any problems in the qualitative evaluation.

**Running Evaluation on 120 math problems**
1. Setup the environment.
```
pip install requirements.txt
touch key_openai.txt
tar -xvf 3000_math_problems.tar.gz
```
2.  If you are using OpenAI, create a `key_openai.txt` and put your key there. If you are using azure AI, put your info in `azure.json`. Change `use_azure=True` in `main.py`.
3. In `pseudo_main.py`, comment out code blocks to run different frameworks. By default it will run AutoGen on 120 problems.
4. Run with `python main.py`.


**Compared Methods**
- **AutoGen AgentChat**: Out-of-box usage of AssitantAgent+UserProxyAgent from AutoGen.
- **LangChain ReAct+Python**: Use the python agent from LangChain. For parsing errors, set `handle_parsing_errors=True` and use the default zero-shot ReAct prompt.
- **ChatGPT+Plugin**: Enabled the Wolfram Alpha plugin (a math computation engine) in the OpenAI web client.
- **ChatGPT+Code Interpreter**: A recent feature in OpenAI web client. Note that these premium features require a paid subscription.
- **Auto-GPT**: The out-of-box Auto-GPT is used. Initialized with the purpose to "solve math problems", resulting in a "MathSolverGPT" with auto-generated goals.

|                | AutoGen | ChatGPT+ Code Interpreter | ChatGPT+ Plugin | Vanilla GPT-4 | Multi-Agent Debate | LangChain ReAct |
|----------------|----------|---------------------------|-----------------|---------------|--------------------|-----------------|
| Correct Count  | **65**   | 58                        | 54              | 36            | 32                 | 28              |

----------
**Qualitative Evaluation**

Each LLM-based system is tested three times on each of the problems. We report the problem solving correctness and summarize the failure reasons in this table.
**Evaluation on the first problem that asks to simplify a square root fraction.**
|                       | Correctness | Failure Reason                                                                                                        |
|-----------------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| AutoGen           | 3/3         | N/A.                                                                                                                  |
| Auto-GPT              | 0/3         | The LLM gives code without the print function so the result is not printed.                                           |
| ChatGPT+Plugin        | 1/3         | The return from Wolfram Alpha contains 2 simplified results, including the correct answer, but GPT-4 always chooses the wrong answer. |
| ChatGPT+Code Interpreter | 2/3      | Returns a wrong decimal result.                                                                                       |
| LangChain ReAct       | 0/3         | LangChain gives 3 different wrong answers.                                                                            |
| Multi-Agent Debate    | 0/3         | It gives 3 different wrong answers due to calculation errors.                                                         |


**Evaluation on the second problem.**
|                       | Correctness | Failure Reason                                                                                                        |
|-----------------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| AutoGen              | 2/3         | The final answer from code execution is wrong.                                                                       |
| Auto-GPT              | 0/3         | The LLM gives code without the print function so the result is not printed.                                           |
| ChatGPT+Plugin        | 1/3         | For one trial, GPT-4 got stuck because it keeps giving wrong queries and has to be stopped. Another trial simply gives a wrong answer. |
| ChatGPT+Code Interpreter | 0/3      | It gives 3 different wrong answers.                                                                                   |
| LangChain ReAct       | 0/3         | LangChain gives 3 different wrong answers.                                                                            |
| Multi-Agent Debate    | 0/3         | It gives 3 different wrong answers.                                                                                   |




## Scenario 2:  Human-in-the-loop Problem-Solving

For the hard problems that these LLM systems cannot solve autonomously, human feedback during the problem solving process can be helpful.
To incorporate human feedback with **AutoGen**, one can set `human\_input\_mode=`ALWAYS'` in the user proxy agent.
We compare such configuration of **AutoGen** with systems that could also incorporate human feedback during the problem solving process, including Auto-GPT, ChatGPT+Plugin, ChatGPT+Code Interpreter.

Trial with AutGen and AutoGPT is in `Eval_with_human Agent+AutoGPT.ipynb`

Trial with ChatGPT+Code Interpreter:
- https://chat.openai.com/share/c1b7cd23-ea7d-456d-8c43-cfe7ce111ef6
- https://chat.openai.com/share/b996bae1-53c0-4a94-96d8-4cdd09174d90
- https://chat.openai.com/share/d0ba8bcd-a132-4997-af30-4019bd7c2067

Trial with ChatGPT+Plugin:
- https://chat.openai.com/share/c96ca7fd-c560-4fa6-ac53-5e730b334c3b
- https://chat.openai.com/share/f062f6bc-a099-461a-8173-f4d0b3a72b20
- https://chat.openai.com/share/22983d99-075f-4dbe-9f2d-7eda8ddac597

## Scenario 3: Problem-Solving with AI and Multiple Human Users

Check out [this notebook](../../notebook/agentchat_two_users.ipynb) for a demo.
