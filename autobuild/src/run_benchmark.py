import autogen
import textwrap
from autogen.agentchat.contrib.agent_builder import AgentBuilder


max_agents = 3

MATH_PROMPT = textwrap.dedent("""We need a group of math experts to solve some math problems. 
Those problems are in the fields of algebra, counting and probability, geometry, intermediate algebra, number theory, pre-algebra, and pre-calculus.
They can use tools or write python code themselves if needed.
For example, here is an algebra problem which agents need to solve:
Let \[f(x) = \left\{
\\begin{array}{cl} ax+3, &\\text{ if }x>2, \\
x-5 &\\text{ if } -2 \le x \le 2, \\
2x-b &\\text{ if } x <-2.
\end{array}
\\right.\]
Find $a+b$ if the piecewise function is continuous.
""")

ML_BENCH_PROMPT = textwrap.dedent("""We need a group of machine learning experts to solve some machine learning problems.
Agents need to solve the problems by leveraging different machine learning frameworks or models like DGL, BERT, PyTorch-GAN, etc.
Their final goal is to write a python command to run the training task with those machine learning frameworks or models.
""")

SCI_BENCH_PROMPT = textwrap.dedent("""We need a group of science experts to solve some scientific problems.
Those problems are in the fields of 
""")