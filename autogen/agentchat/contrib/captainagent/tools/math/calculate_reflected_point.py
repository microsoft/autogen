def calculate_reflected_point(point):
    """
    Calculates the reflection point of a given point about the line y=x.

    Args:
        point (dict): A dictionary representing the coordinates of the point.
            The dictionary should have keys 'x' and 'y' representing the x and y coordinates respectively.

    Returns:
        dict: A dictionary representing the coordinates of the reflected point. Its keys are 'x' and 'y'.
    """
    # Swap x and y for reflection about y=x
    reflected_point = {"x": point["y"], "y": point["x"]}
    return reflected_point
