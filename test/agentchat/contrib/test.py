import os
import openai

openai.api_type = "azure"
openai.api_base = "https://synapseml-openai.openai.azure.com/"
openai.api_version = "2023-07-01-preview"
openai.api_key = "0e6ea67454dd4b76b4d0528c448fe633"

response = openai.ChatCompletion.create(
    engine="gpt-35-turbo",
    messages=[{"role": "system", "content": "You are an AI assistant that helps people find information."}],
    temperature=0.7,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
)

print(response.choices[0])
