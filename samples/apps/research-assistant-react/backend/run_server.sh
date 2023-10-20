
# read the contents of file OAI_CONFIG_LIST and export it to the environment var OAI_CONFIG_LIST
export OAI_CONFIG_LIST=$(cat ./OAI_CONFIG_LIST)
export BING_API_KEY=$(cat ./BING_API_KEY)
uvicorn main:app
