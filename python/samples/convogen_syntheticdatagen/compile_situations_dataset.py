import pandas as pd
import os
import json
from glob import glob
import argparse
import yaml

from pipeline.data_formatter import DataFormatter
from pipeline.azure_data_uploader import AzureDataUploader


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Data formatter and uploader')
    parser.add_argument('--config', '-c', type=str, help='Path to the yml configuration file', default=os.path.join("configs", "upload-config-1.yaml"))
    args = parser.parse_args()

    # Load the configuration file
    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    experiment_name = config["experiment_name"]
    run_name = config["run_name"]

    format_config = config["formatting"]
    upload_config = config["upload_to_azure"]

    data = []
    # prepare formatting parameters
    base_input_path = format_config["base_input_path"]
    skip_runs = format_config["skip_runs"]
    for root, dirs, files in os.walk(base_input_path):
        for dir in dirs:
            if dir not in skip_runs:
                print(dir)
                run_path = os.path.join(base_input_path, dir)
                for root, dirs, files in os.walk(run_path):
                    for file in files:
                        if file.endswith(".json"):
                            file_path = os.path.join(run_path, file)
                            with open(file_path, "r", encoding="utf-8") as f:
                                data.append(json.load(f))
    
    print(f"Total number of data points: {len(data)}")
            
    # Initialize the data formatter
    data_formatter = DataFormatter(format_config, experiment_name, run_name)

    # Initialize the Azure Data Uploader
    azure_data_uploader = AzureDataUploader(upload_config)

    # Upload the data files
    for i in range(0, len(data), format_config["write_partition_size"]):
        data_partition = data[i:i + format_config["write_partition_size"]]
        data_formatter.write_data_in_format(data_partition, i)
        azure_data_uploader.upload_data_to_azure()