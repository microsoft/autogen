import os

try:
    from transformers import Trainer as TFTrainer
except ImportError:
    TFTrainer = object


class TrainerForAuto(TFTrainer):
    def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
        """Overriding transformers.Trainer.evaluate by saving metrics and checkpoint path"""
        from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

        ckpt_dir = os.path.join(
            self.args.output_dir, f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}"
        )
        eval_dataset = eval_dataset if eval_dataset is not None else self.eval_dataset
        metrics = eval_dataset and super().evaluate(
            eval_dataset, ignore_keys, metric_key_prefix
        )
        if metrics:
            for key in list(metrics.keys()):
                if key.startswith("eval_"):
                    metrics[key[5:]] = metrics.pop(key)
        if hasattr(self, "ckpt_to_global_step"):
            self.ckpt_to_global_step[ckpt_dir] = self.state.global_step
            if metrics:
                self.ckpt_to_metric[ckpt_dir] = metrics
        else:
            self.ckpt_to_global_step = {ckpt_dir: self.state.global_step}
            self.ckpt_to_metric = {ckpt_dir: metrics} if metrics else {}
