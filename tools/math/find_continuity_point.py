def find_continuity_point(f_leq, f_gt, x_value):
    """
    Find the value 'a' that ensures the continuity of a piecewise function at a given point.

    Args:
        f_leq (str): The function expression for f(x) when x is less than or equal to the continuity point, in the form of a string.
        f_gt (str): The function expression for f(x) when x is greater than the continuity point, in the form of a string.
        x_value (float): The x-value at which continuity is to be ensured.

    Returns:
        float or None: The value of 'a' that satisfies the continuity condition,
        or None if no such value exists.
    """
    from sympy import Eq, solve, symbols, sympify

    x, a = symbols("x a")

    # Convert string to sympy expression
    f_leq_expr = sympify(f_leq)
    f_gt_expr = sympify(f_gt)

    # Evaluate the expressions at the given x_value
    f_leq_value = f_leq_expr.subs(x, x_value)
    f_gt_value = f_gt_expr.subs(x, x_value)

    # Set up the equation for a
    equation = Eq(f_leq_value, f_gt_value)

    # Solve the equation
    a_value = solve(equation, a)

    return a_value[0] if a_value else None
