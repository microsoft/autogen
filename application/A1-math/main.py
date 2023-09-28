import os
from pseudo_main import pseudo_main
from autogen import oai
import json
import openai


def main():
    pseudo_main(config_list, use_azure=use_azure)


if __name__ == "__main__":
    config_list = None
    use_azure = False
    if use_azure:
        print("Using Azure")
        with open('azure.json', 'r') as json_file:
            config_list = json.load(json_file)

        config_list = [config_list]
    else:
        config_list = [{
            'model': 'gpt-4',
            'api_key': open("key_openai.txt").read().strip(),
            }]

    oai.retry_timeout = 1200
    main()
