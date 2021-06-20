import os

try:
    from transformers import Trainer as TFTrainer
except ImportError:
    TFTrainer = object


class TrainerForAutoTransformers(TFTrainer):

    def evaluate(self,
                 eval_dataset=None):
        """
            Overriding transformers.Trainer.evaluate by saving state with save_state

            Args:
                eval_dataset:
                    the dataset to be evaluated
        """
        from ray import tune

        eval_dataloader = self.get_eval_dataloader(eval_dataset)
        output = self.prediction_loop(
            eval_dataloader, description="Evaluation")
        self.log(output.metrics)

        self.save_state()

        for key in list(output.metrics.keys()):
            if key.startswith("eval_"):
                output.metrics[key[5:]] = output.metrics[key]
        tune.report(**output.metrics)

        return output.metrics

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
                f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}")
            self.save_model(output_dir)
            torch.save(self.optimizer.state_dict(),
                       os.path.join(output_dir, "optimizer.pt"))
            torch.save(self.lr_scheduler.state_dict(),
                       os.path.join(output_dir, "scheduler.pt"))

    @staticmethod
    def convert_num_train_epochs_to_max_steps(
            num_train_epochs: int,
            num_train_examples: int,
            per_device_train_batch_size: int,
            device_count: int):
        return int(num_train_epochs * num_train_examples / per_device_train_batch_size / device_count)

    @staticmethod
    def convert_max_steps_to_num_train_epochs(
            max_steps: int,
            num_train_examples: int,
            per_device_train_batch_size: int,
            device_count: int):
        return float(max_steps * per_device_train_batch_size * device_count) / num_train_examples

    @staticmethod
    def convert_warmup_ratio_to_warmup_steps(
            warmup_ratio,
            max_steps=None,
            num_train_epochs=None,
            num_train_examples=None,
            per_device_train_batch_size=None,
            device_count=None):
        if max_steps:
            return int(warmup_ratio * max_steps)
        max_steps = TrainerForAutoTransformers.convert_num_train_epochs_to_max_steps(
            num_train_epochs,
            num_train_examples,
            per_device_train_batch_size,
            device_count)
        return int(warmup_ratio * max_steps)

    @staticmethod
    def convert_warmup_steps_to_warmup_ratio(
            warmup_steps: int,
            num_train_epochs: int,
            num_train_examples: int,
            per_device_train_batch_size: int,
            device_count: int):
        max_steps = TrainerForAutoTransformers.convert_num_train_epochs_to_max_steps(
            num_train_epochs,
            num_train_examples,
            per_device_train_batch_size,
            device_count)
        return float(warmup_steps / max_steps)
