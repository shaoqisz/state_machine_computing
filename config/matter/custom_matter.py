import sys

def T0(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Device boot and initialization')
    return True

def T1(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Device boot and initialization')
    return True

def T2(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    return True

def T3(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo is ready for Servo On')
    return True
def T4(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo On')
    actions.append('Enters the mode in which the controller is allowed to issue a motion command')
    return True
def T5(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')
    return True

def T6(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    return True

def T7(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    return True

def T8(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')

    return True
def T9(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')

    return True
def T10(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    return True

def T11(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Quick stop function is enabled.')
    actions.append('The time setting for deceleration to a stop is different for the two errors.')
    actions.append('1. OD 2503h (P5.003)')
    actions.append('2. OD 6085h')
    return True
def T12(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')

    return True
def T13(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')

    return True
def T14(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Servo switches to Servo Off')
    return True

def T15(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    return True

def T16(actions):
    print(f'calling {sys._getframe().f_code.co_name}')
    actions.append('Motion operation restart. The restart action is mode-dependent.')
    return True
