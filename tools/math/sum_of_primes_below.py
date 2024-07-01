def sum_of_primes_below(threshold):
    """
    Calculates the sum of all prime numbers below a given threshold.

    Args:
        threshold (int): The maximum number (exclusive) up to which primes are summed.

    Returns:
        int: The sum of all prime numbers below the threshold.
    """
    from sympy import primerange

    return sum(primerange(2, threshold))
