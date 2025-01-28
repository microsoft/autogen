# AssistantBench Benchmark

This scenario implements the [AssistantBench](https://assistantbench.github.io/) agent benchmark. Before you begin, make sure you have followed the instructions in `../README.md` to prepare your environment. We modify the evaluation code from AssistantBench in [Scripts](Scripts) and retain the license  including it here [LICENSE](Scripts/evaluate_utils/LICENSE).  Please find the original AssistantBench evaluation code here [https://huggingface.co/spaces/AssistantBench/leaderboard/tree/main/evaluation](https://huggingface.co/spaces/AssistantBench/leaderboard/tree/main/evaluation).

### Setup Environment Variables for AgBench

Navigate to AssistantBench

```bash
cd benchmarks/AssistantBench
```

Create a file called ENV.json with the following (required) contents (If you're using MagenticOne)

```json
{
    "BING_API_KEY": "REPLACE_WITH_YOUR_BING_API_KEY",
    "HOMEPAGE": "https://www.bing.com/",
    "WEB_SURFER_DEBUG_DIR": "/autogen/debug",
    "CHAT_COMPLETION_KWARGS_JSON": "{\"api_version\": \"2024-02-15-preview\", \"azure_endpoint\": \"YOUR_ENDPOINT/\", \"model_capabilities\": {\"function_calling\": true, \"json_output\": true, \"vision\": true}, \"azure_ad_token_provider\": \"DEFAULT\", \"model\": \"gpt-4o-2024-05-13\"}",
    "CHAT_COMPLETION_PROVIDER": "azure"
}
```

You can also use the openai client by replacing the last two entries in the ENV file by:

- `CHAT_COMPLETION_PROVIDER='openai'`
- `CHAT_COMPLETION_KWARGS_JSON` with the following JSON structure:

```json
{
  "api_key": "REPLACE_WITH_YOUR_API",
  "model": "gpt-4o-2024-05-13"
}
```

Now initialize the tasks.

```bash
python Scripts/init_tasks.py
```

Note: This will attempt to download AssistantBench from Huggingface, but this requires authentication.

After running the script, you should see the new following folders and files:

```
.
./Downloads
./Downloads/AssistantBench
./Downloads/AssistantBench/assistant_bench_v1.0_dev.jsonl
./Downloads/AssistantBench/assistant_bench_v1.0_dev.jsonl
./Tasks
./Tasks/assistant_bench_v1.0_dev.jsonl
./Tasks/assistant_bench_v1.0_dev.jsonl
```

Then run `Scripts/init_tasks.py` again.

Once the script completes, you should now see a folder in your current directory called `Tasks` that contains one JSONL file per template in `Templates`.

### Running AssistantBench

Now to run a specific subset of AssistantBench use:

```bash
agbench run Tasks/assistant_bench_v1.0_dev__MagenticOne.jsonl
```

You should see the command line print the raw logs that shows the agents in action To see a summary of the results (e.g., task completion rates), in a new terminal run the following:

```bash
agbench tabulate Results/assistant_bench_v1.0_dev__MagenticOne
```

## References

Yoran, Ori, Samuel Joseph Amouyal, Chaitanya Malaviya, Ben Bogin, Ofir Press, and Jonathan Berant. "AssistantBench: Can Web Agents Solve Realistic and Time-Consuming Tasks?." arXiv preprint arXiv:2407.15711 (2024). https://arxiv.org/abs/2407.15711
