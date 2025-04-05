
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, 
                             QPlainTextEdit, QShortcut, QSizePolicy, QSplitter, QMenu, QMainWindow, QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath, QFont, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSettings, QPointF, QEvent, pyqtSignal

import datetime

TIMESTAMP_FORMAT = "%Y-%m-%d_%H:%M:%S.%f"



class ColorfulTextEdit(QPlainTextEdit):
    class FunctionType:
        regular     = 0
        transition  = 1
        trigger     = 2

    def __init__(self, parent=None):
        super().__init__(parent)

    def append_log_new_machine(self, machine_name, left_variable):
        self.appendHtml('<span style="color: #2ca20f; font-weight: bold;"> --------------------------- system restarted --------------------------- </span>')
        self.append_log(object_name=None, 
                                  function_name='StateMachine', 
                                  function_params=[machine_name],
                                  return_code=None,
                                  left_variable=left_variable)

    def append_log(self, object_name, function_name, function_params, return_code, left_variable=None, function_type=FunctionType.regular):
        now = datetime.datetime.now()
        timestamp = now.strftime(TIMESTAMP_FORMAT)

        color_ts = f'<span style="color: #2ca20f;">[{timestamp}]</span>'

        color_object_name = ''
        if object_name is not None:
            color_object_name = f'<span style="color: #302a36;">{object_name}.</span>'
        
        if function_type == ColorfulTextEdit.FunctionType.regular:
            color_func_name = f'<span style="color: #ff6833;">{function_name}</span>'
        elif function_type == ColorfulTextEdit.FunctionType.transition:
            color_func_name = f'<span style="color: #c6b100;">{function_name}</span>'
        elif function_type == ColorfulTextEdit.FunctionType.trigger:
            color_func_name = f'<span style="color: #030efa;">{function_name}</span>'

        color_function_params = None
        if function_params is not None:
            function_params_str = ', '.join(f"'{item}'" for item in function_params)
            color_function_params = f'<span style="color: #fa03af;">({function_params_str})</span>'
        else:
            color_function_params = f'<span style="color: #fa03af;">()</span>'
        
        color_return_code = ''
        if return_code is not None:
            if return_code is True:
                color_return_code = f'<span style="color: #9f33ff;">return</span> <span style="color: #2ca20f; font-weight: bold;">{return_code}</span>'
            else:
                color_return_code = f'<span style="color: #9f33ff;">return</span> <span style="color: red; font-weight: bold;">{return_code}</span>'

        color_left_variable = ''
        if left_variable is not None:
            color_left_variable = f'{left_variable} ='

        text = f"{color_ts} {color_left_variable} {color_object_name}{color_func_name}{color_function_params} {color_return_code}"

        self.appendHtml(text)