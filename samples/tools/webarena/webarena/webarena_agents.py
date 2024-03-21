import autogen

from browser_env.actions import (
    ActionParsingError,
    Action,
    create_none_action,
    create_id_based_action,
    create_playwright_action,
)

from browser_env import (
    ActionTypes,
    StateInfo,
    Trajectory,
    create_stop_action,
)

from browser_env.helper_functions import (
    RenderHelper,
    get_action_description,
)

from browser_env.actions import is_equivalent


def early_stop(
    trajectory: Trajectory, max_steps: int, thresholds: dict[str, int]
) -> tuple[bool, str]:
    """Check whether need to early stop"""

    # reach the max step
    num_steps = (len(trajectory) - 1) / 2
    if num_steps >= max_steps:
        return True, f"Reach max steps {max_steps}"

    last_k_actions: list[Action]
    action_seq: list[Action]

    # Case: parsing failure for k times
    k = thresholds["parsing_failure"]
    last_k_actions = trajectory[1::2][-k:]  # type: ignore[assignment]
    if len(last_k_actions) >= k:
        if all(
            [action["action_type"] == ActionTypes.NONE for action in last_k_actions]
        ):
            return True, f"Failed to parse actions for {k} times"

    # Case: same action for k times
    k = thresholds["repeating_action"]
    last_k_actions = trajectory[1::2][-k:]  # type: ignore[assignment]
    action_seq = trajectory[1::2]  # type: ignore[assignment]

    if len(action_seq) == 0:
        return False, ""

    last_action: Action = action_seq[-1]

    if last_action["action_type"] != ActionTypes.TYPE:
        if len(last_k_actions) >= k:
            if all([is_equivalent(action, last_action) for action in last_k_actions]):
                return True, f"Same action for {k} times"

    else:
        # check the action sequence
        if sum([is_equivalent(action, last_action) for action in action_seq]) >= k:
            return True, f"Same typing action for {k} times"

    return False, ""


class EnvironmentAgent(autogen.ConversableAgent):
    def __init__(
        self,
        env,
        config_file,
        result_dir,
        action_set_tag,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.env = env
        self.trajectory: Trajectory = []
        obs, info = env.reset(options={"config_file": config_file})
        self.state_info: StateInfo = {"observation": obs, "info": info}
        self.trajectory.append(self.state_info)
        self.meta_data = {"action_history": ["None"]}
        self.action_set_tag = action_set_tag
        self.render_helper = RenderHelper(config_file, result_dir, action_set_tag)
        self.register_reply(
            [autogen.Agent, None], EnvironmentAgent.generate_env_reply, position=1
        )
        self.register_hook(
            hookable_method="process_message_before_send",
            hook=self.process_message_before_send,
        )

    def process_message_before_send(self, sender, message, recipient, silent):
        if "context" in message:
            raise ValueError("Message should not contain context freom generate_reply")

        message["context"] = {
            "trajectory": self.trajectory,
            "meta_data": self.meta_data,
            "state_info": self.state_info,
        }

        if "intent" in message["content"]:
            intent = message["content"]["intent"]
            obs = self.state_info["observation"]["text"]
            message["content"] = f"{obs} \n\n {intent}"
            message["context"]["intent"] = intent
        return message

    def generate_env_reply(
        self,
        messages=None,
        sender=None,
        config=None,
    ):
        if messages is None:
            messages = self.chat_messages[sender]

        action = messages[-1]["context"]
        action_str = messages[-1]["content"]
        self.trajectory.append(action)

        self.render_helper.render(action, self.state_info, self.meta_data, True)
        self.meta_data["action_history"].append(action_str)

        if action["action_type"] == ActionTypes.STOP:
            return True, {"content": "TERMINATE"}

        obs, _, terminated, _, info = self.env.step(action)
        self.state_info = {"observation": obs, "info": info}
        self.trajectory.append(self.state_info)

        if terminated:
            self.trajectory.append(create_stop_action(""))
            return True, "TERMINATE"

        return True, {"content": obs["text"]}


class ActionTakingCapability:
    def __init__(
        self, prompt_constructor, action_set_tag, max_steps, early_stop_thresholds
    ):
        self.action_set_tag = action_set_tag
        self.prompt_constructor = prompt_constructor
        self.max_steps = max_steps
        self.early_stop_thresholds = early_stop_thresholds

    def add_to_agent(self, agent):
        agent.register_hook(
            hookable_method="process_all_messages_before_reply",
            hook=self.process_all_messages_before_reply,
        )
        agent.register_hook(
            hookable_method="process_message_before_send",
            hook=self.process_message_before_send,
        )

    def process_all_messages_before_reply(self, messages):
        if "context" in messages[-1]:
            m = messages[-1]["context"]
            trajectory = m["trajectory"]
            meta_data = m["meta_data"]
            intent = messages[0]["context"]["intent"]
        else:
            if "TERMINATE" in messages[-1]["content"]:
                return messages

        # take action
        prompt = self.prompt_constructor.construct(trajectory, intent, meta_data)
        return prompt

    def process_message_before_send(self, sender, message, recipient, silent):
        force_prefix = self.prompt_constructor.instruction["meta_data"].get(
            "force_prefix", ""
        )
        response = f"{force_prefix}{message}"
        try:
            parsed_response = self.prompt_constructor.extract_action(response)
            if self.action_set_tag == "id_accessibility_tree":
                action = create_id_based_action(parsed_response)
            elif self.action_set_tag == "playwright":
                action = create_playwright_action(parsed_response)
            else:
                action = create_stop_action(f"ERROR: {str(e)}")
        except ActionParsingError as e:
            action = create_none_action()
            action["raw_prediction"] = response
        except Exception as e:
            action = create_stop_action(f"ERROR: {str(e)}")
            action["raw_prediction"] = response

        messages = sender.chat_messages[recipient]
        if "context" in messages[-1]:
            m = messages[-1]["context"]
            state_info = m["state_info"]
            trajectory = m["trajectory"]
            early_stop_flag, stop_info = early_stop(
                trajectory, self.max_steps, self.early_stop_thresholds
            )

            if early_stop_flag:
                action = create_stop_action(f"Early stop: {stop_info}")

            action_str = get_action_description(
                action,
                state_info["info"]["observation_metadata"],
                action_set_tag=self.action_set_tag,
                prompt_constructor=self.prompt_constructor,
            )
            return {"content": action_str, "context": action}
        return {"content": "", "context": action}
