def explore_csv(file_path, num_lines=5):
    """
    Reads a CSV file and prints the column names, shape, data types, and the first few lines of data.

    Args:
        file_path (str): The path to the CSV file.
        num_lines (int, optional): The number of lines to print. Defaults to 5.
    """
    import pandas as pd

    df = pd.read_csv(file_path)
    header = df.columns
    print("Columns:")
    print(", ".join(header))
    print("Shape:", df.shape)
    print("Data Types:")
    print(df.dtypes)
    print("First", num_lines, "lines:")
    print(df.head(num_lines))
