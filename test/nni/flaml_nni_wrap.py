from flaml.tune.searcher.blendsearch import BlendSearchTuner as BST


class BlendSearchTuner(BST):
    # for best performance pass low cost initial parameters here
    def __init__(self, low_cost_partial_config={"hidden_size": 128}):
        super.__init__(self, low_cost_partial_config=low_cost_partial_config)
