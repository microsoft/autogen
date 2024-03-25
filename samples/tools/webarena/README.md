# WebArena Benchmark

This directory helps run AutoGen agents on the [WebArena](https://arxiv.org/pdf/2307.13854.pdf) benchmark.

## Installing WebArena

WebArena can be installed by following the instructions from [WebArena's GitHub repository](git@github.com:web-arena-x/webarena.git)

If using WebArena with AutoGen there is a clash on the versions of OpenAI and some code changes are needed in WebArena to be compatible with AutoGen's OpenAI version:

- webarena's openai version is `openai==0.27.0`
- autogen's openai version is: `openai>=1.3`

Prior to installation, in the WebArena codebase, any file containing `openai.error` needs to be replaced with `openai`.

## Running with AutoGen agents

You can use the `run.py` file in the `webarena` directory to run WebArena with AutoGen. The OpenAI (or AzureOpenAI or other model) configuration can be setup via `OAI_CONFIG_LIST`. The config list will be filtered by whatever model is passed in the `--model` argument.

e.g. of running `run.py`:

```
mkdir myresultdir
python run.py --instruction_path agent/prompts/jsons/p_cot_id_actree_2s.json --test_start_idx 27 --test_end_idx 28 --model gpt-4 --result_dir myresultdir
```

The original `run.py` file has been modified to use AutoGen agents which are defined in the `webarena_agents.py` file.

## References
**WebArena: A Realistic Web Environment for Building Autonomous Agents**<br/>
Zhou, Shuyan and Xu, Frank F and Zhu, Hao and Zhou, Xuhui and Lo, Robert and Sridhar, Abishek and Cheng, Xianyi and Bisk, Yonatan and Fried, Daniel and Alon, Uri and others<br/>
[https://arxiv.org/pdf/2307.13854.pdf](https://arxiv.org/pdf/2307.13854.pdf)
