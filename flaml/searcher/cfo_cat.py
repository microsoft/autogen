'''!
 * Copyright (c) 2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from .flow2 import FLOW2
from .blendsearch import CFO


class FLOW2Cat(FLOW2):
    '''Local search algorithm optimized for categorical variables
    '''

    def _init_search(self):
        super()._init_search()
        self.step_ub = 1
        self.step = self.STEPSIZE * self.step_ub
        lb = self.step_lower_bound
        if lb > self.step:
            self.step = lb * 2
        # upper bound
        if self.step > self.step_ub:
            self.step = self.step_ub
        self._trunc = self.dim


class CFOCat(CFO):
    '''CFO optimized for categorical variables
    '''

    LocalSearch = FLOW2Cat
