from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["pandas", "scipy"])
def shapiro_wilk_test(csv_file, column_name):
    """
    Perform the Shapiro-Wilk test on a specified column of a CSV file.

    Args:
    csv_file (str): The path to the CSV file.
    column_name (str): The name of the column to perform the test on.

    Returns:
    float: The p-value resulting from the Shapiro-Wilk test.
    """
    import pandas as pd
    from scipy.stats import shapiro

    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Extract the specified column as a numpy array
    column_data = df[column_name].values

    # Perform the Shapiro-Wilk test
    _, p_value = shapiro(column_data)

    return p_value
