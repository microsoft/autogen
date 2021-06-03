import numpy as np
import logging
import itertools
from typing import Dict, Optional, List
from flaml.tune import Categorical, Float, PolynomialExpansionSet
from flaml.tune import Trial
from flaml.onlineml import VowpalWabbitTrial
from flaml.searcher import CFO

logger = logging.getLogger(__name__)


class BaseSearcher:
    """Implementation of the BaseSearcher

    Methods:
        set_search_properties(metric, mode, config)
        next_trial()
        on_trial_result(trial_id, result)
        on_trial_complete()
    """

    def __init__(self,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 ):
        pass

    def set_search_properties(self, metric: Optional[str] = None, mode: Optional[str] = None,
                              config: Optional[Dict] = None):
        if metric:
            self._metric = metric
        if mode:
            assert mode in ["min", "max"], "`mode` must be 'min' or 'max'."
            self._mode = mode

    def next_trial(self):
        NotImplementedError

    def on_trial_result(self, trial_id: str, result: Dict):
        pass

    def on_trial_complete(self, trial):
        pass


class ChampionFrontierSearcher(BaseSearcher):
    """The ChampionFrontierSearcher class

    Methods:
        (metric, mode, config)
            Generate a list of new challengers, and add them to the _challenger_list
        next_trial()
            Pop a trial from the _challenger_list
        on_trial_result(trial_id, result)
            Doing nothing
        on_trial_complete()
            Doing nothing

    NOTE:
        This class serves the role of ConfigOralce.
        Every time we create an online trial, we generate a searcher_trial_id.
        At the same time, we also record the trial_id of the VW trial.
        Note that the trial_id is a unique signature of the configuraiton.
        So if two VWTrials are associated with the same config, they will have the same trial_id
        (although not the same searcher_trial_id).
        searcher_trial_id will be used in suggest()
    """
    # ****the following constants are used when generating new challengers in
    # the _query_config_oracle function
    # how many item to add when doing the expansion
    # (i.e. how many interaction items to add at each time)
    POLY_EXPANSION_ADDITION_NUM = 1
    # the order of polynomial expansions to add based on the given seed interactions
    EXPANSION_ORDER = 2
    # the number of new challengers with new numerical hyperparamter configs
    NUMERICAL_NUM = 2

    # In order to use CFO, a loss name and loss values of configs are need
    # since CFO in fact only requires relative loss order of two configs to perform
    # the update, a pseudo loss can be used as long as the relative performance orders
    # of different configs are perserved. We set the loss of the init config to be
    # a large value (CFO_SEARCHER_LARGE_LOSS), and set the loss of the better config as
    # 0.95 of the previous best config's loss.
    # NOTE: this setting depends on the assumption that  (and thus
    # _query_config_oracle) is only triggered when a better champion is found.
    CFO_SEARCHER_METRIC_NAME = 'pseudo_loss'
    CFO_SEARCHER_LARGE_LOSS = 1e6

    # the random seed used in generating numerical hyperparamter configs (when CFO is not used)
    NUM_RANDOM_SEED = 111

    CHAMPION_TRIAL_NAME = 'champion_trial'
    TRIAL_CLASS = VowpalWabbitTrial

    def __init__(self,
                 init_config: Dict,
                 space: Optional[Dict] = None,
                 metric: Optional[str] = None,
                 mode: Optional[str] = None,
                 random_seed: Optional[int] = 2345,
                 online_trial_args: Optional[Dict] = {},
                 nonpoly_searcher_name: Optional[str] = 'CFO'
                 ):
        '''Constructor

        Args:
            init_config: dict
            space: dict
            metric: str
            mode: str
            random_seed: int
            online_trial_args: dict
            nonpoly_searcher_name: A string to specify the search algorithm
                for nonpoly hyperparameters
        '''
        self._init_config = init_config
        self._space = space
        self._seed = random_seed
        self._online_trial_args = online_trial_args
        self._nonpoly_searcher_name = nonpoly_searcher_name

        self._random_state = np.random.RandomState(self._seed)
        self._searcher_for_nonpoly_hp = {}
        self._space_of_nonpoly_hp = {}
        # dicts to remember the mapping between searcher_trial_id and trial_id
        self._searcher_trialid_to_trialid = {}  # key: searcher_trial_id, value: trial_id
        self._trialid_to_searcher_trial_id = {}  # value: trial_id, key: searcher_trial_id
        self._challenger_list = []
        # initialize the search in set_search_properties
        self.set_search_properties(config={self.CHAMPION_TRIAL_NAME: None}, init_call=True)
        logger.debug('using random seed %s in config oracle', self._seed)

    def set_search_properties(self, metric: Optional[str] = None,
                              mode: Optional[str] = None,
                              config: Optional[Dict] = {},
                              init_call: Optional[bool] = False):
        """Construct search space with given config, and setup the search
        """
        super().set_search_properties(metric, mode, config)
        # *********Use ConfigOralce (i.e, self._generate_new_space to generate list of new challengers)
        logger.info('champion trial %s', config)
        champion_trial = config.get(self.CHAMPION_TRIAL_NAME, None)
        if champion_trial is None:
            champion_trial = self._create_trial_from_config(self._init_config)
        # generate a new list of challenger trials
        new_challenger_list = self._query_config_oracle(champion_trial.config,
                                                        champion_trial.trial_id,
                                                        self._trialid_to_searcher_trial_id[champion_trial.trial_id])
        # add the newly generated challengers to existing challengers
        # there can be duplicates and we check duplicates when calling next_trial()
        self._challenger_list = self._challenger_list + new_challenger_list
        # add the champion as part of the new_challenger_list when called initially
        if init_call:
            self._challenger_list.append(champion_trial)
        logger.critical('Created challengers from champion %s', champion_trial.trial_id)
        logger.critical('New challenger size %s, %s', len(self._challenger_list),
                        [t.trial_id for t in self._challenger_list])

    def next_trial(self):
        """Return a trial from the _challenger_list
        """
        next_trial = None
        if self._challenger_list:
            next_trial = self._challenger_list.pop()
        return next_trial

    def _create_trial_from_config(self, config, searcher_trial_id=None):
        if searcher_trial_id is None:
            searcher_trial_id = Trial.generate_id()
        trial = self.TRIAL_CLASS(config, **self._online_trial_args)
        self._searcher_trialid_to_trialid[searcher_trial_id] = trial.trial_id
        # only update the dict when the trial_id does not exist
        if trial.trial_id not in self._trialid_to_searcher_trial_id:
            self._trialid_to_searcher_trial_id[trial.trial_id] = searcher_trial_id
        return trial

    def _query_config_oracle(self, seed_config, seed_config_trial_id,
                             seed_config_searcher_trial_id=None) -> List[Trial]:
        """Give the seed config, generate a list of new configs (which are supposed to include
        at least one config that has better performance than the input seed_config)
        """
        # group the hyperparameters according to whether the configs of them are independent
        # with the other hyperparameters
        hyperparameter_config_groups = []
        searcher_trial_ids_groups = []
        nonpoly_config = {}
        for k, v in seed_config.items():
            config_domain = self._space[k]
            if isinstance(config_domain, PolynomialExpansionSet):
                # get candidate configs for hyperparameters of the PolynomialExpansionSet type
                partial_new_configs = self._generate_independent_hp_configs(k, v, config_domain)
                if partial_new_configs:
                    hyperparameter_config_groups.append(partial_new_configs)
                    # does not have searcher_trial_ids
                    searcher_trial_ids_groups.append([])
            elif isinstance(config_domain, Float) or isinstance(config_domain, Categorical):
                # otherwise we need to deal with them in group
                nonpoly_config[k] = v
                if k not in self._space_of_nonpoly_hp:
                    self._space_of_nonpoly_hp[k] = self._space[k]

        # -----------generate partial new configs for non-PolynomialExpansionSet hyperparameters
        if nonpoly_config:
            new_searcher_trial_ids = []
            partial_new_nonpoly_configs = []
            if 'CFO' in self._nonpoly_searcher_name:
                if seed_config_trial_id not in self._searcher_for_nonpoly_hp:
                    self._searcher_for_nonpoly_hp[seed_config_trial_id] = CFO(space=self._space_of_nonpoly_hp,
                                                                              points_to_evaluate=[nonpoly_config],
                                                                              metric=self.CFO_SEARCHER_METRIC_NAME,
                                                                              )
                    # initialize the search in set_search_properties
                    self._searcher_for_nonpoly_hp[seed_config_trial_id].set_search_properties(
                        config={'metric_target': self.CFO_SEARCHER_LARGE_LOSS})
                    # We need to call this for once, such that the seed config in points_to_evaluate will be called
                    # to be tried
                    self._searcher_for_nonpoly_hp[seed_config_trial_id].suggest(seed_config_searcher_trial_id)
                # assuming minimization
                if self._searcher_for_nonpoly_hp[seed_config_trial_id].metric_target is None:
                    pseudo_loss = self.CFO_SEARCHER_LARGE_LOSS
                else:
                    pseudo_loss = self._searcher_for_nonpoly_hp[seed_config_trial_id].metric_target * 0.95
                pseudo_result_to_report = {}
                for k, v in nonpoly_config.items():
                    pseudo_result_to_report['config/' + str(k)] = v
                pseudo_result_to_report[self.CFO_SEARCHER_METRIC_NAME] = pseudo_loss
                pseudo_result_to_report['time_total_s'] = 1
                self._searcher_for_nonpoly_hp[seed_config_trial_id].on_trial_complete(seed_config_searcher_trial_id,
                                                                                      result=pseudo_result_to_report)
                while len(partial_new_nonpoly_configs) < self.NUMERICAL_NUM:
                    # suggest multiple times
                    new_searcher_trial_id = Trial.generate_id()
                    new_searcher_trial_ids.append(new_searcher_trial_id)
                    suggestion = self._searcher_for_nonpoly_hp[seed_config_trial_id].suggest(new_searcher_trial_id)
                    if suggestion is not None:
                        partial_new_nonpoly_configs.append(suggestion)
                logger.info('partial_new_nonpoly_configs %s', partial_new_nonpoly_configs)
            else:
                raise NotImplementedError
            if partial_new_nonpoly_configs:
                hyperparameter_config_groups.append(partial_new_nonpoly_configs)
                searcher_trial_ids_groups.append(new_searcher_trial_ids)
        # ----------- coordinate generation of new challengers in the case of multiple groups
        new_trials = []
        for i in range(len(hyperparameter_config_groups)):
            logger.info('hyperparameter_config_groups[i] %s %s',
                        len(hyperparameter_config_groups[i]),
                        hyperparameter_config_groups[i])
            for j, new_partial_config in enumerate(hyperparameter_config_groups[i]):
                new_seed_config = seed_config.copy()
                new_seed_config.update(new_partial_config)
                # For some groups of the hyperparameters, we may have already generated the
                # searcher_trial_id. In that case, we only need to retrieve the searcher_trial_id
                # instead of generating it again. So we do not generate searcher_trial_id and
                # instead set the searcher_trial_id to be None. When creating a trial from a config,
                # a searcher_trial_id will be generated if None is provided.
                # TODO: An alternative option is to generate a searcher_trial_id for each partial config
                if searcher_trial_ids_groups[i]:
                    new_searcher_trial_id = searcher_trial_ids_groups[i][j]
                else:
                    new_searcher_trial_id = None
                new_trial = self._create_trial_from_config(new_seed_config, new_searcher_trial_id)
                new_trials.append(new_trial)
        logger.info('new_configs %s', [t.trial_id for t in new_trials])
        return new_trials

    def _generate_independent_hp_configs(self, hp_name, current_config_value, config_domain) -> List:
        if isinstance(config_domain, PolynomialExpansionSet):
            seed_interactions = list(current_config_value) + list(config_domain.init_monomials)
            logger.critical('Seed namespaces (singletons and interactions): %s', seed_interactions)
            logger.info('current_config_value %s %s', current_config_value, seed_interactions)
            configs = self._generate_poly_expansion_sets(seed_interactions,
                                                         self.EXPANSION_ORDER,
                                                         config_domain.allow_self_inter,
                                                         config_domain.highest_poly_order,
                                                         self.POLY_EXPANSION_ADDITION_NUM,
                                                         )
        else:
            raise NotImplementedError
        configs_w_key = [{hp_name: hp_config} for hp_config in configs]
        return configs_w_key

    def _generate_poly_expansion_sets(self, seed_interactions, order, allow_self_inter,
                                      highest_poly_order, interaction_num_to_add):
        champion_all_combinations = self._generate_all_comb(seed_interactions, order, allow_self_inter, highest_poly_order)
        space = sorted(list(itertools.combinations(
                       champion_all_combinations, interaction_num_to_add)))
        self._random_state.shuffle(space)
        candidate_configs = [set(seed_interactions) | set(item) for item in space]
        final_candidate_configs = []
        for c in candidate_configs:
            new_c = set([e for e in c if len(e) > 1])
            final_candidate_configs.append(new_c)
        return final_candidate_configs

    @staticmethod
    def _generate_all_comb(seed_interactions: list, seed_interaction_order: int,
                           allow_self_inter: Optional[bool] = False,
                           highest_poly_order: Optional[int] = None):
        """Generate new interactions by doing up to seed_interaction_order on the seed_interactions

        Args:
            seed_interactions (List[str]): the see config which is a list of interactions string
            (including the singletons)
            seed_interaction_order (int): the maxmum order of interactions to perform on the seed_config
            allow_self_inter (bool): whether self-interaction is allowed
                e.g. if set False, 'aab' will be considered as 'ab', i.e. duplicates in the interaction
                string are removed.
            highest_poly_order (int): the highest polynomial order allowed for the resulting interaction.
                e.g. if set 3, the interaction 'abcd' will be excluded.
        """

        def get_interactions(list1, list2):
            """Get combinatorial list of tuples
            """
            new_list = []
            for i in list1:
                for j in list2:
                    # each interaction is sorted. E.g. after sorting
                    # 'abc' 'cba' 'bca' are all 'abc'
                    # this is done to ensure we can use the config as the signature
                    # of the trial, i.e., trial id.
                    new_interaction = ''.join(sorted(i + j))
                    if new_interaction not in new_list:
                        new_list.append(new_interaction)
            return new_list

        def strip_self_inter(s):
            """Remove duplicates in an interaction string
            """
            if len(s) == len(set(s)):
                return s
            else:
                # return ''.join(sorted(set(s)))
                new_s = ''
                char_list = []
                for i in s:
                    if i not in char_list:
                        char_list.append(i)
                        new_s += i
                return new_s

        interactions = seed_interactions.copy()
        all_interactions = []
        while seed_interaction_order > 1:
            interactions = get_interactions(interactions, seed_interactions)
            seed_interaction_order -= 1
            all_interactions += interactions
        if not allow_self_inter:
            all_interactions_no_self_inter = []
            for s in all_interactions:
                s_no_inter = strip_self_inter(s)
                if len(s_no_inter) > 1 and s_no_inter not in all_interactions_no_self_inter:
                    all_interactions_no_self_inter.append(s_no_inter)
            all_interactions = all_interactions_no_self_inter
        if highest_poly_order is not None:
            all_interactions = [c for c in all_interactions if len(c) <= highest_poly_order]
        logger.info('all_combinations %s', all_interactions)
        return all_interactions
