with open("python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_selector_group_chat.py", "r") as f:
    content = f.read()

old_code = """        if self._previous_speaker is not None:
            trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, using the previous speaker.")
            return self._previous_speaker
        trace_logger.warning(
            f"Model failed to select a speaker after {max_attempts} and there was no previous speaker, using the first participant."
        )
        return self._participant_names[0]"""

new_code = """        import random
        if not self._allow_repeated_speaker and self._previous_speaker is not None:
            candidates = [p for p in participants if p != self._previous_speaker]
            if candidates:
                trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, returning a random different candidate.")
                return random.choice(candidates)

        if self._previous_speaker is not None:
            trace_logger.warning(f"Model failed to select a speaker after {max_attempts}, using the previous speaker.")
            return self._previous_speaker
        trace_logger.warning(
            f"Model failed to select a speaker after {max_attempts} and there was no previous speaker, using the first participant."
        )
        return self._participant_names[0]"""

content = content.replace(old_code, new_code)

with open("python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_selector_group_chat.py", "w") as f:
    f.write(content)
