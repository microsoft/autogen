from .math_user_proxy_agent import MathUserProxy

task_proxy_map = {
    'math': MathUserProxy,
    'tabular': None,
    'coding': None,
}