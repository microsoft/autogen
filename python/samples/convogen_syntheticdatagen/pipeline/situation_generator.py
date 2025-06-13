import json
import os
from llm.models.client_builder import OpenAIClientBuilder
from llm.prompt_generator import PromptGenerator
import json
import uuid

class SituationGenerator:
    def __init__(self, config):
        self.config = config
        self.deployment_name = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"] if "deployment_name" not in config else config["deployment_name"]
        try:
            self.aoi_llm = OpenAIClientBuilder(self.deployment_name).get_client()
        except Exception as e:
            raise Exception(f"Error building OpenAI client: {e}")
        self.llm_params = config["llm_params"] if "llm_params" in config else {}
        self.prompt_config_path = config["prompt_config_path"] if "prompt_config_path" in config else "situations-random-shots-1.yaml"
        self.prompt_generator = PromptGenerator(self.prompt_config_path)
        # Use an output path for the situtations to re-use them later as shots based on the config specification
        self.situations_output_path = config["situations_output_path"] if "situations_output_path" in config else None
        self.re_use_situations_as_shots = config["re_use_situations_as_shots"] if "re_use_situations_as_shots" in config else False
        if self.re_use_situations_as_shots or self.situations_output_path:
            self.save_situations = True
        else:
            self.save_situations = False

        
    def _load_prompt_and_params(self, personas=None):
        if personas is None:            
            situations_prompt, params = self.prompt_generator.retrieve_prompt_and_params()
        else:
            situations_prompt, params = self.prompt_generator.retrieve_prompt_and_params_for_personas(personas)
        self.situations_prompt = situations_prompt
        self.params = params

    def _build_chain(self):
        if self.llm_params != {}: # if there are llm params
            self.chain = self.situations_prompt | self.aoi_llm.bind(**self.llm_params)
        else:
            self.chain = self.situations_prompt | self.aoi_llm

    def _fix_json_response(self, response):
        # fix any mistakes in the output that can cause the parsing to fail
        # TODO: currently this relies on the format of the prompt output, it should be more general
        rem_object = response.content.rfind("\"individuals\"")
        trim_index = response.content.rfind("}", 0, rem_object)
        if trim_index != -1 and trim_index < rem_object:
            fixed_response = response.content[:trim_index+1] + "]"
        else:
            fixed_response = response.content
        return fixed_response
    
    def _save_situations(self, output):
        if self.re_use_situations_as_shots:
            self.prompt_generator.save_shots(output)
        else:
            for item in output:
                filename = os.path.join(self.situations_output_path, f"shot-{uuid.uuid4()}.json")
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(item, f, indent=4, ensure_ascii=False)
        
    def generate_situations(self, personas=None):
        # Each time we generate situations, 
        # we need to load the prompt and params and build the chain
        self._load_prompt_and_params(personas)
        # build the chain
        self._build_chain()

        try:
            response = self.chain.invoke(self.params)
            # use to fix any mistakes in the output that can cause the parsing to fail
            try:
                output = json.loads(response.content.strip("```json").strip("```").strip())
            except Exception as e:
                fixed_response = self._fix_json_response(response)
                output = json.loads(fixed_response.strip("```json").strip("```").strip())
            if self.save_situations:
                self._save_situations(output)
            return output
        except Exception as e:
            raise Exception(f"Error generating situations: {e}")

