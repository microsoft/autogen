def detect_outlier_iqr(csv_file: str, column_name: str):
    """
    Detect outliers in a specified column of a CSV file using the IQR method.

    Args:
    csv_file (str): The path to the CSV file.
    column_name (str): The name of the column to detect outliers in.

    Returns:
    list: A list of row indices that correspond to the outliers.
    """
    import pandas as pd

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Calculate the quartiles and IQR for the specified column
    q1 = df[column_name].quantile(0.25)
    q3 = df[column_name].quantile(0.75)
    iqr = q3 - q1

    # Find the outliers based on the defined criteria
    outliers = df[(df[column_name] < q1 - 1.5 * iqr) | (df[column_name] > q3 + 1.5 * iqr)]

    # Return the row indices of the outliers
    return outliers.index.tolist()
