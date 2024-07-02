from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["sympy"])
def calculate_circle_area_from_diameter(diameter):
    """
    Calculate the area of a circle given its diameter.

    Args:
    diameter (float): The diameter of the circle.

    Returns:
    float: The area of the circle.
    """
    from sympy import pi

    radius = diameter / 2
    area = pi * radius**2
    return area
