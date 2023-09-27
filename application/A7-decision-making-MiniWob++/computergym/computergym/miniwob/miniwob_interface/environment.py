from typing import Union
import os
import sys
import logging

from .state import MiniWoBState
from .instance import MiniWoBInstance


class MiniWoBEnvironment(object):
    """MiniWoB environment."""

    def __init__(self, subdomain):
        """Creates a new MiniWoBEnvironment with no instances.
        Must call configure() to set up instances.

        Args:
            subdomain (str): MiniWoB task name (e.g., "click-test")
        """
        self.subdomain = subdomain
        self.instances = []
        self.died = False

    @property
    def num_instances(self):
        return len(self.instances)

    def configure(self, num_instances=1, seeds=None, **kwargs):
        """Creates the required number of MiniWoBInstance.

        Args:
            num_instances (int): Number of instances

        kwargs are passed into the constructor of MiniWoBInstance:
            headless (bool): Whether to render GUI
            base_url (str): Base URL, which is usually one of the following
                - http://localhost:8000/     (served by http-serve)
                - file:///path/to/miniwob-plusplus/html/
            cache_state (bool): Whether to cache and return the initial
                state; only make sense if the task interface never changes
            threading (bool): Whether to run the instances in separate threads
            reward_processor (callable; optional): A function that takes
                the metadata and return a reward (see miniwob.reward)
            seeds (list[object]): Random seeds to set for each instance;
                len(seeds) must be equal to num_instances.
            wait_ms (float): Pause the instance after each action for this
                amount of time (in milliseconds).
            block_on_reset (bool): On reset, block until the page loads.
            refresh_freq (int): Every this number of episodes,
                refresh the page at the beginning of the next episode.
                Takes time but cleans up any lingering states and memory leaks.
                *** Must specify `seeds` at each reset call.
            initial_mode (str): Initial data mode (e.g., "train", "test")
        """
        assert seeds is not None, "seeds must be specified"
        assert len(seeds) == num_instances, "len(seeds) must be equal to num_instances"
        self.configure_kwargs = kwargs
        for instance in self.instances:
            instance.close()
        self.instances = []
        for index in range(num_instances):
            logging.info("Starting WebDriver Instance %d", index)
            instance = MiniWoBInstance(index, self.subdomain, seeds[index], **kwargs)
            instance.start()
            self.instances.append(instance)
        for instance in self.instances:
            instance.wait()

    def reset(self, seeds=None, mode=None, record_screenshots=False):
        """Forces stop and start all instances.

        Args:
            seeds (list[object]): Random seeds to set for each instance;
                If specified, len(seeds) must be equal to the number of instances.
                A None entry in the list = do not set a new seed.
            mode (str): If specified, set the data mode to this value before
                starting new episodes.
            record_screenshots (bool): Whether to record screenshots of the states.
        Returns:
            states (list[MiniWoBState])
        """
        # If an instance died, call configure
        if any(instance.died for instance in self.instances):
            logging.warning("An instance died. Reset instance ...")
            self.configure(len(self.instances), seeds, **self.configure_kwargs)
        # Parse arguments
        if seeds is None:
            seeds = [None] * len(self.instances)
        else:
            assert isinstance(seeds, (list, tuple)) and len(seeds) == len(
                self.instances
            )
        if mode is not None:
            self.set_mode(mode)
        self.set_record_screenshots(record_screenshots)
        # The ith entry in `states` will be set by the ith instance
        states = [None] * len(self.instances)
        for i, instance in enumerate(self.instances):
            instance.call(instance.reset, states, seeds[i])
        for instance in self.instances:
            instance.wait()
        self.died = any(instance.died for instance in self.instances)
        return states

    def step(self, actions):
        """Applies an action on each instance and returns the results.

        Args:
            actions (list[MiniWoBAction or None])

        Returns:
            tuple (states, rewards, dones, info)
            states (list[MiniWoBState])
            rewards (list[float])
            dones (list[bool])
            info (dict): additional debug information.
                Global debug information is directly in the root level
                Local information for instance i is in info['n'][i]
        """
        assert len(actions) == len(
            self.instances
        ), "len(action) is {} but there are {} instances".format(
            len(actions), len(self.instances)
        )
        # Initialize with reasonable values
        states: list[Union[None, MiniWoBState]] = [None] * len(self.instances)
        rewards = [-1.0] * len(self.instances)
        dones = [True] * len(self.instances)
        info = {"n": [{} for _ in self.instances]}
        # Have the instances replace the values
        for i, instance in enumerate(self.instances):
            instance.call(instance.step, actions[i], states, rewards, dones, info["n"])
        for instance in self.instances:
            instance.wait()
        self.died = any(instance.died for instance in self.instances)
        return states, rewards, dones, info

    def set_mode(self, mode):
        """Set the data mode ("train", "test", etc.) of all instances.
        Will have effect starting from the next episode.

        Args:
            mode (str)
        """
        for instance in self.instances:
            instance.mode = mode

    def set_record_screenshots(self, record_screenshots):
        """Adjust whether the record the screenshots of the states.

        Args:
            record_screenshots (bool)
        """
        for instance in self.instances:
            instance.record_screenshots = record_screenshots

    def visualize_attention(self, attentions):
        """Sends the attention weights to be visualized.

        Args:
            attentions (list[*]): attention weight for each instance.
                Each list element is one of:
                - None: Do not do anything
                - np.array or 2d list of shape (num_grid_rows, num_grid_cols)
                - np.array or 2d list of shape (0, 0): Clear the visualization
        """
        for i, instance in enumerate(self.instances):
            instance.call(instance.visualize_attention, attentions[i])
        for instance in self.instances:
            instance.wait()

    def close(self):
        for instance in self.instances:
            instance.call(instance.close)
        for instance in self.instances:
            instance.wait()


def test_environment():
    try:
        task_name = sys.argv[1]
    except IndexError:
        print("Usage: python {} TASK_NAME".format(sys.argv[0]))
        exit(1)
    env = MiniWoBEnvironment(task_name)
    base_url = os.environ.get("MINIWOB_BASE_URL")
    env.configure(num_instances=1, seeds=[0], base_url=base_url)
    states = env.reset()
    print(states[0].dom.visualize())
    env.close()


if __name__ == "__main__":
    test_environment()
