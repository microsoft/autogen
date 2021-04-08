from flaml import AutoML
from sklearn.datasets import load_boston
import os
import unittest
import logging
import tempfile
import io


class TestLogging(unittest.TestCase):

    def test_logging_level(self):

        from flaml import logger, logger_formatter

        with tempfile.TemporaryDirectory() as d:

            training_log = os.path.join(d, "training.log")

            # Configure logging for the FLAML logger
            # and add a handler that outputs to a buffer.
            logger.setLevel(logging.INFO)
            buf = io.StringIO()
            ch = logging.StreamHandler(buf)
            ch.setFormatter(logger_formatter)
            logger.addHandler(ch)

            # Run a simple job.
            automl = AutoML()
            automl_settings = {
                "time_budget": 1,
                "metric": 'mse',
                "task": 'regression',
                "log_file_name": training_log,
                "log_training_metric": True,
                "n_jobs": 1,
                "model_history": True,
            }
            X_train, y_train = load_boston(return_X_y=True)
            n = len(y_train) >> 1
            automl.fit(X_train=X_train[:n], y_train=y_train[:n],
                       X_val=X_train[n:], y_val=y_train[n:],
                       **automl_settings)

            # Check if the log buffer is populated.
            self.assertTrue(len(buf.getvalue()) > 0)

        import pickle
        with open('automl.pkl', 'wb') as f:
            pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
        print(automl.__version__)
