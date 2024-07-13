from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["sympy"])
def compute_currency_conversion(amount, exchange_rate):
    """
    Compute the currency conversion of the given amount using the provided exchange rate.

    Args:
    amount (float): The amount to be converted.
    exchange_rate (float): The exchange rate to use for the conversion, represented as the amount of second currency equivalent to one unit of the first currency.

    Returns:
    float: The converted amount.

    """
    from sympy import Rational

    # Calculate the converted amount using the given exchange rate
    converted_amount = Rational(amount, exchange_rate)
    return float(converted_amount)
