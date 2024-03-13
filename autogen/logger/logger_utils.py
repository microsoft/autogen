import datetime
import inspect
from typing import Any, Dict, List, Tuple, Union

__all__ = ("get_current_ts", "to_dict")


def get_current_ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")


def to_dict(
    obj: Union[int, float, str, bool, Dict[Any, Any], List[Any], Tuple[Any, ...], Any],
    exclude: Tuple[str, ...] = (),
    no_recursive: Tuple[Any, ...] = (),
) -> Any:
    if isinstance(obj, (int, float, str, bool)):
        return obj
    elif callable(obj):
        return inspect.getsource(obj).strip()
    elif isinstance(obj, dict):
        return {
            str(k): to_dict(str(v)) if isinstance(v, no_recursive) else to_dict(v, exclude, no_recursive)
            for k, v in obj.items()
            if k not in exclude
        }
    elif isinstance(obj, (list, tuple)):
        return [to_dict(str(v)) if isinstance(v, no_recursive) else to_dict(v, exclude, no_recursive) for v in obj]
    elif hasattr(obj, "__dict__"):
        return {
            str(k): to_dict(str(v)) if isinstance(v, no_recursive) else to_dict(v, exclude, no_recursive)
            for k, v in vars(obj).items()
            if k not in exclude
        }
    else:
        return obj
