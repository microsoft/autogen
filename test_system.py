import os
import json
from protein_drug_discovery.main import main as run_main

def run_test():
    # Create a dummy config.json file
    config = {
        "llm_provider": "openai",
        "llm_config": {
            "model": "gpt-3.5-turbo",
            "api_key": os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
        }
    }
    with open("protein_drug_discovery/config.json", "w") as f:
        json.dump(config, f)

    # Run the main script
    try:
        test_args = {
            "disease": "Alzheimer's",
            "n": 3,
            "start_year": 2020,
            "end_year": 2023,
        }
        run_main(test_args)
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Clean up the dummy config file
        os.remove("protein_drug_discovery/config.json")

if __name__ == "__main__":
    run_test()
