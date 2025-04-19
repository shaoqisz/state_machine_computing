import sys
from transitions import Machine
from transitions.core import MachineError
from transitions.extensions.states import Timeout, Tags, add_state_features
from transitions.extensions.factory import HierarchicalGraphMachine as HGMachine

@add_state_features(Timeout, Tags)
class CustomStateMachine(HGMachine):
    pass

class Matter(object):
    pass