from azureml.core import Workspace, Experiment, ScriptRunConfig
ws = Workspace.from_config()

compute_target = ws.compute_targets['V100-4']
# compute_target = ws.compute_targets['K80']
command = [
    "pip install torch transformers datasets flaml[blendsearch,ray] && ",
    "python test_electra.py"]

config = ScriptRunConfig(
    source_directory='hf/',
    command=command,
    compute_target=compute_target,
)

exp = Experiment(ws, 'test-electra')
run = exp.submit(config)
print(run.get_portal_url())  # link to ml.azure.com
run.wait_for_completion(show_output=True)
