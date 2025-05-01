import pandas as pd
import os
import json


class DataFormatter:
    def __init__(self, config, experiment_name, run_name):
        self.config = config
        self.output_path = os.path.join(config["base_output_path"], experiment_name, run_name)
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        self.format = config["format"] if "format" in config else "csv"
        self.format_params = config["format_params"] if "format_params" in config else {}
    
    def _write_csv(self, data, partition_num):
        delimiter = self.format_params.get("delimiter", ",")
        file_extension = "csv"
        if delimiter == "\t":
            file_extension = "tsv"
        output_file = os.path.join(self.output_path, f"part-{partition_num}.{file_extension}")
        if len(data) > 0:
            keys = data[0].keys()
            print(keys)
            with open(output_file, 'w', encoding='utf-8') as tsv_file:
                tsv_file.write('\t'.join(keys) + '\n')
                for obj in data:
                    tsv_file.write(f"{obj['meetingID']}\t{json.dumps(obj['speakerMap'])}\t{json.dumps(obj['Conversation'])}\t{json.dumps(obj['situation_config'])}\n")

    def _write_jsonl(self, data, partition_num):
        output_file = os.path.join(self.output_path, f"part-{partition_num}.jsonl")
        with open(output_file, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    def write_data_in_format(self, data, partition_num):
        if self.format == "csv":
            self._write_csv(data, partition_num)
        elif self.format == "jsonl":
            self._write_jsonl(data, partition_num)
        else:
            raise Exception(f"Unsupported format: {self.format}")