import sys
from transitions import Machine
from transitions.core import MachineError
from transitions.extensions.states import Timeout, Tags, add_state_features
from transitions.extensions.factory import HierarchicalGraphMachine as HGMachine



class AxisType():
    PMC     = 1,
    SPMC    = 2,
    VMC     = 3,



# to set the global settings
AXIS_TYPE = AxisType.SPMC
SHOW_THE_NOISY_INTERNAL_TRANSITIONS = True

class AxisMode():
    AXIS_MODE_UNKNOWN = 0
    AXIS_MODE_PTP = 1
    AXIS_MODE_JOG = 2


@add_state_features(Timeout, Tags)
class CustomStateMachine(HGMachine):
    pass

class Matter(object):
    def __init__(self):
        self.bServoPowerOn = False
        self.axisMode = AxisMode.AXIS_MODE_UNKNOWN
        self.bBrakeEngagedStatus = False
        self.waitForStartMotionTimeMs_is_timeout = False
        self.deltaPosAbs_greater_than_inPositionThresholdMicrons = True
        self.has_collision = False

    def isJogMode(self) -> bool:
        return self.axisMode == AxisMode.AXIS_MODE_JOG

    def isPtpMode(self) -> bool:
        return self.axisMode == AxisMode.AXIS_MODE_PTP
    
    def XMCHomedInPositionState_entry(self) -> None:
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}')

    def XMCWaitCouchTypeITrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check the couch type, if couch type is identified, guard will return false to block this internal transition')
        return False
    def XMCWaitCouchTypeToPowerUpTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check the couch type, if couch type is identified, guard will return true to allow this transition')
        return True
    def XMCAxisPowerUpITrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check the result of checkAxisConnection(), that to check the SDO of CANOPEN_AXIS_IDENTITY_OBJECT_SI.')
        return False
    def XMCAxisPowerUpToInitializeAxisNTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check checkAxisConnection(), isAxisInitialized() and isAxisOperational()')
        return True
    def XMCAxisPowerUpToAxisInitializedNTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() ...')
        return True
    def XMCInitializeAxisITrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check if isAxisInitialized() and isAxisOperational()')
        return False
    def XMCInitializeAxisToInitializedTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will check if isAxisInitialized() and isAxisOperational()')
        return True
    def XMCCouchEstopClosedITrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return true all the time ')
        return True
    def XMCAxisInitializedToWaitForMinSpeedNTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return true almost all the time')
        return True
    def XMCServoPowerWaitMinSpeedToPowerCheckTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return true almost all the time')
        return True

    def XMCServoPowerCheckITrans(self):
        if self.bServoPowerOn == False:
            print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return True due to bServoPowerOn == False, then call changeStateToEnableOperation trying to servo on')
            return True
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return False due to bServoPowerOn == True')
        return False

    def XMCServoPowerCheckToRecoveryTrans(self):
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() ...')
        return False

    def XMCServoPowerCheckToPtpWaitModeNTrans(self):
        if self.bServoPowerOn == True:
            print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return True due to bServoPowerOn == True')
            return True
        
        print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return False due to bServoPowerOn == False')
        return False
    
    def XMCHomedPtpJogMoveReqITrans(self):
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will clear fault if EE switch was triggered, and check if it has collision.')
        return self.has_collision

    ## jog
    def XMCHomedInPositionToJogWaitModeNTrans(self):
        print(f'[JOG] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will clear fault if EE switch was triggered, and check if it has collision, send VMC_ONE_SPEED_JOG_ANS to CouchMgr')
        return not self.has_collision
    ## ptp
    def XMCHomedInPositionToPtpWaitModeNTrans(self):
        print(f'[PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will send VMC_PET_GO_VERT_MOVE_ANS, COUCH_REPORT_VERT_POS_BKST/COUCH_PET_REPORT_SUBFRAME_POS_BKST/COUCH_REPORT_HOR_POS_BKST to CouchMgr, and check if the direction has collision')
        return not self.has_collision


    # jog
    def XMCHomedJogWaitModeToWaitForStartMotionTrans(self):
        prefix = f'[JOG] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard()'
        if self.bBrakeEngagedStatus:
            print(f'{prefix} return False, due to bBrakeEngagedStatus={self.bBrakeEngagedStatus}')
            return False
        print(f'{prefix} return True, due to bBrakeEngagedStatus={self.bBrakeEngagedStatus}, and call ptpmove()')
        return True
    


    # jog or ptp
    def XMCHomedWaitForStartMotionTrans(self):
        if self.waitForStartMotionTimeMs_is_timeout == True:
            print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return True, to test if waitForStartMotionTimeMs was timeout for VMC, SPMC=500ms, PMC=100ms')
            return True
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() return False, to test if waitForStartMotionTimeMs was not timeout for VMC, SPMC=500ms, PMC=100ms')
        return False
    
    def XMCHomedMovingUpdateErrITrans(self):
        if AXIS_TYPE == AxisType.VMC:
            print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() always return True, to test if startMovingTimeMs was timeout for 200ms')
            return True
        return False

    def XMCHomedWaitForStartMotionToMovingTrans(self):
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() always return True')
        return True
    

    def XMCHomedMovingITrans(self):
        ret = self.deltaPosAbs_greater_than_inPositionThresholdMicrons
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() send COUCH_REPORT_VERT_POS_BKST/COUCH_PET_REPORT_SUBFRAME_POS_BKST/COUCH_REPORT_HOR_POS_BKST to CouchMgr, and returns {ret}, due to deltaPosAbs_greater_than_inPositionThresholdMicrons={self.deltaPosAbs_greater_than_inPositionThresholdMicrons}')
        return ret

    def XMCHomedMovingToInPositionBackupNTrans(self):
        ret = not self.deltaPosAbs_greater_than_inPositionThresholdMicrons
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() returns not deltaPosAbs_greater_than_inPositionThresholdMicrons={ret}')
        return ret

    def XMCHomedMovingToInPositionNTrans(self):
        print(f'[JOG/PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which will update the current position and check if it is a true in position, now we always return true for simply')
        return True



    ## jog
    def XMCHomedJogWaitModeITrans(self) -> bool:
        ret = (not self.isJogMode())
        print(f'[JOG] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which returns {ret}, due to isJogMode={self.isJogMode()}')
        return ret
    ## ptp
    def XMCHomedPtpWaitModeITrans(self) -> bool:
        ret = (not self.isPtpMode())
        print(f'[PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard() which returns {ret}, due to isPtpMode={self.isPtpMode()}')
        return ret

    ## jog
    def XMCHomedJogWaitModeToWaitForStartMotionBackupTrans(self) -> bool:
        prefix = f'[JOG] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard()'
        ret = False
        if self.isJogMode():
            ret = True

        if AXIS_TYPE == AxisType.VMC and self.bBrakeEngagedStatus:
            ret = False

        if ret:
            print(f'{prefix} call ptpmove() and return {ret}, due to isJogMode={self.isJogMode()} and brake={self.bBrakeEngagedStatus}.')
        else:
            print(f'{prefix} return {ret}, due to isJogMode={self.isJogMode()} and brake={self.bBrakeEngagedStatus}')

        return ret
    
    ## ptp 
    def XMCHomedPtpWaitModeToWaitForStartMotionBackupTrans(self) -> bool:
        prefix = f'[PTP] {sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} {sys._getframe().f_code.co_name}::guard()'
        ret = False
        if self.isPtpMode():
            ret = True

        if AXIS_TYPE == AxisType.VMC and self.bBrakeEngagedStatus:
            ret = False

        if ret:
            print(f'{prefix} call ptpmove() and return {ret}, due to isPtpMode={self.isPtpMode()} and brake={self.bBrakeEngagedStatus}.')
        else:
            print(f'{prefix} return {ret}, due to isPtpMode={self.isPtpMode()} and brake={self.bBrakeEngagedStatus}')

        return ret
    
    def XMCHomedInPositionMotionReqITrans(self) -> bool:
        return True


