import os
import unittest
from tempfile import TemporaryDirectory

from sklearn.datasets import load_boston

from flaml import AutoML
from flaml.training_log import training_log_reader


class TestTrainingLog(unittest.TestCase):

    def test_training_log(self):

        with TemporaryDirectory() as d:
            filename = os.path.join(d, 'test_training_log.log')

            # Run a simple job.
            automl_experiment = AutoML()
            automl_settings = {
                "time_budget": 2,
                "metric": 'mse',
                "task": 'regression',
                "log_file_name": filename,
                "log_training_metric": True,
                "mem_thres": 1024 * 1024,
                "n_jobs": 1,
                "model_history": True,
                "verbose": 2,
            }
            X_train, y_train = load_boston(return_X_y=True)
            automl_experiment.fit(X_train=X_train, y_train=y_train,
                                  **automl_settings)

            # Check if the training log file is populated.
            self.assertTrue(os.path.exists(filename))
            with training_log_reader(filename) as reader:
                count = 0
                for record in reader.records():
                    print(record)
                    count += 1
                self.assertGreater(count, 0)
