import json
import os
import argparse
import uuid
import yaml

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from pipeline.group_chat_builder import GroupChatBuilder
from pipeline.situation_generator import SituationGenerator
from pipeline.data_formatter import DataFormatter
from pipeline.azure_data_uploader import AzureDataUploader

from utils.persona_loader import PersonaLoader

import time

from azure.identity import DefaultAzureCredential


# Retrieve the Azure Credential
# credential = DefaultAzureCredential()
# token =  credential.get_token("https://cognitiveservices.azure.com/.default").token


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Group Chat Generation')
    parser.add_argument('--config', '-c', type=str, help='Path to the yml configuration file', default=os.path.join("configs", "gen-config-1.yaml"))
    args = parser.parse_args()

    # Load the configuration file
    generation_config = yaml.safe_load(open(args.config, encoding="utf-8"))

    if "experiment_name" not in generation_config:
        experiment_name = "Default"
    else:
        experiment_name = generation_config["experiment_name"]
    print(f"Starting the group chat generation for experiment: {experiment_name}")

    if "run_name" not in generation_config:
        run_name = f"run-{uuid.uuid4()}"
    else:
        run_name = generation_config["run_name"]

    # Retrieve the number of conversations to generate
    num_conversations = generation_config.get("num_conversations", 1)
    # number of processes to run in parallel
    num_processes = generation_config.get("num_processes", 1)
    # number of threads to run in parallel per process
    num_threads = generation_config.get("num_threads", 1)
    # The size of each data partition
    write_partition_size = generation_config.get("write_partition_size", 1)
    
    generated_conversation_count = 0
    generated_conversations = []
    part_num = 0

    retrying = False

    persona_loader = None
    use_personas = False

    # read the personas dataset
    if "Situation_generation" in generation_config:
        situation_generation_config = generation_config["Situation_generation"]
        situation_generator = SituationGenerator(situation_generation_config)
        if "personas" in situation_generation_config:
            use_personas = True
            personas_config = situation_generation_config["personas"]
            persona_loader = PersonaLoader(personas_config)

    else:
        raise ValueError("Situation generation configuration is missing in the generation config file")

    end_signal = False

    while generated_conversation_count < num_conversations and not end_signal:
        try:
            # Each process will generate a batch of conversations
            # Step 1: Generate the situations
            # if "Situation_generation" in generation_config:
            #     situation_generation_config = generation_config["Situation_generation"]
            #     # Generate the situations
            #     situation_generator = SituationGenerator(situation_generation_config)
            situations = []
            if not retrying:
                if use_personas:
                    personas, end_signal = persona_loader.get_next_personas_batch()
                    situations = situation_generator.generate_situations(personas)
                else:
                    situations = situation_generator.generate_situations()
                print("Total number of generated situations: ", len(situations))
            else:
                retrying = False
                print("Re-using the previously generated situations: ", len(situations))
            # else:
            #     raise ValueError("Situation generation configuration is missing in the generation config file")
            
            # Step 2: Generate the group chat for each situation using threads
            if "Group_chat_generation" in generation_config:
                group_chat_generation_config = generation_config["Group_chat_generation"]
                threads = []
                results = []
                futures = []

                if len(situations) == 0:
                    print("No situations generated. Generate situations first. Retrying...")
                    continue
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    for i in range(len(situations)):
                        group_chat_builder = GroupChatBuilder(situations[i], experiment_name, run_name, **group_chat_generation_config)                    
                        future = executor.submit(group_chat_builder.start_conversation, save_output=True)
                        futures.append(future)  

                            
                    
                print("Submitted all the group chat generation tasks")
                for future in futures:
                    results.append(future.result())
                # filter the results to remove the None values
                unprocessed_situations = []
                remaining_results =[]

                for i, result in enumerate(results):
                    if result is not None:
                        remaining_results.append(result)
                    else:
                        unprocessed_situations.append(situations[i])

                results = remaining_results
                situations = unprocessed_situations

                if len(results) == 0:
                    print("No group chats generated. Retrying...")
                    retrying = True
                    # print("Refreshing the token..")
                    # token =  credential.get_token("https://cognitiveservices.azure.com/.default").token
                    # print(token)
                else:
                    # we got some results but not for all the situations so we still need to refreshh the tokens
                    if len(results) < len(situations):
                        print("Some group chats were not generated. Retrying...")
                        retrying = True
                        print("Refreshing the token..")
                        # token =  credential.get_token("https://cognitiveservices.azure.com/.default").token
                        # print(token)
                    else:
                        print("Completed all the group chat generation tasks")

                    print("Total number of generated group chats: ", len(results))
                    generated_conversation_count += len(results)
                    generated_conversations.extend(results)

                    # Step 4: Put all the json files in the required format
                    if len(generated_conversations) >= write_partition_size or generated_conversation_count >= num_conversations:
                        if "formatting" in generation_config:
                            formatting_config = generation_config["formatting"]
                            # Format the data
                            data_formatter = DataFormatter(formatting_config, experiment_name, run_name)
                            formatted_data = data_formatter.write_data_in_format(generated_conversations, part_num)
                            part_num += 1
                    

                        # reset the array and write the data to the Azure Blob
                        generated_conversations = []
                    
                        # Write the data to the Azure Blob
                        if "upload_to_azure" in generation_config:
                            azure_upload_config = generation_config["upload_to_azure"]
                            # Upload the data to Azure Blob for further steps
                            azure_data_uploader = AzureDataUploader(azure_upload_config)
                            azure_data_uploader.upload_data_to_azure()
        except Exception as e:
            print("Error in generating the group chat. Throttling and retrying...")
            print(e)
            retrying = True
            # print("Refreshing the token..")
            # token =  credential.get_token("https://cognitiveservices.azure.com/.default").token
            # print(token)
            # Sleep for 10 seconds
            time.sleep(10)
            continue
            
