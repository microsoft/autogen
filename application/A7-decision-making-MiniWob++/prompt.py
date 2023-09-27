import os


class Prompt:
    def __init__(self, env: str = "click-button") -> None:
        self.llm = "davinci"
        self.davinci_type_regex = "^type\s.{1,}$"
        self.chatgpt_type_regex = '^type\s[^"]{1,}$'
        self.press_regex = (
            "^press\s(enter|arrowleft|arrowright|arrowup|arrowdown|backspace)$"
        )
        self.clickxpath_regex = "^clickxpath\s.{1,}$"
        self.clickoption_regex = "^clickoption\s.{1,}$"
        self.movemouse_regex = "^movemouse\s.{1,}$"

        if os.path.exists(f"prompt/{env}/"):
            base_dir = f"prompt/{env}/"
        else:
            base_dir = f"prompt/"

        with open(base_dir + "example.txt") as f:
            self.example_prompt = f.read()

        with open(base_dir + "first_action.txt") as f:
            self.first_action_prompt = f.read()

        with open(base_dir + "base.txt") as f:
            self.base_prompt = f.read()
            self.base_prompt = self.replace_regex(self.base_prompt)

        with open(base_dir + "initialize_plan.txt") as f:
            self.init_plan_prompt = f.read()

        with open(base_dir + "action.txt") as f:
            self.action_prompt = f.read()

        with open(base_dir + "rci_action.txt") as f:
            self.rci_action_prompt = f.read()
            self.rci_action_prompt = self.replace_regex(self.rci_action_prompt)

        with open(base_dir + "update_action.txt") as f:
            self.update_action = f.read()

    def replace_regex(self, base_prompt):
        if self.llm == "chatgpt":
            base_prompt = base_prompt.replace("{type}", self.chatgpt_type_regex)
        elif self.llm == "davinci":
            base_prompt = base_prompt.replace("{type}", self.davinci_type_regex)
        else:
            raise NotImplemented

        base_prompt = base_prompt.replace("{press}", self.press_regex)
        base_prompt = base_prompt.replace("{clickxpath}", self.clickxpath_regex)
        base_prompt = base_prompt.replace("{clickoption}", self.clickoption_regex)
        base_prompt = base_prompt.replace("{movemouse}", self.movemouse_regex)

        return base_prompt
