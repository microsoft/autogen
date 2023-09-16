import os
import argparse
import pandas as pd
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)


def main():
    """Main function of the script."""

    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="path to input data")
    parser.add_argument("--test_train_ratio", type=float, required=False, default=0.25)
    parser.add_argument("--train_data", type=str, help="path to train data")
    parser.add_argument("--test_data", type=str, help="path to test data")
    args = parser.parse_args()

    logger.info(" ".join(f"{k}={v}" for k, v in vars(args).items()))

    data_path = os.path.join(args.data, "data.csv")
    df = pd.read_csv(data_path)

    train_df, test_df = train_test_split(
        df,
        test_size=args.test_train_ratio,
    )

    # output paths are mounted as folder, therefore, we are adding a filename to the path
    train_df.to_csv(os.path.join(args.train_data, "data.csv"), index=False)

    test_df.to_csv(os.path.join(args.test_data, "data.csv"), index=False)


if __name__ == "__main__":
    main()
