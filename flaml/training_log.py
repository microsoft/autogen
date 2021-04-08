'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
'''

import json
from typing import IO
from contextlib import contextmanager
import warnings


class TrainingLogRecord(object):

    def __init__(self,
                 record_id: int,
                 iter_per_learner: int,
                 logged_metric: float,
                 trial_time: float,
                 total_search_time: float,
                 validation_loss,
                 config,
                 best_validation_loss,
                 best_config,
                 learner,
                 sample_size):
        self.record_id = record_id
        self.iter_per_learner = iter_per_learner
        self.logged_metric = logged_metric
        self.trial_time = trial_time
        self.total_search_time = total_search_time
        self.validation_loss = validation_loss
        self.config = config
        self.best_validation_loss = best_validation_loss
        self.best_config = best_config
        self.learner = learner
        self.sample_size = sample_size

    def dump(self, fp: IO[str]):
        d = vars(self)
        return json.dump(d, fp)

    @classmethod
    def load(cls, json_str: str):
        d = json.loads(json_str)
        return cls(**d)

    def __str__(self):
        return json.dumps(vars(self))


class TrainingLogCheckPoint(TrainingLogRecord):

    def __init__(self, curr_best_record_id: int):
        self.curr_best_record_id = curr_best_record_id


class TrainingLogWriter(object):

    def __init__(self, output_filename: str):
        self.output_filename = output_filename
        self.file = None
        self.current_best_loss_record_id = None
        self.current_best_loss = float('+inf')
        self.current_sample_size = None
        self.current_record_id = 0

    def open(self):
        self.file = open(self.output_filename, 'w')

    def append(self,
               it_counter: int,
               train_loss: float,
               trial_time: float,
               total_search_time: float,
               validation_loss,
               config,
               best_validation_loss,
               best_config,
               learner,
               sample_size):
        if self.file is None:
            raise IOError("Call open() to open the outpute file first.")
        if validation_loss is None:
            raise ValueError('TEST LOSS NONE ERROR!!!')
        record = TrainingLogRecord(self.current_record_id,
                                   it_counter,
                                   train_loss,
                                   trial_time,
                                   total_search_time,
                                   validation_loss,
                                   config,
                                   best_validation_loss,
                                   best_config,
                                   learner,
                                   sample_size)
        if validation_loss < self.current_best_loss or \
            validation_loss == self.current_best_loss and \
                sample_size > self.current_sample_size:
            self.current_best_loss = validation_loss
            self.current_sample_size = sample_size
            self.current_best_loss_record_id = self.current_record_id
        self.current_record_id += 1
        record.dump(self.file)
        self.file.write('\n')
        self.file.flush()

    def checkpoint(self):
        if self.file is None:
            raise IOError("Call open() to open the outpute file first.")
        if self.current_best_loss_record_id is None:
            warnings.warn("checkpoint() called before any record is written, "
                          "skipped.")
            return
        record = TrainingLogCheckPoint(self.current_best_loss_record_id)
        record.dump(self.file)
        self.file.write('\n')
        self.file.flush()

    def close(self):
        self.file.close()
        self.file = None  # for pickle


class TrainingLogReader(object):

    def __init__(self, filename: str):
        self.filename = filename
        self.file = None

    def open(self):
        self.file = open(self.filename)

    def records(self):
        if self.file is None:
            raise IOError("Call open() before reading log file.")
        for line in self.file:
            data = json.loads(line)
            if len(data) == 1:
                # Skip checkpoints.
                continue
            yield TrainingLogRecord(**data)

    def close(self):
        self.file.close()
        self.file = None  # for pickle

    def get_record(self, record_id) -> TrainingLogRecord:
        if self.file is None:
            raise IOError("Call open() before reading log file.")
        for rec in self.records():
            if rec.record_id == record_id:
                return rec
        raise ValueError(f"Cannot find record with id {record_id}.")


@contextmanager
def training_log_writer(filename: str):
    try:
        w = TrainingLogWriter(filename)
        w.open()
        yield w
    finally:
        w.close()


@contextmanager
def training_log_reader(filename: str):
    try:
        r = TrainingLogReader(filename)
        r.open()
        yield r
    finally:
        r.close()
