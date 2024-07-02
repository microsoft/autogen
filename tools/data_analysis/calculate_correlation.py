def calculate_correlation(csv_path: str, column1: str, column2: str, method: str = "pearson") -> float:
    """
    Calculate the correlation between two columns in a CSV file.

    Args:
    csv_path (str): The path to the CSV file.
    column1 (str): The name of the first column.
    column2 (str): The name of the second column.
    method (str or callable, optional): The method used to calculate the correlation.
        - 'pearson' (default): Pearson correlation coefficient.
        - 'kendall': Kendall Tau correlation coefficient.
        - 'spearman': Spearman rank correlation coefficient.
        - callable: A custom correlation function that takes two arrays and returns a scalar.

    Returns:
    float: The correlation coefficient between the two columns.
    """
    import pandas as pd

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_path)

    # Select the specified columns
    selected_columns = df[[column1, column2]]

    # Calculate the correlation based on the specified method
    if method == "pearson":
        correlation = selected_columns.corr().iloc[0, 1]
    elif method == "kendall":
        correlation = selected_columns.corr(method="kendall").iloc[0, 1]
    elif method == "spearman":
        correlation = selected_columns.corr(method="spearman").iloc[0, 1]
    elif callable(method):
        correlation = selected_columns.corr(method=method).iloc[0, 1]
    else:
        raise ValueError("Invalid correlation method. Please choose 'pearson', 'kendall', 'spearman', or a callable.")

    return correlation
