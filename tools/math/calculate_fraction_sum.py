def calculate_fraction_sum(
    fraction1_numerator: int, fraction1_denominator: int, fraction2_numerator: int, fraction2_denominator: int
):
    """
    Calculates the sum of two fractions and returns the result as a mixed number.

    Args:
        fraction1_numerator: The numerator of the first fraction.
        fraction1_denominator: The denominator of the first fraction.
        fraction2_numerator: The numerator of the second fraction.
        fraction2_denominator: The denominator of the second fraction.

    Returns:
        str: The sum of the two fractions as a mixed number in the format 'a b/c'
    """
    from fractions import Fraction

    fraction1 = Fraction(fraction1_numerator, fraction1_denominator)
    fraction2 = Fraction(fraction2_numerator, fraction2_denominator)
    result = fraction1 + fraction2
    mixed_number = result.numerator // result.denominator
    mixed_fraction_numerator = result.numerator % result.denominator
    if mixed_fraction_numerator > 0:
        return f"{mixed_number} {Fraction(mixed_fraction_numerator, result.denominator)}"
    else:
        return str(mixed_number)
