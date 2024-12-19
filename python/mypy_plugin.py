from typing import Callable
from mypy.plugin import Plugin, DynamicClassDefContext, SymbolTableNode
from mypy.nodes import SymbolTableNode

class CustomPlugin(Plugin):
 def get_dynamic_class_hook(
        self, fullname: str
    ) -> Callable[[DynamicClassDefContext], None] | None:

    def hook(ctx: DynamicClassDefContext) -> None:
        if "Component" in fullname:
            # We need to generate mypy.nodes.TypeInfo
            # to make mypy understand the type of the class
            ctx.api.add_symbol_table_node(
               fullname, SymbolTableNode(

               )
            )
            return

def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return CustomPlugin