# HumanEval Benchmark

This scenario implements a modified version of the [HumanEval](https://arxiv.org/abs/2107.03374) benchmark.
Compared to the original benchmark, there are **two key differences** here:

- A chat model rather than a completion model is used.
- The agents get pass/fail feedback about their implementations, and can keep trying until they succeed or run out of tokens or turns.

## Running the tasks

```
autogenbench run Tasks/human_eval_two_agents.jsonl
autogenbench tabulate Results/human_eval_two_agents
```

For faster development and iteration, a reduced HumanEval set is available via `Tasks/r_human_eval_two_agents.jsonl`, and contains only 26 problems of varying difficulty.

## References
**Evaluating Large Language Models Trained on Code**<br/>
Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan, Henrique Ponde de Oliveira Pinto, Jared Kaplan, Harri Edwards, Yuri Burda, Nicholas Joseph, Greg Brockman, Alex Ray, Raul Puri, Gretchen Krueger, Michael Petrov, Heidy Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan, Scott Gray, Nick Ryder, Mikhail Pavlov, Alethea Power, Lukasz Kaiser, Mohammad Bavarian, Clemens Winter, Philippe Tillet, Felipe Petroski Such, Dave Cummings, Matthias Plappert, Fotios Chantzis, Elizabeth Barnes, Ariel Herbert-Voss, William Hebgen Guss, Alex Nichol, Alex Paino, Nikolas Tezak, Jie Tang, Igor Babuschkin, Suchir Balaji, Shantanu Jain, William Saunders, Christopher Hesse, Andrew N. Carr, Jan Leike, Josh Achiam, Vedant Misra, Evan Morikawa, Alec Radford, Matthew Knight, Miles Brundage, Mira Murati, Katie Mayer, Peter Welinder, Bob McGrew, Dario Amodei, Sam McCandlish, Ilya Sutskever, Wojciech Zaremba<br/>
[https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374)
