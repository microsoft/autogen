def simplify_mixed_numbers(numerator1, denominator1, numerator2, denominator2, whole_number1, whole_number2):
    """
    Simplifies the sum of two mixed numbers and returns the result as a string in the format 'a b/c'.

    Args:
        numerator1 (int): The numerator of the first fraction.
        denominator1 (int): The denominator of the first fraction.
        numerator2 (int): The numerator of the second fraction.
        denominator2 (int): The denominator of the second fraction.
        whole_number1 (int): The whole number part of the first mixed number.
        whole_number2 (int): The whole number part of the second mixed number.

    Returns:
        str: The simplified sum of the two mixed numbers as a string in the format 'a b/c'.
    """
    from fractions import Fraction

    # Convert mixed numbers to improper fractions
    fraction1 = whole_number1 * denominator1 + numerator1
    fraction2 = whole_number2 * denominator2 + numerator2
    # Create Fraction objects
    frac1 = Fraction(fraction1, denominator1)
    frac2 = Fraction(fraction2, denominator2)
    # Calculate the sum
    result = frac1 + frac2
    # Convert to mixed number
    mixed_number = result.numerator // result.denominator
    mixed_fraction_numerator = result.numerator % result.denominator
    mixed_fraction = Fraction(mixed_fraction_numerator, result.denominator)
    # Return as a string in the format 'a b/c'
    if mixed_fraction_numerator > 0:
        return f"{mixed_number} {mixed_fraction}"
    else:
        return str(mixed_number)
