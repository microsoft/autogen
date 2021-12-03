import os

try:
    from transformers import Trainer as TFTrainer
    from transformers import Seq2SeqTrainer
except ImportError:
    TFTrainer = object


class TrainerForAuto(TFTrainer):
    def evaluate(
        self,
        eval_dataset=None,
        ignore_keys=None,
        metric_key_prefix="eval",
        is_seq2seq=False,
    ):
        """Overriding transformers.Trainer.evaluate by saving metrics and checkpoint path"""
        from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

        ckpt_dir = os.path.join(
            self.args.output_dir, f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}"
        )
        eval_dataset = eval_dataset if eval_dataset is not None else self.eval_dataset

        # TODO: if your task is seq2seq (i.e., SUMMARIZATION), uncomment the code below (add indentation before metrics = eval_dataset...

        # if is_seq2seq:
        #     metrics = eval_dataset and super().evaluate(
        #         eval_dataset,
        #         ignore_keys,
        #         metric_key_prefix,
        #         num_beams=self.args.num_beams,
        #     )
        # else:
        metrics = eval_dataset and super().evaluate(
            eval_dataset,
            ignore_keys,
            metric_key_prefix,
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


# TODO: if your task is SUMMARIZATION, you need a different
#  class Seq2SeqTrainerForAuto, uncomment the code below
#  Note: I have implemented it here,
#  but I don't know whether it's correct, you need to debug
#  Seq2SeqTrainerForAuto to make sure it's correct


# class Seq2SeqTrainerForAuto(Seq2SeqTrainer, TrainerForAuto):
#     def evaluate(self, eval_dataset=None, ignore_keys=None, metric_key_prefix="eval"):
#         """Overriding transformers.Trainer.evaluate by saving metrics and checkpoint path"""
#         super(TrainerForAuto).evaluate(
#             eval_dataset, ignore_keys, metric_key_prefix, is_seq2seq=True
#         )


# TODO: if your task is QUESTIONANSWERING, uncomment the code below
#  by adapting the code in https://github.com/huggingface/transformers/blob/master/examples/pytorch/question-answering/trainer_qa.py#L28


# class QATrainerForAuto(TrainerForAuto):
#     pass
# TODO: if your task is QUESTIONANSWERING, do the post processing here
