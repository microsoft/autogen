from __future__ import annotations

from typing import Iterable, Literal

Attribute = Literal[
    "bold",
    "dark",
    "underline",
    "blink",
    "reverse",
    "concealed",
]

Highlight = Literal[
    "on_black",
    "on_grey",
    "on_red",
    "on_green",
    "on_yellow",
    "on_blue",
    "on_magenta",
    "on_cyan",
    "on_light_grey",
    "on_dark_grey",
    "on_light_red",
    "on_light_green",
    "on_light_yellow",
    "on_light_blue",
    "on_light_magenta",
    "on_light_cyan",
    "on_white",
]

Color = Literal[
    "black",
    "grey",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "light_grey",
    "dark_grey",
    "light_red",
    "light_green",
    "light_yellow",
    "light_blue",
    "light_magenta",
    "light_cyan",
    "white",
]


# termcolor is an optional dependency - if it cannot be imported then no color is used.
# Alternatively the envvar NO_COLOR can be used to disable color.
# To allow for proper typing and for termcolor to be optional we need to re-define the types used in the lib here.
# This is the direct function definition from termcolor.
def colored(
    text: object,
    color: Color | None = None,
    on_color: Highlight | None = None,
    attrs: Iterable[Attribute] | None = None,
    *,
    no_color: bool | None = None,
    force_color: bool | None = None,
) -> str:
    try:
        from termcolor import colored

        return colored(
            text=text, color=color, on_color=on_color, attrs=attrs, no_color=no_color, force_color=force_color
        )
    except ImportError:
        return text
