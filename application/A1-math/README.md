# A1 Math Evaluation


## Senario 1
**Frameworks**
- **AutoGen AgentChat**: Out-of-box usage of AssitantAgent+UserProxyAgent from AutoGen. 
- **LangChain ReAct+Python**: Use the python agent from LangChain. For parsing errors, set `handle_parsing_errors=True` and use the default zero-shot ReAct prompt.
- **ChatGPT+Plugin**: Enabled the Wolfram Alpha plugin (a math computation engine) in the OpenAI web client.
- **ChatGPT+Code Interpreter**: A recent feature in OpenAI web client. Note that these premium features require a paid subscription.
- **Auto-GPT**: The out-of-box Auto-GPT is used. Initialized with the purpose to "solve math problems", resulting in a "MathSolverGPT" with auto-generated goals.


Each LLM-based system is tested three times on each of the problems. We report the problem solving correctness and summarize the failure reasons in this table. 
**Evaluation on the first problem that asks to simplify a square root fraction.**
|                       | Correctness | Failure Reason                                                                                                        |
|-----------------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| \libName              | 3/3         | N/A.                                                                                                                  |
| Auto-GPT              | 0/3         | The LLM gives code without the print function so the result is not printed.                                           |
| ChatGPT+Plugin        | 1/3         | The return from Wolfram Alpha contains 2 simplified results, including the correct answer, but GPT-4 always chooses the wrong answer. |
| ChatGPT+Code Interpreter | 2/3      | Returns a wrong decimal result.                                                                                       |
| LangChain ReAct       | 0/3         | LangChain gives 3 different wrong answers.                                                                            |
| Multi-Agent Debate    | 0/3         | It gives 3 different wrong answers due to calculation errors.                                                         |


**Evaluation on the second problem.**
|                       | Correctness | Failure Reason                                                                                                        |
|-----------------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| \libName              | 2/3         | The final answer from code execution is wrong.                                                                       |
| Auto-GPT              | 0/3         | The LLM gives code without the print function so the result is not printed.                                           |
| ChatGPT+Plugin        | 1/3         | For one trial, GPT-4 got stuck because it keeps giving wrong queries and has to be stopped. Another trial simply gives a wrong answer. |
| ChatGPT+Code Interpreter | 0/3      | It gives 3 different wrong answers.                                                                                   |
| LangChain ReAct       | 0/3         | LangChain gives 3 different wrong answers.                                                                            |
| Multi-Agent Debate    | 0/3         | It gives 3 different wrong answers.                                                                                   |



For the quantitative evaluation, we sample 120 level-5 problems from the MATH dataset (20 problem from 6 categories excluding geometry) to test the correctness of these systems. We do not include Auto-GPT in this evaluation since it cannot access results from code executions and doesn't solve any problems in the qualitative evaluation. 
|                | \libName | ChatGPT+ Code Interpreter | ChatGPT+ Plugin | Vanilla GPT-4 | Multi-Agent Debate | LangChain ReAct |
|----------------|----------|---------------------------|-----------------|---------------|--------------------|-----------------|
| Correct Count  | **65**   | 58                        | 54              | 36            | 32                 | 28              |


## Senario 2:

For the hard problems that these LLM systems cannot solve autonomously, human feedback during the problem solving process can be helpful. 
To incorporate human feedback with **AutoGen**, one can set \texttt{human\_input\_mode=`ALWAYS'} in the user proxy agent. 
We compare such configuration of **AutoGen** with systems that could also incorporate human feedback during the problem solving process, including Auto-GPT, ChatGPT+Plugin, ChatGPT+Code Interpreter.

