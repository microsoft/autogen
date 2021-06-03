from .blendsearch import CFO, BlendSearch, BlendSearchTuner
from .flow2 import FLOW2
try:
    from .online_searcher import ChampionFrontierSearcher
except ImportError:
    print('need to install vowpalwabbit to use ChampionFrontierSearcher')
