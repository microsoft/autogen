

_NOT_SUPPORT_MESSAGE_NAME_PROVIDERS=['mistral']

def is_not_support_user_message_name(provider:str):
    return provider in _NOT_SUPPORT_MESSAGE_NAME_PROVIDERS