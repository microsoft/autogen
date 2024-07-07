from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["sympy"])
def calculate_matrix_power(matrix, power):
    """
    Calculate the power of a given matrix.

    Args:
        matrix (list): An array of numbers that represents the matrix.
        power (int): The power to which the matrix is raised.

    Returns:
        Matrix: The resulting matrix after raising to power.

    Raises:
        ValueError: If the power is negative and the matrix is not invertible.
    """
    from sympy import Matrix, eye

    m = Matrix(matrix)
    if power == 0:
        return eye(m.shape[0])
    elif power < 0:
        if not m.is_invertible():
            raise ValueError("Matrix is not invertible.")
        return m.inverse() ** (-power)
    elif power > 0:
        return m**power
