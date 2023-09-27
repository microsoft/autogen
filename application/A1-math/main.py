import os
from pseudo_main import pseudo_main
from flaml.autogen import oai
import json
import openai


def main():
    pseudo_main(config_list, use_azure=use_azure)


if __name__ == "__main__":
    config_list = None
    use_azure = False
    try:
        config_list = [{
            'model': 'gpt-4',
            'api_key': open("key_openai.txt").read().strip(),
            }]
    except Exception:
        use_azure = True
        with open('azure.json', 'r') as json_file:
            config_list = json.load(json_file)

        config_list = [config_list]
    try:
        os.environ["WOLFRAM_ALPHA_APPID"] = open("wolfram.txt").read().strip()
    except Exception:
        print("Warning: Wolfram Alpha API key not found. Ignore this if it is not needed.")
        pass
    oai.retry_timeout = 1200
    main()
