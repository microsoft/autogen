import os
from dotenv import load_dotenv
# get the current file directory
dir_path = os.path.dirname(os.path.realpath(__file__))
print(dir_path)
envpath = os.path.join(dir_path,'.env')
load_dotenv(envpath)


open_ai_ep = os.getenv('AZURE_OPENAI_ENDPOINT')
os.environ["OPENAI_API_TYPE"] = "azure_ad"
open_ai_api_version = os.environ["AZURE_OPENAI_API_VERSION"]
open_ai_api_deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]