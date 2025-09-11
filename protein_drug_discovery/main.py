import argparse
import os
import time
import logging
import json
from protein_drug_discovery.orchestrator import Orchestrator
from protein_drug_discovery.utils import setup_logging, LLMUsageTracker
from dotenv import load_dotenv
from autogen_core import EVENT_LOGGER_NAME

load_dotenv()

def main(args):
    start_time = time.time()
    setup_logging()

    try:
        with open("protein_drug_discovery/config.json") as f:
            config = json.load(f)
            llm_config = config.get("llm_config")
            if llm_config is None:
                raise ValueError("LLM configuration not found in config.json")
            if llm_config.get("api_key") == "YOUR_OPENAI_API_KEY":
                raise ValueError("Please replace YOUR_OPENAI_API_KEY with your actual API key in config.json")
    except FileNotFoundError:
        raise FileNotFoundError("config.json not found. Please create a config.json file from the template.")

    # Set up the logging configuration to use the custom handler
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    llm_usage = LLMUsageTracker()
    logger.handlers = [llm_usage]

    orchestrator = Orchestrator(llm_config)
    orchestrator.run(args['n'], args['disease'], args['start_year'], args['end_year'])

    end_time = time.time()
    runtime = end_time - start_time

    logging.info(f"Total runtime: {runtime:.2f} seconds")
    logging.info(f"Total tokens used: {llm_usage.total_tokens}")
    logging.info(f"Prompt tokens: {llm_usage.prompt_tokens}")
    logging.info(f"Completion tokens: {llm_usage.completion_tokens}")
    logging.info(f"Total cost: ${llm_usage.total_cost:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Protein Drug Discovery Agent System")
    parser.add_argument("--n", type=int, default=5, help="Number of top protein targets to return")
    parser.add_argument("--disease", type=str, required=True, help="Disease of interest")
    parser.add_argument("--start_year", type=int, default=2010, help="Start year for the search")
    parser.add_argument("--end_year", type=int, default=2024, help="End year for the search")
    cli_args = parser.parse_args()
    main(vars(cli_args))
