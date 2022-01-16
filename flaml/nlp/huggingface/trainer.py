import os

try:
    from transformers import Seq2SeqTrainer
except ImportError:
    Seq2SeqTrainer = object


class TrainerForAuto(Seq2SeqTrainer):
    def predict(
        self,
        test_dataset,
        ignore_keys=None,
        metric_key_prefix=None,
        max_length=None,
        num_beams=None,
    ):
        if getattr(self, "_is_seq2seq", None):
            return super().predict(
                test_dataset,
                ignore_keys,
                metric_key_prefix,
                max_length,
                num_beams,
            )
        else:
            return super(Seq2SeqTrainer, self).predict(
                test_dataset, ignore_keys, metric_key_prefix
            )

    def prediction_step(
        self,
        model,
        inputs,
        prediction_loss_only,
        ignore_keys,
    ):
        if getattr(self, "_is_seq2seq", None):
            return super().prediction_step(
                model, inputs, prediction_loss_only, ignore_keys
            )
        else:
            return super(Seq2SeqTrainer, self).prediction_step(
                model, inputs, prediction_loss_only, ignore_keys
            )

    def log(self, logs) -> None:
        if getattr(self, "_is_seq2seq", None):
            super().log(logs)
        else:
            super(Seq2SeqTrainer, self).log(logs)
        if not hasattr(self, "intermediate_results"):
            self.intermediate_results = {}

        epoch_num = logs.get("epoch", None)
        if epoch_num:
            self.intermediate_results.setdefault(epoch_num, {})
            self.intermediate_results[epoch_num].update(logs)

    def evaluate(
        self,
        eval_dataset=None,
        ignore_keys=None,
        metric_key_prefix="eval",
    ):
        """Overriding transformers.Trainer.evaluate by saving metrics and checkpoint path."""
        from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

        ckpt_dir = os.path.join(
            self.args.output_dir, f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}"
        )
        eval_dataset = eval_dataset if eval_dataset is not None else self.eval_dataset

        # TODO: if your task is seq2seq (i.e., SUMMARIZATION), uncomment the code below (add indentation before metrics = eval_dataset...

        if getattr(self, "_is_seq2seq", None):
            metrics = eval_dataset and super().evaluate(
                eval_dataset,
                ignore_keys,
                metric_key_prefix,
                max_length=self.args.generation_max_length,
                num_beams=self.args.generation_num_beams,
            )
        else:
            metrics = eval_dataset and super(Seq2SeqTrainer, self).evaluate(
                eval_dataset,
                ignore_keys,
                metric_key_prefix,
            )
        if hasattr(self, "ckpt_to_global_step"):
            self.ckpt_to_global_step[ckpt_dir] = self.state.global_step
            if metrics:
                self.ckpt_to_metric[ckpt_dir] = metrics
        else:
            self.ckpt_to_global_step = {ckpt_dir: self.state.global_step}
            self.ckpt_to_metric = {ckpt_dir: metrics} if metrics else {}
        return metrics
