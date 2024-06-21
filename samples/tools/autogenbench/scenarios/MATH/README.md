# MATH Benchmark

This scenario implements the [MATH](https://arxiv.org/abs/2103.03874) benchmark.

## Running the tasks

```
autogenbench run Tasks/math_two_agents.jsonl
autogenbench tabulate Results/math_two_agents
```

By default, only a small subset (17 of 5000) MATH problems are exposed. Edit `Scripts/init_tasks.py` to expose more tasks.

## Note on automated evaluation
In this scenario, we adopted an automated evaluation pipeline (from [AutoGen](https://arxiv.org/abs/2308.08155) evaluation) that uses LLM to compare the results. Thus, the metric above is only an estimation of the agent's performance on math problems. We also find a similar practice of using LLM as judger for MATH dataset from the [Cumulative Reasoning](https://arxiv.org/abs/2308.04371) paper ([code](https://github.com/iiis-ai/cumulative-reasoning/blob/main/MATH/math-cr-4shot.py)).

The static checking from MATH dataset requires an exact match ('comparing 2.0 and 2 results in False'). We haven't found an established way that accurately compares the answer, so human involvement is still needed to confirm the result. In AutoGen, the conversation will end at “TERMINATE” by default. To enable an automated way of answer extraction and evaluation, we prompt an LLM with 1. the given problem 2. the ground truth answer 3. the last response from the solver, to extract the answer and compare it with the ground truth answer.

We evaluate the 17 problems for 3 times and go through these problems manually to check the answers. Compared with the automated result evaluation (the model is gpt-4-0613), we find that in 2/3 trials, the automated evaluation determined 1 correct answer as wrong (False Negative). This means 49/51 problems are evaluated correctly. We also went through 200 random sampled problems from whole dataset to check the results.
There are 1 False Negative and 2 False Positives.

We note that False Positive is also possible due to the hallucination of LLMs, and the variety of problems.

## References
**Measuring Mathematical Problem Solving With the MATH Dataset**<br/>
Dan Hendrycks, Collin Burns, Saurav Kadavath, Akul Arora, Steven Basart, Eric Tang, Dawn Song, Jacob Steinhardt<br/>
[https://arxiv.org/abs/2103.03874](https://arxiv.org/abs/2103.03874)

**AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation**<br/>
Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Shaokun Zhang, Erkang Zhu, Beibin Li, Li Jiang, Xiaoyun Zhang and Chi Wang<br/>
[https://arxiv.org/abs/2308.08155](https://arxiv.org/abs/2308.08155)

**Cumulative Reasoning with Large Language Models**<br/>
Yifan Zhang, Jingqin Yang, Yang Yuan, Andrew Chi-Chih Yao<br/>
[https://arxiv.org/abs/2308.04371](https://arxiv.org/abs/2308.04371)
