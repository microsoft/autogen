def calculate_skewness_and_kurtosis(csv_file: str, column_name: str) -> tuple:
    """
    Calculate the skewness and kurtosis of a specified column in a CSV file. The kurtosis is calculated using the Fisher definition.
    The two metrics are computed using scipy.stats functions.

    Args:
    csv_file (str): The path to the CSV file.
    column_name (str): The name of the column to calculate skewness and kurtosis for.

    Returns:
    tuple: (skewness, kurtosis)
    """
    import pandas as pd
    from scipy.stats import kurtosis, skew

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Extract the specified column
    column = df[column_name]

    # Calculate the skewness and kurtosis
    skewness = skew(column)
    kurt = kurtosis(column)

    return skewness, kurt
