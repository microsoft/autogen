# MATH Benchmark

This scenario implements the [MATH](https://arxiv.org/abs/2103.03874) benchmark.

## Running the tasks

```
autogenbench run Tasks/math_two_agents.jsonl
autogenbench tabulate Results/math_two_agents
```

By default, only a small subset (17 of 5000) MATH problems are exposed. Edit `Scripts/init_tasks.py` to expose more tasks.

*Note*: Scoring is done by prompting the LLM (ideally GPT-4) with both the proposed answer and the ground truth answer, and asking the LLM to grade itself.

## References
**Measuring Mathematical Problem Solving With the MATH Dataset**<br/>
Dan Hendrycks, Collin Burns, Saurav Kadavath, Akul Arora, Steven Basart, Eric Tang, Dawn Song, Jacob Steinhardt<br/>
[https://arxiv.org/abs/2103.03874](https://arxiv.org/abs/2103.03874)
