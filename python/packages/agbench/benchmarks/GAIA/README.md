# GAIA Benchmark

This scenario implements the [GAIA](https://arxiv.org/abs/2311.12983) agent benchmark. Before you begin, make sure you have followed instruction in `../README.md` to prepare your environment.

### Setup Environment Variables for AgBench

Navigate to GAIA

```bash
cd benchmarks/GAIA
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

You might need to add additional packages to the requirements.txt file inside the Templates/MagenticOne folder.

Now initialize the tasks.

```bash
python Scripts/init_tasks.py
```

Note: This will attempt to download GAIA from Hugginface, but this requires authentication.

The resulting folder structure should look like this:

```
.
./Downloads
./Downloads/GAIA
./Downloads/GAIA/2023
./Downloads/GAIA/2023/test
./Downloads/GAIA/2023/validation
./Scripts
./Templates
./Templates/TeamOne
```

Then run `Scripts/init_tasks.py` again.

Once the script completes, you should now see a folder in your current directory called `Tasks` that contains one JSONL file per template in `Templates`.

### Running GAIA

Now to run a specific subset of GAIA use:

```bash
agbench run Tasks/gaia_validation_level_1__MagenticOne.jsonl
```

You should see the command line print the raw logs that shows the agents in action To see a summary of the results (e.g., task completion rates), in a new terminal run the following:

```bash
agbench tabulate Results/gaia_validation_level_1__MagenticOne/
```

## References

**GAIA: a benchmark for General AI Assistants** `<br/>`
Grégoire Mialon, Clémentine Fourrier, Craig Swift, Thomas Wolf, Yann LeCun, Thomas Scialom `<br/>`
[https://arxiv.org/abs/2311.12983](https://arxiv.org/abs/2311.12983)
