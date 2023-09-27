import sys
import os

from gym.envs.registration import register

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


_AVAILABLE_ENVS = {
    "MiniWoBEnv-v0": {
        "entry_point": "computergym.miniwob.base_env:MiniWoBEnv",
        "discription": "MinoWoB++ environments",
    },
}

for env_id, val in _AVAILABLE_ENVS.items():
    register(id=env_id, entry_point=val.get("entry_point"))
