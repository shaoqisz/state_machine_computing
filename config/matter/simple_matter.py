import sys

def state1_state2_trans(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append("Custom action is executed during the transition.")
    return True