import re
import yaml
import numpy as np
import json
import os
import uuid
import pandas as pd

from langchain_core.prompts import PromptTemplate

class PromptGenerator:
    
    def __init__(self, config_name):
        config_path = os.path.join(os.path.realpath(os.path.dirname(__file__)), "promptConfigs", config_name)
        self.config_path = config_path
        with open(self.config_path, 'r') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        print(self.config['main_prompt']['path'])
        self.main_prompt = self._read_md(os.path.realpath(self.config['main_prompt']['path'])) if self.config['main_prompt']['path'] else ''
        self.additional_sections = self.config.get("additional_sections",[])



    def _read_md(self, file):
        with open(file, 'r') as f:
            return f.read()
  
    def _parse_item(self, key, item):
        if key == "shots":
            self.shots_base_path = os.path.realpath(item['path'])
            return self._load_shots(item)
        else:
            return item
        
    def _load_shots(self,item):        
        method = item['method'].lower()
        assert method in ['random', 'fixed'], "[PromptGenerationError] Method should be one of the following: ['random', 'fixed'], Revisit the config file."
        params = item['method_params']

        shots = [] 
        if method == "random": # pick random shots
            assert 'num_shots' in params, "[PromptGenerationError] num_shots should be in the method_params, Revisit the config file."
            
            shot_files = [ file for file in os.listdir(self.shots_base_path) if file.endswith('.json')]
            num_shots = min(params['num_shots'], len(shot_files))
            selected_shots = np.random.choice(shot_files, size=num_shots, replace=False).tolist()
            print("Selected shots: ", selected_shots)

        elif method == "fixed":
            assert 'shot_names' in params, "[PromptGenerationError] shot_names should be in the method_params, Revisit the config file."
            selected_shots = params['shot_names']

        for shot_name in selected_shots:
            with open(os.path.join(self.shots_base_path, shot_name), "r", encoding="utf-8") as f:
                shot = json.load(f)
                shots.append(shot)
        
        shot_type = params.get('shot_type', 'text')
        if shot_type == 'text':
            shots = "\n\n".join(shots) if shots != [] else ''
        elif shot_type == 'json':
            shots = json.dumps(shots).replace("{","{{").replace("}","}}") if shots != [] else ''
        else:
            shots = "\n\n".join(shots) if shots != [] else ''
        
        return shots


    def load_formatted_prompt(self):
        # load dynamic parts from the prompt
        
        params = {}
        for key,item in self.additional_sections.items():
            params[key] = self._parse_item(key, item)

        prompt = PromptTemplate.from_template(self.main_prompt)
        prompt = prompt.format(**params)
        return prompt
    
    def retrieve_prompt_and_params(self):
        params = {}
        for key,item in self.additional_sections.items():
            params[key] = self._parse_item(key, item)

        prompt = PromptTemplate.from_template(self.main_prompt)
        return prompt, params
    
    def retrieve_prompt_and_params_for_personas(self, personas):
        params = {}
        params["personas"] = personas
        for key,item in self.additional_sections.items():
            if key != "personas":
                params[key] = self._parse_item(key, item)

        prompt = PromptTemplate.from_template(self.main_prompt)
        return prompt, params
    
    def save_shots(self, output):
        for item in output:
            filename = os.path.join(self.shots_base_path, f"shot-{uuid.uuid4()}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(item, f, indent=4, ensure_ascii=False)