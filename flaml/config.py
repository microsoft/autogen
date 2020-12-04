'''!
 * Copyright (c) 2020 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. 
'''

N_SPLITS = 5
RANDOM_SEED = 1
SPLIT_RATIO = 0.1
HISTORY_SIZE = 10000000
MEM_THRES = 4*(1024**3)
SMALL_LARGE_THRES = 10000000
MIN_SAMPLE_TRAIN = 10000
MIN_SAMPLE_VAL = 10000
CV_HOLDOUT_THRESHOLD = 100000

BASE_Const = 2
BASE_LOWER_BOUND = 2**(0.01)

ETI_INI = {
    'lgbm':1,
    'xgboost':1.6,
    'xgboost_nb':1.6,
    'rf':2,
    'lrl1':160,
    'lrl2':25,
    'linear_svc':16,
    'kneighbor':30,
    'catboost':15,
    'extra_tree':1.9,
    'nn':50,
}