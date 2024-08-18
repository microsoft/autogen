import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from openai import BadRequestError
from sweagent.agent.agents import AgentConfig
from sweagent.agent.parsing import FormatError

import autogen
from autogen.agentchat import Agent, UserProxyAgent


class SweUserProxy(UserProxyAgent):
    DEFAULT_REPLY = ""

    def __init__(
        self,
        setup_args,
        env,
        config_path,
        name: Optional[str] = "SweUserProxy",
        human_input_mode: Optional[str] = "NEVER",
        default_auto_reply: Optional[Union[str, Dict, None]] = DEFAULT_REPLY,
        **kwargs,
    ):
        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            default_auto_reply=default_auto_reply,
            **kwargs,
        )

        config = AgentConfig.load_yaml(config_path)
        object.__setattr__(self, "config", config)
        self.system_msg = None
        self.system_args = {
            "command_docs": self.config.command_docs,
            **self.config.env_variables,
        }

        self._parse_command_patterns()

        self.answer = None
        self.last_container_id = None
        self.done = False
        self.format_fails = 0
        self.blocklist_fails = 0

        assert env.container_obj is not None
        assert env.record is not None
        assert self.config is not None
        assert self.config is not None

        if env.container_obj.id != self.last_container_id:
            print(f"Initializing agent settings for container {env.container_obj.id}")
            self._init_environment_vars(env)
            self.last_container_id = env.container_obj.id
        self._setup(setup_args, None)
        self.env = env
        self.register_reply(trigger=autogen.Agent, reply_func=SweUserProxy.generate_evaluation_reply, position=4)

    @property
    def state_command(self) -> str:
        """Return the bash command that will be used to extract the environment state."""
        return self.config.state_command.name

    def _setup(self, instance_args, init_model_stats=None) -> None:
        """Setup the agent for a new instance."""

        assert self.config is not None
        self.instance_args = instance_args
        self.system_msg = self.config.system_template.format(**self.system_args)

    def _init_environment_vars(self, env):
        self._set_environment_vars(env, self.config.env_variables)

    def _set_environment_vars(self, env, env_variables):
        assert self.config is not None  # mypy
        commands_to_execute = (
            [self.config.state_command.code]
            +
            # [code for code in self.config.util_functions] +
            # [command.code for command in self.config._commands] +
            [f"{k}={v}" for k, v in env_variables.items()]
        )
        commands = "\n".join(commands_to_execute)
        try:
            output = env.communicate(commands)
            if env.returncode != 0:
                raise RuntimeError(f"Nonzero return code: {env.returncode}\nOutput: {output}")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("Failed to set environment variables")
            raise e
        command_files = list()
        for file in self.config.command_files:
            datum = dict()
            contents = open(file, "r").read()
            datum["contents"] = contents
            filename = Path(file).name
            if not contents.strip().startswith("#!"):
                if filename.endswith(".sh"):
                    # files are sourced, so they are not executable
                    datum["name"] = Path(file).name
                    datum["type"] = "source_file"
                elif filename.startswith("_"):
                    # files are sourced, so they are not executable
                    datum["name"] = Path(file).name
                    datum["type"] = "utility"
                else:
                    raise ValueError(
                        (
                            f"Non-shell script file {file} does not start with shebang.\n"
                            "Either add a shebang (#!) or change the file extension to .sh if you want to source it.\n"
                            "You can override this behavior by adding an underscore to the file name (e.g. _utils.py)."
                        )
                    )
            else:
                # scripts are made executable
                datum["name"] = Path(file).name.rsplit(".", 1)[0]
                datum["type"] = "script"
            command_files.append(datum)
        env.add_commands(command_files)

    def _guard_multiline_input(self, action: str) -> str:
        parsed_action = list()
        rem_action = action
        while rem_action.strip():
            first_match = self._get_first_match(rem_action, "multi_line_no_subroutines")
            if first_match:
                pre_action = rem_action[: first_match.start()]
                match_action = rem_action[first_match.start() : first_match.end()]
                rem_action = rem_action[first_match.end() :]
                if pre_action.strip():
                    parsed_action.append(pre_action)
                if match_action.strip():
                    eof = first_match.group(3).strip()
                    if not match_action.split("\n")[0].strip().endswith(f"<< '{eof}'"):
                        guarded_command = match_action[first_match.start() :]
                        first_line = guarded_command.split("\n")[0]
                        guarded_command = guarded_command.replace(first_line, first_line + f" << '{eof}'", 1)
                        parsed_action.append(guarded_command)
                    else:
                        parsed_action.append(match_action)
            else:
                parsed_action.append(rem_action)
                rem_action = ""
        return "\n".join(parsed_action)

    def _parse_command_patterns(self):
        assert self.config is not None  # mypy
        self.command_patterns = dict()
        for command in self.config._commands:
            if command.end_name is not None:
                pat = re.compile(
                    rf"^\s*({command.name})\s*(.*?)^({command.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                self.command_patterns[command.name] = pat
            else:
                pat = re.compile(rf"^\s*({command.name})\s*(.*?)$", re.MULTILINE)
                self.command_patterns[command.name] = pat
        self.subroutine_patterns = dict()
        for _, subroutine in self.config._subroutines.items():
            if subroutine.end_name is None:
                pat = re.compile(rf"^\s*({subroutine.name})\s*(.*?)$", re.MULTILINE)
                self.subroutine_patterns[subroutine.name,] = pat
            else:
                pat = re.compile(
                    rf"^\s*({subroutine.name})\s*(.*?)^({subroutine.end_name})\s*$",
                    re.DOTALL | re.MULTILINE,
                )
                self.subroutine_patterns[subroutine.name] = pat
        if hasattr(self.config, "submit_command_end_name"):
            submit_pat = re.compile(
                rf"^\s*({self.config.submit_command})\s*(.*?)^({self.config.submit_command_end_name})\s*$",
                re.DOTALL | re.MULTILINE,
            )
        else:
            submit_pat = re.compile(rf"^\s*({self.config.submit_command})(\s*)$", re.MULTILINE)  # group 2 is nothing
        self.subroutine_patterns[self.config.submit_command] = submit_pat
        self.command_patterns[self.config.submit_command] = submit_pat

    def _get_first_match(self, action: str, pattern_type: str) -> Optional[re.Match]:  # TODO: check
        """Return the first match of a command pattern in the action string."""
        assert self.config is not None  # mypy
        if pattern_type == "subroutine":
            patterns = {k: v for k, v in self.subroutine_patterns.items()}
        elif pattern_type == "multi_line":
            patterns = {
                k: v
                for k, v in self.command_patterns.items()
                if k in self.config.multi_line_command_endings or k == self.config.submit_command
            }
            patterns += {
                k: v for k, v in self.subroutine_patterns.items() if k in self.config.multi_line_command_endings
            }
        elif pattern_type == "multi_line_no_subroutines":
            patterns = {k: v for k, v in self.command_patterns.items() if k in self.config.multi_line_command_endings}
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
        matches = list()
        for name, pat in patterns.items():
            match = pat.search(action)
            if match:
                matches.append(match)
        if len(matches) == 0:
            return None
        matches = sorted(matches, key=lambda x: x.start())
        return matches[0]

    def _initial_text(self, observation: str, state: str) -> str:

        assert self.config is not None  # mypy
        state_vars = json.loads(state)
        templates = [self.config.instance_template]
        if self.config.strategy_template is not None:
            templates.append(self.config.strategy_template)

        messages = []
        for template in templates:
            messages.append(
                template.format(
                    **self.instance_args,
                    **self.system_args,
                    **state_vars,
                    observation=(observation if observation is not None else ""),
                )
            )
        message = "\n".join(messages)
        return message

    def _reply_text(self, observation: str, available_actions: list[str], state: str) -> str:

        assert self.config is not None  # mypy
        state_vars = json.loads(state)
        templates: List[str] = []

        if observation is None or observation.strip() == "":
            # Show no output template if observation content was empty
            templates = [self.config.next_step_no_output_template]
        else:
            # Show standard output template if there is observation content
            templates = [self.config.next_step_template]

        messages = []
        for template in templates:
            messages.append(
                template.format(
                    **self.instance_args,
                    **self.system_args,
                    **state_vars,
                    observation=(observation if observation is not None else ""),
                )
            )
        message = "\n".join(messages)

        return message

    def _should_block_action(self, action):
        """Check if the command should be blocked."""
        names = action.strip().split()
        if len(names) == 0:
            return False
        name = names[0]
        if name in self.config.blocklist:
            return True
        if name in self.config.blocklist_standalone and name == action.strip():
            return True
        return False

    def _retry_after_format_fail(self):
        """Ask the model to correct (without committing to persistent history) after a malformatted model output"""

        format_error_template = self.config.format_error_template
        return format_error_template

    def _retry_after_blocklist_fail(self, output, action):
        """Ask the model to correct (without committing to persistent history) after a disallowed command"""

        name = action.strip().split()[0]
        blocklist_error_message = self.config.blocklist_error_template.format(name=name)
        return blocklist_error_message

    def _parser_message(self, output: str) -> Tuple[bool, str, str]:
        try:
            thought, action = self.config.parse_function(
                output,
                self.config._commands + self.config.subroutine_types,
                strict=False,
            )
        except KeyboardInterrupt:
            raise
        except FormatError:
            self.format_fails += 1
            if self.format_fails + self.blocklist_fails > 3:
                return True, None, "exit_format"
            output = self._retry_after_format_fail()
            return True, output, "ask_for_retry"
        if self._should_block_action(action):
            self.blocklist_fails += 1
            if self.format_fails + self.blocklist_fails > 3:
                return True, None, "exit_format"
            output = self._retry_after_blocklist_fail(output, action)
            return True, output, "ask_for_retry"
        else:
            return False, thought, action

    def _split_actions(self, action: str, pattern_type="subroutine") -> List[Dict[str, Any]]:
        """Split an action into a list of actions in a greedy manner, each of which is a subroutine call or a single command."""
        parsed_action = list()
        rem_action = action
        while rem_action.strip():
            first_match = self._get_first_match(rem_action, pattern_type)
            if first_match:
                pre_action = rem_action[: first_match.start()]
                match_action = rem_action[first_match.start() : first_match.end()]
                rem_action = rem_action[first_match.end() :]
                if pre_action.strip():
                    parsed_action.append({"agent": self.name, "action": pre_action, "cmd_name": None})
                if match_action.strip():
                    if match_action.split()[0] == self.config.submit_command:
                        parsed_action.append(
                            {
                                "agent": self.name,
                                "action": match_action,
                                "cmd_name": first_match.group(1),
                            }
                        )  # submit command is not a subroutine
                    else:
                        parsed_action.append(
                            {
                                "agent": first_match.group(1),
                                "args": first_match.group(2),
                                "action": match_action,
                                "cmd_name": first_match.group(1),
                            }
                        )
            else:
                parsed_action.append({"agent": self.name, "action": rem_action, "cmd_name": None})
                rem_action = ""
        return parsed_action

    def _reset(self):
        """Reset the agent's state."""
        self.done = False
        self.system_msg = None
        self.answer = None
        self.format_fails = 0
        self.blocklist_fails = 0

    def generate_evaluation_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Union[Dict, Literal[False]]] = None,
    ):
        """
        Generate a reply to the evaluation message.
        Args:
            messages: The messages to evaluate.
            sender: The agent that sent the messages.
            config: The configuration for the evaluation.
        Returns:
            (bool, str)
        """
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]["content"]

        final, thought, action = self._parser_message(message)
        if final:
            return True, thought
        else:
            observations = list()
            run_action = self._guard_multiline_input(action)
            for sub_action in self._split_actions(run_action):
                obs, _, done, info = self.env.step(sub_action["action"])
                self.done = done
                observations.append(obs)
                if sub_action["cmd_name"] == self.config.submit_command:
                    self.done = True
                if self.done:
                    break
            observation = "\n".join([obs for obs in observations if obs is not None])
            if self.done:
                self.answer = info
                return True, None
            else:
                state = self.env.communicate(self.state_command) if self.state_command else None
                return True, self._reply_text(observation, self.env.get_available_actions(), state)

    def initiate_chat(
        self,
        recipient,
        initial_observation,
        silent: Optional[bool] = False,
        **context,
    ):
        self._prepare_chat(recipient, True)
        error_message = None
        chat_history = []
        try:
            state = self.env.communicate(self.state_command) if self.state_command else None
            initial_text = self._initial_text(initial_observation, state)
            self.send(initial_text, recipient, silent=silent)
        except BadRequestError as e:  # TODO: deal with errors
            error_message = str(e)
            print("error information: {}".format(error_message))

        key = list(self.chat_messages.keys())[0]
        chat_messages = self.chat_messages[key]
        for item in chat_messages:
            chat_history.append(item)
        if error_message is not None:
            chat_history.append(error_message)

        answer = self.answer
        if answer is None:
            answer = {"exit_status": "submitted", "submission": ""}
        recipient.reset()
        return answer, chat_history
