from flaml.searcher.blendsearch import BlendSearchTuner as BST


class BlendSearchTuner(BST):
    # for best performance pass low cost initial parameters here 
    def __init__(self, points_to_evaluate=[{"hidden_size":128}]):
        super.__init__(self, points_to_evaluate=points_to_evaluate)
