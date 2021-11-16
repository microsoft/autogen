import os

try:
    from transformers import Trainer as TFTrainer
except ImportError:
    TFTrainer = object


class TrainerForAuto(TFTrainer):
    def evaluate(self, eval_dataset=None):
        """
        Overriding transformers.Trainer.evaluate by saving state with save_state

        Args:
            eval_dataset:
                the dataset to be evaluated
        """

        if self.eval_dataset is not None:
            eval_dataloader = self.get_eval_dataloader(self.eval_dataset)
            output = self.prediction_loop(eval_dataloader, description="Evaluation")
            self.log(output.metrics)

            ckpt_dir = self.save_state()

            for key in list(output.metrics.keys()):
                if key.startswith("eval_"):
                    output.metrics[key[5:]] = output.metrics.pop(key)

            if hasattr(self, "ckpt_to_global_step"):
                self.ckpt_to_metric[ckpt_dir] = output.metrics
                self.ckpt_to_global_step[ckpt_dir] = self.state.global_step
            else:
                self.ckpt_to_global_step = {ckpt_dir: self.state.global_step}
                self.ckpt_to_metric = {ckpt_dir: output.metrics}

    def save_state(self):
        """
        Overriding transformers.Trainer.save_state. It is only through saving
        the states can best_trial.get_best_checkpoint return a non-empty value.
        """
        import torch
        from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR
        from ray import tune

        with tune.checkpoint_dir(step=self.state.global_step) as checkpoint_dir:
            self.args.output_dir = checkpoint_dir
            # This is the directory name that Huggingface requires.
            output_dir = os.path.join(
                self.args.output_dir,
                f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}",
            )
            self.save_model(output_dir)
            torch.save(
                self.optimizer.state_dict(), os.path.join(output_dir, "optimizer.pt")
            )
            torch.save(
                self.lr_scheduler.state_dict(), os.path.join(output_dir, "scheduler.pt")
            )
            return output_dir
