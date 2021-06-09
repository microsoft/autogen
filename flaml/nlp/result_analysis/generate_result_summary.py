def extract_ranked_config_score(console_args, partial_config_dict):
    from .azure_utils import AzureUtils
    azure_utils = AzureUtils(console_args=console_args)

    for method, each_partial_config in partial_config_dict.items():
        dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(each_partial_config,
                                                                                       ["dat", "subdat"], method)
        for each_dataset, configscorelist in dataset2configscorelist.items():
            for config_idx in range(len(configscorelist)):
                avg_scores = configscorelist[config_idx][0][1]
                top_config = configscorelist[config_idx][0][0]
                print(avg_scores)
                print(top_config)
                # print(method + "," + str(each_dataset) + ",rep=" + str(config_idx))
                # print("avg score :" + str(avg_scores))
                # print(''.join(['{0}={1}\n'.format(key, top_config[key]) for key in sorted(top_config.keys())]))


def extract_sorted_config_list(dataset2configscorelist, topk):
    dataset2topkconfigs = {}
    for dataset, configscorelist in dataset2configscorelist.items():
        all_configscorelist = []
        for scorelist in configscorelist:
            for item in scorelist:
                if item[0] not in [x[0] for x in all_configscorelist]:
                    all_configscorelist.append(item)
        sorted_all_configscorelist = sorted(all_configscorelist, key=lambda x: x[1], reverse=True)
        topk_configs = []

        for each_hp in ("learning_rate", "num_train_epochs", "per_device_train_batch_size", "warmup_ratio",
                        "weight_decay", "adam_epsilon"):
            topk_configs.append((each_hp, [sorted_all_configscorelist[x][0][each_hp] for x in range(topk)]))
        topk_configs.append(("perf", [sorted_all_configscorelist[x][1] for x in range(topk)]))

        dataset2topkconfigs[dataset] = topk_configs
    return dataset2topkconfigs


def dict2tuple(this_dict):
    tuple_list = []
    for key in sorted(this_dict.keys()):
        tuple_list.append(this_dict[key])
    return tuple(tuple_list)


def merge_configscore_list(small_dataset2configscorelist):
    dataset2merged_configscorelist = {}
    for (dataset, each_configscore_list) in small_dataset2configscorelist.items():
        merged_configscore_list = {}
        for rep_id in range(len(each_configscore_list)):
            for each_configscore_entry in each_configscore_list[rep_id]:
                is_exist = False
                for configscore in merged_configscore_list.keys():
                    if configscore[0] == each_configscore_entry[0]:
                        is_exist = True
                        break
                if is_exist is False:
                    merged_configscore_list[dict2tuple(each_configscore_entry[0])] = each_configscore_entry[1]
        dataset2merged_configscorelist[dataset] = merged_configscore_list
    return dataset2merged_configscorelist


def get_result(console_args, partial_jobid_config):
    from .azure_utils import AzureUtils, JobID
    azure_utils = AzureUtils(console_args=console_args)
    dataset2configscorelist = \
        azure_utils.get_config_and_score_from_partial_config(
            console_args.azure_root_log_path,
            partial_jobid_config,
            ["dat", "subdat"],
            "hpo")
    for dataset, configscore_list in dataset2configscorelist.items():
        for rep_id in range(len(configscore_list)):
            config_dict = configscore_list[rep_id][0][0]
            score = configscore_list[rep_id][0][1]
            print(dataset, rep_id)
            print_config(config_dict)
            print(score)
            print()


def print_config(config_dict):
    for key in sorted(config_dict.keys()):
        if key in ("attention_probs_dropout_prob", "hidden_dropout_prob", "seed"):
            continue
        if key == "per_device_train_batch_size":
            short_key = "batch_size"
        elif key == "num_train_epochs":
            short_key = "epochs"
        else:
            short_key = key
        print(short_key, config_dict[key])


def compare_small_vs_large(console_args):
    from .azure_utils import AzureUtils, JobID
    azure_utils = AzureUtils(console_args=console_args)

    partial_jobid_config = JobID()
    partial_jobid_config.pre = "deberta"
    partial_jobid_config.mod = "hpo"
    partial_jobid_config.spa = "uni"
    partial_jobid_config.presz = "base"

    small_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
                                                                                         ["dat", "subdat"], "list")

    small_mergedconfiglist = merge_configscore_list(small_dataset2configscorelist)

    partial_jobid_config = JobID()
    partial_jobid_config.pre = "deberta"
    partial_jobid_config.mod = "hpo"
    partial_jobid_config.spa = "uni"
    partial_jobid_config.presz = "large"

    large_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
                                                                                         ["dat", "subdat"], "hpo")

    large_mergedconfiglist = merge_configscore_list(large_dataset2configscorelist)

    for (each_dataset, merged_small_configlist) in small_mergedconfiglist.items():
        merged_large_configlist = large_mergedconfiglist[each_dataset]
        print(each_dataset)
        print()
        for (each_tuple, large_score) in sorted(merged_large_configlist.items(), key=lambda x: x[1], reverse=True):
            # small_score = merged_small_configlist[each_tuple]
            is_in_onlysmall = each_tuple in small_mergedconfiglist[each_dataset]
            for each_val in each_tuple:
                print(each_val, end=", ")
            print(large_score, is_in_onlysmall, sep=",")
        print()
        for (each_tuple, small_score) in \
                sorted(small_mergedconfiglist[each_dataset].items(), key=lambda x: x[1], reverse=True):
            is_in_large = each_tuple in large_mergedconfiglist[each_dataset]
            for each_val in each_tuple:
                print(each_val, end=", ")
            print(small_score, is_in_large, sep=",")


def check_conflict(console_args, partial_jobid_config_list):
    from .azure_utils import AzureUtils, JobID
    azure_utils = AzureUtils(console_args=console_args)
    for each_partial_config in partial_jobid_config_list:
        dataset2configscorelist = \
            azure_utils.get_config_and_score_from_partial_config(
                console_args.azure_root_log_path,
                each_partial_config,
                ["dat", "subdat"],
                "unsorted")
        for (dataset, configscorelists) in dataset2configscorelist.items():
            config2score = {}
            for each_configscorelist in configscorelists:
                for (config, score, blobname) in each_configscorelist:
                    config_dict = dict2tuple(config)
                    try:
                        config2score[config_dict].append((score, blobname))
                    except KeyError:
                        config2score.setdefault(config_dict, [])
                        config2score[config_dict].append((score, blobname))
            dup_keys = [config for config in config2score.keys() if len(config2score[config]) > 1]
            dupkey_count = [len(set([y[0] for y in config2score[x]])) for x in dup_keys]
            print(dataset)
            print(len(config2score))
            print(len(dupkey_count))
            print(dupkey_count)


def print_cfo(console_args):
    from .azure_utils import JobID, AzureUtils
    jobid_config = JobID()
    jobid_config.mod = "bestnn"
    jobid_config.spa = "buni"
    jobid_config.alg = "bs"
    jobid_config.pre = "funnel"
    jobid_config.presz = "xlarge"

    for each_rep in range(3):
        jobid_config.rep = each_rep
        azure_utils = AzureUtils(console_args=console_args, jobid=jobid_config)

        dataset2configscorelist = \
            azure_utils.get_config_and_score_from_partial_config(
                console_args.azure_root_log_path,
                jobid_config,
                ["dat", "subdat"],
                "sort_time")
        dataset = ('glue', 'mrpc')
        configscorelist = dataset2configscorelist[dataset]
        count = 0
        print(dataset)
        for (config, score, blobname) in sorted(configscorelist[0], key=lambda x: x[1], reverse=True)[0:1]:
            print(count)
            print(score)
            print_config(config)
            print()
            count += 1


def download_validation(console_args, result_root_dir):
    from .azure_utils import JobID, AzureUtils
    partial_jobid_config = JobID()
    partial_jobid_config.mod = "grid"
    partial_jobid_config.pre = "roberta"
    partial_jobid_config.presz = "base"
    # partial_jobid_config.alg = "optuna"
    # partial_jobid_config.pru = "asha"
    partial_jobid_config.rep = 0

    azure_utils = AzureUtils(console_args=console_args, jobid=partial_jobid_config)
    azure_utils.get_validation_perf(console_args=console_args, partial_jobid_config=partial_jobid_config)
    azure_utils.get_test_perf(partial_jobid_config, result_root_dir)


def get_result_str(jobid_config, val_score, test_score, best_config, subdat2config=None, mode="grid"):
    result_str = jobid_config.subdat.upper() + ","
    if jobid_config.alg:
        result_str += jobid_config.alg.upper().replace("OPTUNA", "Optuna")
    if jobid_config.pru is not None and jobid_config.pru != "None":
        result_str += "+" + jobid_config.pru.upper()
    if jobid_config.subdat != "mrpc":
        result_str += ",rep " + str(jobid_config.rep) + " & " + str(
            "%.1f" % (val_score * 100)) + " & " + str(test_score)
    else:
        result_str += ",rep " + str(jobid_config.rep) + " & " + str(
            "%.1f" % (val_score[0] * 100)) + "/" + str(
            "%.1f" % (val_score[1] * 100)) + " & " + str(test_score)
    for hp in ["learning_rate", "warmup_ratio", "per_device_train_batch_size", "hidden_dropout", "attention_dropout",
               "weight_decay"]:
        if hp not in best_config:
            result_str += " & "
        else:
            if mode == "hpo":
                if best_config[hp] > 1.2 * subdat2config[jobid_config.subdat][hp]:
                    wrap_left = "\\cellcolor{green!85}{"
                elif best_config[hp] > subdat2config[jobid_config.subdat][hp]:
                    wrap_left = "\\cellcolor{green!15}{"
                elif best_config[hp] < subdat2config[jobid_config.subdat][hp] / 1.2:
                    wrap_left = "\\cellcolor{red!85}{"
                else:
                    wrap_left = "\\cellcolor{red!15}{"
                wrap_right = "}"
            else:
                wrap_left = wrap_right = ""
            if hp == "per_device_train_batch_size" or hp == "learning_rate":
                wrap_left = wrap_right = ""
            if hp == "learning_rate":
                result_str += " & " + wrap_left + "{:.1e}".format(best_config[hp]) + wrap_right
            elif hp == "per_device_train_batch_size":
                result_str += " & " + wrap_left + str(best_config[hp]) + wrap_right
            else:
                result_str += " & " + wrap_left + str("%.3f" % best_config[hp]) + wrap_right
    return result_str + "\\\\"


def extract_grid(console_args, jobid_config, overfitting_subdat, test_scores):
    from .azure_utils import JobID, AzureUtils
    key2printstr = {}
    subdat2config = {}
    for idx in range(len(overfitting_subdat)):
        jobid_config.subdat = overfitting_subdat[idx]
        jobid_config.mod = "grid"
        jobid_config.rep = 0
        azure_utils = AzureUtils(console_args=console_args, jobid=jobid_config)
        best_config, val_score = azure_utils.get_best_perf_config(console_args, jobid_config)
        best_config["hidden_dropout"] = 0.1
        best_config["attention_dropout"] = 0.1
        test_score = test_scores[idx]
        key2printstr[jobid_config.subdat.upper() + ", grid"] = get_result_str(jobid_config, val_score,
                                                                              test_score, best_config)
        subdat2config[jobid_config.subdat] = best_config
    print()
    for key, printstr in sorted(key2printstr.items(), key=lambda x: x[0]):
        print(printstr)
    return subdat2config


def extract_hpo(
        console_args,
        jobid_config,
        overfitting_subdat,
        overfitting_alg,
        overfitting_pru,
        overfitting_rep,
        subdat2config,
        test_scores):
    from .azure_utils import AzureUtils
    key2printstr = {}
    for idx in range(len(overfitting_subdat)):
        jobid_config.subdat = overfitting_subdat[idx]
        jobid_config.alg = overfitting_alg[idx]
        jobid_config.pru = overfitting_pru[idx]
        jobid_config.rep = overfitting_rep[idx]
        azure_utils = AzureUtils(console_args=console_args, jobid=jobid_config)
        best_config, val_score = azure_utils.get_best_perf_config(console_args, jobid_config)
        test_score = test_scores[idx]
        key2printstr[jobid_config.subdat.upper() + "," + jobid_config.alg.upper() + ","
                     + jobid_config.pru + ",rep " + str(jobid_config.rep)] \
            = get_result_str(jobid_config, val_score, test_score, best_config, subdat2config, mode="hpo")

    for key, printstr in sorted(key2printstr.items(), key=lambda x: x[0]):
        print(printstr)


def extract_roberta_overfitting_configs(console_args):
    from .azure_utils import JobID, AzureUtils
    jobid_config = JobID()
    jobid_config.pre = "roberta"
    jobid_config.presz = "base"

    overfitting_subdat = ["rte", "mrpc", "cola", "sst2", "stsb"]
    test_scores = ["73.1", "91.4/88.5", "61.4", "96", "89.5/88.7"]
    subdat2config = extract_grid(console_args, jobid_config, overfitting_subdat, test_scores)

    jobid_config = JobID()
    jobid_config.pre = "roberta"
    jobid_config.presz = "base"

    overfitting_subdat = ["rte", "rte", "rte", "mrpc", "mrpc", "mrpc", "sst2",
                          "rte", "mrpc", "mrpc", "stsb", "sst2", "sst2",
                          "rte", "rte", "mrpc", "mrpc", "sst2", "sst2"]
    overfitting_alg = ["rs", "rs", "rs", "rs", "rs", "rs", "rs",
                       "rs", "rs", "rs", "rs", "rs", "rs",
                       "optuna", "optuna", "optuna", "optuna", "optuna", "optuna"]
    overfitting_pru = ["None", "None", "None", "None", "None", "None", "None",
                       "asha", "asha", "asha", "asha", "asha", "asha",
                       "asha", "asha", "asha", "asha", "asha", "asha"]
    overfitting_rep = [0, 1, 2, 0, 1, 2, 0,
                       1, 0, 2, 2, 1, 2,
                       1, 2, 0, 1, 1, 2]
    test_scores = ["71.5", "72.3", "72.2", "90.5/87.1", "90.5/87.4", "90.5/87.2", "95.6",
                   "72.4", "90.7/87.4", "91.0/87.9", "89.4/88.8", "95.2", "95.7",
                   "72.4", "72.4", "90.8/87.4", "90.3/86.5", "95.1", "95.8"]
    extract_hpo(console_args, jobid_config, overfitting_subdat, overfitting_alg, overfitting_pru, overfitting_rep,
                subdat2config, test_scores)


def extract_electra_overfitting_configs(console_args):
    from .azure_utils import JobID, AzureUtils
    jobid_config = JobID()
    jobid_config.pre = "electra"
    jobid_config.presz = "base"

    overfitting_subdat = ["rte", "qnli", "cola"]
    test_scores = ["74.4", "93.2", "64.8"]
    subdat2config = extract_grid(console_args, jobid_config, overfitting_subdat, test_scores)

    jobid_config = JobID()
    jobid_config.pre = "electra"
    jobid_config.presz = "base"

    overfitting_subdat = ["rte", "rte", "qnli", "cola", "qnli", "cola"]
    overfitting_alg = ["rs", "rs", "rs", "rs", "rs", "optuna"]
    overfitting_pru = ["None", "None", "None", "asha", "asha", "asha"]
    overfitting_rep = [0, 1, 0, 2, 0, 0]
    test_scores = ["73.8", "74.3", "92.8", "64.7", "92.9", "63.6"]
    extract_hpo(console_args, jobid_config, overfitting_subdat, overfitting_alg, overfitting_pru, overfitting_rep,
                subdat2config, test_scores)
