import os
import shutil
import tempfile
import unittest
import numpy as np
from flaml.searcher.suggestion import ConcurrencyLimiter
from flaml import tune
from flaml import CFO
from flaml import BlendSearch


class AbstractWarmStartTest:
    def setUp(self):
        # ray.init(num_cpus=1, local_mode=True)
        self.tmpdir = tempfile.mkdtemp()
        self.experiment_name = "searcher-state-Test.pkl"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        # ray.shutdown()

    def set_basic_conf(self):
        raise NotImplementedError()

    def run_part_from_scratch(self):
        np.random.seed(162)
        search_alg, cost = self.set_basic_conf()
        search_alg = ConcurrencyLimiter(search_alg, 1)
        results_exp_1 = tune.run(
            cost,
            num_samples=5,
            search_alg=search_alg,
            verbose=0,
            local_dir=self.tmpdir)
        checkpoint_path = os.path.join(self.tmpdir, self.experiment_name)
        search_alg.save(checkpoint_path)
        return results_exp_1, np.random.get_state(), checkpoint_path

    def run_explicit_restore(self, random_state, checkpoint_path):
        np.random.set_state(random_state)
        search_alg2, cost = self.set_basic_conf()
        search_alg2 = ConcurrencyLimiter(search_alg2, 1)
        search_alg2.restore(checkpoint_path)
        return tune.run(cost, num_samples=5, search_alg=search_alg2, verbose=0)

    def run_full(self):
        np.random.seed(162)
        search_alg3, cost = self.set_basic_conf()
        search_alg3 = ConcurrencyLimiter(search_alg3, 1)
        return tune.run(
            cost, num_samples=10, search_alg=search_alg3, verbose=0)

    def testReproduce(self):
        results_exp_1, _, _ = self.run_part_from_scratch()
        results_exp_2, _, _ = self.run_part_from_scratch()
        trials_1_config = [trial.config for trial in results_exp_1.trials]
        trials_2_config = [trial.config for trial in results_exp_2.trials]
        self.assertEqual(trials_1_config, trials_2_config)

    def testWarmStart(self):
        results_exp_1, r_state, checkpoint_path = self.run_part_from_scratch()
        results_exp_2 = self.run_explicit_restore(r_state, checkpoint_path)
        results_exp_3 = self.run_full()
        trials_1_config = [trial.config for trial in results_exp_1.trials]
        trials_2_config = [trial.config for trial in results_exp_2.trials]
        trials_3_config = [trial.config for trial in results_exp_3.trials]
        self.assertEqual(trials_1_config + trials_2_config, trials_3_config)


class CFOWarmStartTest(AbstractWarmStartTest, unittest.TestCase):
    def set_basic_conf(self):
        space = {
            "height": tune.uniform(-100, 100),
            "width": tune.randint(0, 100),
        }

        def cost(param):
            tune.report(loss=(param["height"] - 14)**2 - abs(param["width"] - 3))

        search_alg = CFO(
            space=space,
            metric="loss",
            mode="min",
            seed=20,
        )

        return search_alg, cost

# # # Not doing test for BS because of problems with random seed in OptunaSearch
# class BlendsearchWarmStartTest(AbstractWarmStartTest, unittest.TestCase):
#     def set_basic_conf(self):
#         space = {
#             "height": tune.uniform(-100, 100),
#             "width": tune.randint(0, 100),
#         }

#         def cost(param):
#             tune.report(loss=(param["height"] - 14)**2 - abs(param["width"] - 3))

#         search_alg = BlendSearch(
#             space=space,
#             metric="loss",
#             mode="min",
#             seed=20,
#         )

#         return search_alg, cost
