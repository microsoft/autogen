from flaml import tune
from flaml.automl.model import LGBMEstimator
import lightgbm
from sklearn.model_selection import train_test_split
from sklearn.datasets import fetch_california_housing
from sklearn.metrics import mean_squared_error

data = fetch_california_housing(return_X_y=False, as_frame=True)
df, X, y = data.frame, data.data, data.target
df_train, _, X_train, X_test, _, y_test = train_test_split(
    df, X, y, test_size=0.33, random_state=42
)
csv_file_name = "test/housing.csv"
df_train.to_csv(csv_file_name, index=False)
# X, y = fetch_california_housing(return_X_y=True, as_frame=True)
# X_train, X_test, y_train, y_test = train_test_split(
#     X, y, test_size=0.33, random_state=42
# )


def train_lgbm(config: dict) -> dict:
    # convert config dict to lgbm params
    params = LGBMEstimator(**config).params
    # train the model
    # train_set = lightgbm.Dataset(X_train, y_train)
    # LightGBM only accepts the csv with valid number format, if even these string columns are set to ignore.
    train_set = lightgbm.Dataset(
        csv_file_name, params={"label_column": "name:MedHouseVal", "header": True}
    )
    model = lightgbm.train(params, train_set)
    # evaluate the model
    pred = model.predict(X_test)
    mse = mean_squared_error(y_test, pred)
    # return eval results as a dictionary
    return {"mse": mse}


def test_tune_lgbm_csv():
    # load a built-in search space from flaml
    flaml_lgbm_search_space = LGBMEstimator.search_space(X_train.shape)
    # specify the search space as a dict from hp name to domain; you can define your own search space same way
    config_search_space = {
        hp: space["domain"] for hp, space in flaml_lgbm_search_space.items()
    }
    # give guidance about hp values corresponding to low training cost, i.e., {"n_estimators": 4, "num_leaves": 4}
    low_cost_partial_config = {
        hp: space["low_cost_init_value"]
        for hp, space in flaml_lgbm_search_space.items()
        if "low_cost_init_value" in space
    }
    # initial points to evaluate
    points_to_evaluate = [
        {
            hp: space["init_value"]
            for hp, space in flaml_lgbm_search_space.items()
            if "init_value" in space
        }
    ]
    # run the tuning, minimizing mse, with total time budget 3 seconds
    analysis = tune.run(
        train_lgbm,
        metric="mse",
        mode="min",
        config=config_search_space,
        low_cost_partial_config=low_cost_partial_config,
        points_to_evaluate=points_to_evaluate,
        time_budget_s=3,
        num_samples=-1,
    )
    print(analysis.best_result)


if __name__ == "__main__":
    test_tune_lgbm_csv()
