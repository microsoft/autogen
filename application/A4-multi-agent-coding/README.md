# OptiGuide with AutoGen


## The Implementation
This project, OptiGuide with AutoGen, is developed to facilitate interaction with LLM-based agents in scenarios utilizing Gurobi models. 

- [optiguide.py](optiguide.py): Contains the primary implementation of the OptiGuide framework.
- [optiguide_example.ipynb](optiguide_example.ipynb): Demonstrates how to utilize the OptiGuide framework effectively.

**Note:** The `ablation/safeguard_details.txt` and `ablation/single_system_msg.txt` files contain the strings for system messages during the ablation experiment.



## The Ablation Experiment

To conduct the ablation study as described in the paper, execute the `ablation_safeguard.py` file. 


Navigate to the `application/A4-multi-agent-coding/ablation/` directory and run the `ablation_safeguard.py` file by executing the following commands in your terminal:

```bash
cd application/A4-multi-agent-coding/ablation/
ls OAI_CONFIG_LIST # Ensure the presence of the OAI_CONFIG_LIST file.
python ablation_safeguard.py
```

Note: 
- Verify the presence of the `OAI_CONFIG_LIST` file, which should contain your API settings, 
    in the `application/A4-multi-agent-coding/ablation/` directory.
- The final output will be in the [ablation/final.txt](ablation/final.txt) file.

**Some Notes**
The `define_malicious` variable in the code performs another ablation study on should we define what "malicious" means in the system message. When it is True, the system message will be much longer and include the definition of "malicious".
However, when it is True, the actual F-1 score performance is slightly slower, possibly because it is hard to define "malicious" comprehensively in a few paragraphs.

