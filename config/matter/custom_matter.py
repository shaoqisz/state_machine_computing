import sys

### trigger ###

def ShutDownCommand(actions):
    print(f'calling custom\'s trigger - {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    x    1    1    0')

def SwitchOnCommand(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    0    1    1    1')


def EnableOperationCommand(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    1    1    1    1')

def DisableVoltageCommand(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    x    x    0    x')

def QuickStopCommand(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    x    0    1    x')


def DisableOperationCommand(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('   0    -    -    -    0    1    1    1')


def AlarmOccurs(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')

def FaultReset(actions):
    print(f'calling custom\'s trigger {sys._getframe().f_code.co_name}()')
    actions.append('Bit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Controlword (OD 6040h)')
    actions.append('0->1    -    -    -    x    x    x    x')

### entry ###
def SwitchOnDisabledEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        1    x    -    0    0    0    0')

def ReadyToSwitchOnEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    1    -    0    0    0    1')

def SwitchOnEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    1    -    0    0    1    1')

def OperationEnabledEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('ServoOn()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    1    -    0    1    1    1')

def QuickStopEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    0    -    0    1    1    1')

def FaultReactionActiveEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    x    -    1    1    1    1')

def FaultEntry(actions):
    print(f'calling custom\'s entry - {sys._getframe().f_code.co_name}()')
    actions.append('     Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0 -- Statusword (OD 6041h)')
    actions.append('        0    x    -    1    0    0    0')

### transitions ###
def T0(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Device boot and initialization')
    return True

def T1(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Device boot and initialization')
    return True

def T2(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    return True

def T3(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo is ready for Servo On')
    return True
def T4(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo On')
    actions.append('Enters the mode in which the controller is allowed to issue a motion command')
    return True
def T5(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')
    return True

def T6(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    return True

def T7(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    return True

def T8(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')

    return True
def T9(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')

    return True
def T10(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    return True

def T11(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Quick stop function is enabled.')
    actions.append('The time setting for deceleration to a stop is different for the two errors.')
    actions.append('1. OD 2503h (P5.003)')
    actions.append('2. OD 6085h')
    return True
def T12(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')

    return True
def T13(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')

    return True
def T14(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Servo switches to Servo Off')
    return True

def T15(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    return True

def T16(actions):
    print(f'calling custom\'s transition - {sys._getframe().f_code.co_name}()')
    actions.append('Motion operation restart. The restart action is mode-dependent.')
    return True
