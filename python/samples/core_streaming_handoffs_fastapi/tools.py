from typing import Dict, Union
from autogen_core.tools import FunctionTool


def execute_order(product: str, price: int) -> Dict[str, Union[str, int]]:
    print("\n\n=== Order Summary ===")
    print(f"Product: {product}")
    print(f"Price: ${price}")
    print("=================\n")
    return {"product":product,"price":price}
    


def look_up_item(search_query: str) -> Dict[str, str]:
    item_id = "item_132612938"
    return {"item_id":item_id,"status":"found"}


def execute_refund(item_id: str, reason: str = "not provided") -> Dict[str, str]:
    print("\n\n=== Refund Summary ===")
    print(f"Item ID: {item_id}")
    print(f"Reason: {reason}")
    print("=================\n")
    print("Refund execution successful!")
    return {"item_id":item_id, "reason":reason, "refund_status":"Successful"}


execute_order_tool = FunctionTool(execute_order, description="Price should be in USD.")
look_up_item_tool = FunctionTool(
    look_up_item, description="Use to find item ID.\nSearch query can be a description or keywords."
)
execute_refund_tool = FunctionTool(execute_refund, description="")
