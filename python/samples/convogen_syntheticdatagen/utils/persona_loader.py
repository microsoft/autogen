import json
import pandas as pd
import numpy as np
from unidecode import unidecode
import re

class PersonaLoader:
    def __init__(self, personas_config):
        self.path = personas_config["path"]
        # these are only used if we are sampling groups of personas
        self.min_num_personas_per_group = personas_config.get("min_num_personas_per_group", 2)
        self.max_num_personas_per_group = personas_config.get("max_num_personas_per_group", 5)
        self.sample_group = personas_config.get("sample_group", False)
        self.batch_size = personas_config.get("batch_size", 8)
        self.rewind = personas_config.get("rewind", False)
        self.start_index = personas_config.get("start_index", 0)

        self.personas = []
        self.current_index = 0
        self._load()
    
    def _load_persona_hub(self):
        persona_hub = []
        personas = pd.read_json(self.path, lines=True)
        personas["drop"] = personas["persona"].apply(lambda x: 0 if re.match(r"^[a-z–A-Z0-9’!ğ()&+#\\u0080-\\u00ff/_ \-\"':,.}{]*$", x) else 1)
        personas = personas[personas["drop"] == 0]
        personas["persona"] = personas.apply(lambda row: re.sub(r"[^a-zA-Z0-9_\- ]", " ", unidecode(row["persona"])), axis=1)
        persona_hub = personas["persona"].tolist()
        np.random.shuffle(persona_hub)
        print("Total number of personas: ", len(persona_hub))
        personas = persona_hub
        return personas

    def _load_partner_personas(self):
        with open(self.path, "r", encoding="utf-8") as f:
            personas = json.load(f)
            df = pd.DataFrame(personas)
            df = df[self.start_index:]
            # adding the index id to the persona
            personas = [[f"{str(index)} - "+" ".join(row["persona"]), f"{str(index)} - "+" ".join(row["partner_persona"])] for index, row in df.iterrows()]
            return personas


    def _load(self):
        # if the file extension is jsonl, load the file as jsonl
        if self.path.endswith(".jsonl"):
            self.personas =  self._load_persona_hub()
        elif self.path.endswith(".json"):
            self.personas = self._load_partner_personas()
        else:
            raise ValueError(f"Unsupported file format for personas: {self.path}")
    
    def get_next_personas_batch(self):
        end_signal = False
        if self.sample_group:
            # group the personas
            selected_persona_groups = []
            for i in range(self.batch_size):
                num_personas = np.random.randint(self.min_num_personas_per_group, self.max_num_personas_per_group+1)
                sampled_group = np.random.choice(self.personas, num_personas, replace=False).tolist()
                selected_persona_groups.append(sampled_group)
            
        else:
            start_index = self.current_index
            end_index = min(len(self.personas), self.current_index + self.batch_size)
            print("Start index: ", start_index)
            print("End index: ", end_index)
            self.current_index = end_index % len(self.personas) # reset the index if we reach the end       
            selected_persona_groups =  self.personas[start_index:end_index]
            if not self.rewind:
                if end_index == len(self.personas):
                    end_signal = True # signal the end of the file
        print("Selected persona groups: ", selected_persona_groups)
        return selected_persona_groups, end_signal
        
