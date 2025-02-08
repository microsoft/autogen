# HumanEval Benchmark

This scenario implements a modified version of the [HumanEval](https://arxiv.org/abs/2107.03374) benchmark.
Compared to the original benchmark, there are **two key differences** here:

- A chat model rather than a completion model is used.
- The agents get pass/fail feedback about their implementations, and can keep trying until they succeed or run out of tokens or turns.

## Running the tasks


Navigate to HumanEval

```bash
cd benchmarks/HumanEval
```

Update `config.yaml` to point to your model host, as appropriate. The default configuration points to 'gpt-4o'.


Now initialize the tasks.

```bash
python Scripts/init_tasks.py
```

Note: This will attempt to download HumanEval

Then run `Scripts/init_tasks.py` again.

Once the script completes, you should now see a folder in your current directory called `Tasks` that contains one JSONL file per template in `Templates`.

Now to run a specific subset of HumanEval use:

```bash
agbench run Tasks/human_eval_AgentChat.jsonl
```

You should see the command line print the raw logs that shows the agents in action To see a summary of the results (e.g., task completion rates), in a new terminal run the following:

```bash
agbench tabulate Results/human_eval_AgentChat
```


## References

**Evaluating Large Language Models Trained on Code**`<br/>`
Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan, Henrique Ponde de Oliveira Pinto, Jared Kaplan, Harri Edwards, Yuri Burda, Nicholas Joseph, Greg Brockman, Alex Ray, Raul Puri, Gretchen Krueger, Michael Petrov, Heidy Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan, Scott Gray, Nick Ryder, Mikhail Pavlov, Alethea Power, Lukasz Kaiser, Mohammad Bavarian, Clemens Winter, Philippe Tillet, Felipe Petroski Such, Dave Cummings, Matthias Plappert, Fotios Chantzis, Elizabeth Barnes, Ariel Herbert-Voss, William Hebgen Guss, Alex Nichol, Alex Paino, Nikolas Tezak, Jie Tang, Igor Babuschkin, Suchir Balaji, Shantanu Jain, William Saunders, Christopher Hesse, Andrew N. Carr, Jan Leike, Josh Achiam, Vedant Misra, Evan Morikawa, Alec Radford, Matthew Knight, Miles Brundage, Mira Murati, Katie Mayer, Peter Welinder, Bob McGrew, Dario Amodei, Sam McCandlish, Ilya Sutskever, Wojciech Zaremba`<br/>`
[https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374)
