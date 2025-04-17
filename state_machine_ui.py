import sys, os
import json
import math
import configparser
from enum import Enum 

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, 
                             QPlainTextEdit, QShortcut, QSizePolicy, QSplitter, QMenu, QMainWindow, QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath, QFontMetrics, QFont, QIcon, QKeySequence, QPalette
from PyQt5.QtCore import Qt, QSettings, QPointF, QEvent, pyqtSignal, QTimer
from transitions.core import MachineError


from state_machine_core import Matter, CustomStateMachine
from transitions.core import EventData

from conditions_table_view import TableViewContainsSearchWidget
from config_page import ConfigPage, Theme
from colorful_text_edit import ColorfulTextEdit, FunctionType
from text_edit_search import TextEditSearch

from state_machine_json_viewer import StateMachineJsonViewer


LEVEL_COLORS_WHITE_THEME = [
    Qt.GlobalColor.red,
    Qt.GlobalColor.darkGreen,
    Qt.GlobalColor.blue,
    Qt.GlobalColor.magenta,
    Qt.GlobalColor.darkBlue,
    Qt.GlobalColor.darkGray,
    Qt.GlobalColor.darkRed,
    Qt.GlobalColor.darkMagenta,
]

LEVEL_COLORS_BLACK_THEME = [
    Qt.GlobalColor.red,
    Qt.GlobalColor.darkGreen,
    Qt.GlobalColor.magenta,
    Qt.GlobalColor.darkYellow,
    Qt.GlobalColor.darkMagenta,
    Qt.GlobalColor.darkRed,
]

class State:
    def __init__(self, name, children=None, parent=None):
        self.name = name
        self.children = children if children else []
        self.parent = parent
        self.rect = None
        self.dragging = False
        self.drag_offset = None
        self.level = 0 if parent is None else parent.level + 1
        self.outgoing_transitions = []
        self.color = None
        self.name_rect = None

        self.enter_list = None
        self.exit_list = None

# class StateConversion(Enum):
#     explicit = 0
#     implicit = 1

#     @property
#     def capitalized_name(self):
#         return self.name.capitalize()

class StateMachineWidget(QWidget):

    called_trigger_signal = pyqtSignal(str)
    called_condition_signal = pyqtSignal(str, str, str, bool)
    called_enter_state_signal = pyqtSignal(str, str, str)
    called_exit_state_signal = pyqtSignal(str, str, str)

    called_set_initial_state_signal = pyqtSignal(str)
    called_new_state_machine_signal = pyqtSignal(str)

    def __init__(self, icon=None):
        super().__init__()
        
        self.original_matter_attributes = set(dir(Matter))

        self.icon = icon

        self.set_white_theme()

        self.rect_2_name_margin = 10

        self.warning_error_msg_box = QMessageBox()
        self.warning_error_msg_box.setWindowIcon(self.icon)
        self.warning_error_msg_box.setIcon(QMessageBox.Warning)
        self.warning_error_msg_box.setStandardButtons(QMessageBox.Ok)

        self.animation_enabled = False

        self.transitions_timer = QTimer()
        self.transitions_timer_is_running = False
        
        self.hightlight_state = None
        self.weak_state = None

        self.focus_state = None
        self.focus_transition = None
        self.current_state = None

        self.is_dragging_all = False
        self.skip_context_menu_event_once = True
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 5.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.STATES_CONFIG = None
        self.TRANSITIONS_CONFIG_FOLDER = None

        self.font = QFont()
        self.font.setPointSize(10)

        self.merged_transitions = {}

        self.states = []
        
        self.json_states = None
        self.json_transitions = None

    def set_animation(self, animation_enabled):
        # print(f'animation_enabled={animation_enabled}')
        self.animation_enabled = animation_enabled

    def remove_all_new_matter_method(self):
        current_matter_attributes = set(dir(Matter))
        new_matter_attributes = current_matter_attributes - self.original_matter_attributes
        if new_matter_attributes:
            for attr in new_matter_attributes:
                if callable(getattr(Matter, attr)):
                    # print(f'del matter\'s attr={attr}')
                    delattr(Matter, attr)

    def reload_config(self, config_name, STATES_CONFIG, TRANSITIONS_CONFIG_FOLDER, enable_default_enter, enable_default_exit, custom_matter=None):
        try:
            self.remove_all_new_matter_method()

            # reset the offset when reload, scale can be remained
            self.offset_x = 0
            self.offset_y = 0

            self.called_new_state_machine_signal.emit(config_name)

            self.STATES_CONFIG = STATES_CONFIG
            self.TRANSITIONS_CONFIG_FOLDER = TRANSITIONS_CONFIG_FOLDER
            
            self.enable_default_enter = enable_default_enter
            self.enable_default_exit = enable_default_exit

            self.custom_matter = custom_matter

            self.font.setPointSize(10)

            self.merged_transitions = {}

            self.states = []
            
            self.json_states = self._load_states()
            self.json_transitions = self._load_transitions()

            if self.json_states is not None:
                self._build_states(self.json_states)

            self._load_state_positions()

            self._layout_states()

            initial_state_name = self._find_the_1st_initial_state(self.json_states)
            self.set_init_state(initial_state_name)

            if self.json_transitions is not None:
                # print(f'json_transitions={json_transitions}')
                self._connect_states(self.json_transitions)

        except Exception as e:
            self.warning_error_msg_box.setText(f'{e}')
            self.warning_error_msg_box.setWindowTitle('Error')
            self.warning_error_msg_box.exec()


    def set_init_state(self, state_name=None):
        self.called_set_initial_state_signal.emit(state_name)

        self.model = Matter()

        extra_args = dict(auto_transitions=False, show_conditions=True, show_state_attributes=True)
        if state_name is not None:
            extra_args['initial'] = state_name

        self.machine = CustomStateMachine(model=self.model,
                                          states=self.json_states,
                                          send_event=True,
                                          ignore_invalid_triggers=True, 
                                          transitions=self.json_transitions, 
                                          **extra_args)
        
        # print(f'current={self.model.state}') 
        for state in self.states:
            if self.model.state == self.get_full_path(state):
                self.set_current_last_state(state, None)

        self.update()

    def save_settings(self, settings):
        settings.setValue(f"{self.__class__.__name__}/offset_x", self.offset_x)
        settings.setValue(f"{self.__class__.__name__}/offset_y", self.offset_y)
        settings.setValue(f"{self.__class__.__name__}/scale_factor", self.scale_factor)

    def load_settings(self, settings):
        offset_x = settings.value(f"{self.__class__.__name__}/offset_x")
        offset_y = settings.value(f"{self.__class__.__name__}/offset_y")
        scale_factor = settings.value(f"{self.__class__.__name__}/scale_factor")
        if scale_factor and offset_x and offset_y:
            self.offset_x = float(offset_x)
            self.offset_y = float(offset_y)
            self.scale_factor = float(scale_factor)

    def _adjust_all_states(self):
        for state in self.states:
            self._adjust_parent(state)
        self.update()

    def _find_the_1st_initial_state(self, state_list, parent_path=None):
        if state_list is None:
            return None

        if parent_path is None:
            parent_path = []

        initial_key = 'initial'

        for state_data in state_list:
            if isinstance(state_data, dict):
                current_parent_path = parent_path + [state_data['name']]
                if initial_key in state_data:
                    initial_state_name = state_data[initial_key]
                    # 查找初始状态对应的子状态字典
                    child_state_dict = next((child for child in state_data.get('children', [])
                                             if isinstance(child, dict) and child.get('name') == initial_state_name), None)
                    if child_state_dict:
                        # 递归查找子状态的初始状态
                        result = self._find_the_1st_initial_state([child_state_dict], current_parent_path)
                        if result:
                            return result
                    # 如果没有子状态或者没找到对应子状态字典，返回当前路径加上初始状态名
                    return '_'.join(current_parent_path + [initial_state_name])

                children = state_data.get('children', [])
                result = self._find_the_1st_initial_state(children, current_parent_path)
                if result is not None:
                    return result

        return None

    def state_rename_slot(self, names, old_state_name: str):
        if names is None or len(names) == 0:
            return

        parent_chain = None
        if len(names) >= 2:
            parent_chain = names[:-1]
            new_state_name = names[-1]
        else:
            new_state_name = names[-1]

        target_state = None
        if parent_chain is None:
            root_states = [state for state in self.states if state.parent is None]
            for root in root_states:
                if root.name == old_state_name:
                    target_state = root
                    break
        else:
            parent_state = self.find_state_by_parent_chain(key=parent_chain)
            if parent_state:
                for child in parent_state.children:
                    if child.name == old_state_name:
                        target_state = child
                        break

        if target_state:
            print(f'Rename state from {target_state.name} to {new_state_name}')
            target_state.name = new_state_name

        for state in self.states:
            state.outgoing_transitions.clear()
        self.merged_transitions.clear()

        if self.json_transitions is not None:
            self._connect_states(self.json_transitions)
        self._adjust_all_states()


    def state_added_slot(self, names):
        if names is None or len(names) < 2:
            return

        parent_chain = names[:-1]
        state_name = names[-1]

        parent_state = self.find_state_by_parent_chain(key=parent_chain)

        state = State(state_name, parent=parent_state)
        self.states.append(state)
        parent_state.children.append(state)

        self._layout_children(parent_state, parent_state.rect[0] + 20,  parent_state.rect[1] + 20)


        for state in self.states:
            state.outgoing_transitions.clear()
        self.merged_transitions.clear()

        if self.json_transitions is not None:
            self._connect_states(self.json_transitions)
        self._adjust_all_states()

    def state_removed_slot(self, names):
        if names is None or len(names) == 0:
            return

        parent_chain = None
        if len(names) >= 2:
            parent_chain = names[:-1]
            state_name = names[-1]
        else:
            state_name = names[-1]

        if parent_chain is None:
            root_states = [state for state in self.states if state.parent is None]
            for root in root_states[:]:  # 复制一份列表，避免在遍历过程中修改列表导致问题
                if root.name == state_name:
                    print(f'remove {root.name}')
                    # 递归删除子状态
                    self._recursive_remove_states(root)
                    if root in self.states:
                        self.states.remove(root)
        else:
            parent_state = self.find_state_by_parent_chain(key=parent_chain)
            print(f'#### removed parent_chain={parent_chain} state_name={state_name}, parent_state={parent_state.name}')

            for child in parent_state.children[:]:  # 复制一份列表，避免在遍历过程中修改列表导致问题
                if child.name == state_name:
                    print(f'remove {child.name}')
                    # 递归删除子状态
                    self._recursive_remove_states(child)
                    if child in self.states:
                        self.states.remove(child)
                    parent_state.children.remove(child)
                    break

        for state in self.states:
            state.outgoing_transitions.clear()
        self.merged_transitions.clear()

        if self.json_transitions is not None:
            self._connect_states(self.json_transitions)

        self._adjust_all_states()

    def _recursive_remove_states(self, state):
        # 先递归删除子状态
        for child in state.children[:]:
            self._recursive_remove_states(child)
            if child in self.states:
                self.states.remove(child)
        # 清空当前状态的子状态列表
        state.children = []

    def find_state_by_parent_chain(self, key):
        def recursive_search(states, current_chain):
            if not current_chain:
                return None
            current_name = current_chain[0]
            for state in states:
                if state.name == current_name:
                    if len(current_chain) == 1:
                        return state
                    else:
                        return recursive_search(state.children, current_chain[1:])
            return None

        return recursive_search(self.states, key)

    def _build_states(self, state_list, parent=None):
        for i, state_data in enumerate(state_list):
            if isinstance(state_data, dict):
                name:str = state_data['name']
                state = State(name, parent=parent)
                full_path = self.get_full_path(state)

                if '_' in name:
                    raise Exception(f'Found the underline in the state name `{name}`, which is not allowed.')
                
                if 'on_enter' in state_data:
                    enter_state_func_names = state_data['on_enter']
                    # print(f'enter_state_func_names={enter_state_func_names}')
                    if isinstance(enter_state_func_names, list):
                        for enter_state_func_name in enter_state_func_names:
                            self.setup_enter_state_function(enter_state_func_name)
                elif self.enable_default_enter is True:
                    default_enter_state_func_name = f'{full_path}::default_enter'
                    state_data['on_enter'] = [default_enter_state_func_name]
                    # print(f'default_enter_state_func_name={default_enter_state_func_name}')
                    self.setup_enter_state_function(default_enter_state_func_name)

                if 'on_exit' in state_data:
                    exit_state_func_names = state_data['on_exit']
                    # print(f'exit_state_func_names={exit_state_func_names}')
                    if isinstance(exit_state_func_names, list):
                        for exit_state_func_name in exit_state_func_names:
                            self.setup_exit_state_function(exit_state_func_name)

                elif self.enable_default_exit is True:
                    default_exit_state_func_name = f'{full_path}::default_exit'
                    state_data['on_exit'] = [default_exit_state_func_name]
                    # print(f'default_exit_state_func_name={default_exit_state_func_name}')
                    self.setup_exit_state_function(default_exit_state_func_name)

                if 'on_enter' in state_data:
                    state.enter_list = state_data['on_enter']

                if 'on_exit' in state_data:
                    state.exit_list = state_data['on_exit']
                
                children = state_data.get('children', [])
                self._build_states(children, state)
                state.children = [child for child in self.states if child.parent == state]
                self.states.append(state)
            elif isinstance(state_data, str):
                name:str = state_data
                state = State(name, parent=parent)
                self.states.append(state)

                if self.enable_default_enter is True or self.enable_default_exit is True:
                    state_dict = {"name": state_data}
                    state_list[i] = state_dict

                    full_path = self.get_full_path(state)
                    if self.enable_default_enter is True:
                        default_enter_state_func_name = f'{full_path}::default_enter'
                        state_dict['on_enter'] = [default_enter_state_func_name]
                        state.enter_list = [default_enter_state_func_name]
                        # print(f'default_enter_state_func_name={default_enter_state_func_name}')
                        self.setup_enter_state_function(default_enter_state_func_name)

                    if self.enable_default_exit is True:
                        default_exit_state_func_name = f'{full_path}::default_exit'
                        state_dict['on_exit'] = [default_exit_state_func_name]
                        state.exit_list =  [default_exit_state_func_name]
                        # print(f'default_exit_state_func_name={default_exit_state_func_name}')
                        self.setup_exit_state_function(default_exit_state_func_name)

    def _layout_states(self):
        default_w = 200
        default_h = 200
        root_x = 50
        root_y = 50
        for state in self.states:
            if state.parent is None:
                if state.rect is None:
                    state.rect = (root_x, root_y, default_w, default_h)
                self._layout_children(state, root_x + 20, root_y + 20)
                root_y += 220

    def _layout_children(self, parent, x, y):
        default_w = 200
        default_h = 40
        for child in parent.children:
            if child.rect is None:
                child.rect = (x, y, default_w, default_h)
            self._layout_children(child, x + 20, y + default_h + 10)
            y += default_h + 10

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # black background
        # painter.setBrush(QColor(0, 0, 0))
        # painter.drawRect(0, 0, self.width(), self.height())

        painter.translate(self.offset_x, self.offset_y)

        painter.scale(self.scale_factor, self.scale_factor)
        self.font.setPointSizeF(10*self.scale_factor)
        self.font.setBold(False)
        painter.setFont(self.font)

        # 找到根状态
        root_states = [state for state in self.states if state.parent is None]
        for root in root_states:
            self._draw_state(painter, root)

        # 绘制转换连线
        self._draw_transitions(painter)

    def set_state_rect_style(self, painter, state):
        pen_color = self.opposite_color
        pen_width = 2
        if self.focus_state is state:
            pen_color = state.color
            pen_width = 4

        if state == self.hightlight_state:
            painter.setBrush(Qt.GlobalColor.yellow)
            pen_color = Qt.GlobalColor.black
        elif state == self.weak_state:
            painter.setBrush(Qt.GlobalColor.gray)
        elif state.level == 0:
            painter.setBrush(self.root_state_color)
        else:
            painter.setBrush(Qt.GlobalColor.transparent)

        painter.setPen(QPen(pen_color, pen_width))

    def set_line_style(self, painter, state, transition_key):
        if self.focus_state is state or self.focus_transition == transition_key:
            pen = QPen(state.color, 4)
        else:
            pen = QPen(self.opposite_color, 1)

        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

    def set_arrow_style(self, painter, state):
        if self.focus_state is state:
            painter.setBrush(state.color)
            return 22
        painter.setBrush(Qt.GlobalColor.black)
        return 12

    def draw_trigger_name(self, x, y, painter, state, transition_key, triggers, conditions):
        is_focus = False
        if self.focus_transition == transition_key or self.focus_state is state:
            is_focus = True

        if is_focus is True:
            self.font.setBold(True)
            painter.setPen(QPen(FunctionType.trigger.color, 1))
        else:
            self.font.setBold(False)
            painter.setPen(QPen(self.opposite_color, 1))

        painter.setFont(self.font)
        painter.drawText(x, y, triggers)
        self.merged_transitions[transition_key]['triggers_pos'] = (x, y)

        if is_focus is True:
            painter.setPen(QPen(FunctionType.condition.color, 1))
            font_height = self.get_text_height()
            new_y = y + font_height
            painter.drawText(x, new_y, conditions)

    def set_current_last_state(self, current, last):

        self.hightlight_state = current
        self.weak_state = last

        self.focus_transition = (last, current)

        self.update()

    def set_black_theme(self):
        self.root_state_color = QColor('#1d1d1d') # Qt.GlobalColor.black # QColor('#2b2b2b')
        self.opposite_color = Qt.GlobalColor.white
        self.level_colors = LEVEL_COLORS_BLACK_THEME

    
    def set_white_theme(self):
        self.root_state_color = QColor('#f4f4f4') # Qt.GlobalColor.white
        self.opposite_color = Qt.GlobalColor.black
        self.level_colors = LEVEL_COLORS_WHITE_THEME

    def update_final_current_state(self):

        for state in self.states:
            if self.model.state == self.get_full_path(state):
                self.hightlight_state = state

        self.update()
        self.transitions_timer_is_running = False


    def set_source_conditions_focus(self, source_name, dest_name, conditions):
        for key, data in self.merged_transitions.items():
            _source = data['source']
            _dest = data['dest']

            source_full_name = self.get_full_path(_source)
            # dest_full_name = self.get_full_path(_dest)

            conditions_list = data['conditions']
            if source_full_name == source_name:
                result = any(_conditions == conditions for _conditions in conditions_list)
                if result is True:                    
                    # self.set_start_state(_source)
                    # print(f'source={_source.name} current={self.current_state.name} source_name={source_name}')
                    # assert(_source == self.current_state)
                    if self.animation_enabled is True:
                        self.transitions_timer.singleShot(150,   lambda current=None,  last=_source:  self.set_current_last_state(current, last))
                        self.transitions_timer.singleShot(400,   lambda current=_dest, last=_source:  self.set_current_last_state(current, last))
                        self.transitions_timer.singleShot(650,   lambda current=_dest, last=None:     self.set_current_last_state(current, last))
                        self.transitions_timer.singleShot(850 ,  lambda current=_dest, last=None:     self.update_final_current_state())
                    else:
                        self.set_current_last_state(current=_dest, last=None)
                        self.transitions_timer.singleShot(0 ,  lambda:self.update_final_current_state())

                    self.transitions_timer_is_running = True

    def _draw_state(self, painter : QPainter, state):
        # 0. 计算名字锚点长度
        x, y, w, h = state.rect
        anchor_width = self.get_text_width(state.name) + self.rect_2_name_margin
        anchor_x = x + self.rect_2_name_margin
        anchor_y = y + self.rect_2_name_margin
        anchor_height = self.get_text_height()
        anchor_x, anchor_y, anchor_width, anchor_height = [round(anchor_x), round(anchor_y), round(anchor_width), round(anchor_height)]
        state.name_rect = [anchor_x, anchor_y, anchor_width, anchor_height]

        # 1. 绘制矩形
        self.set_state_rect_style(painter, state)

        radius = 10
        if state.children is None or len(state.children) == 0:
            painter.drawRoundedRect(round(x), round(y), round(anchor_width+self.rect_2_name_margin*2), round(anchor_height+self.rect_2_name_margin*2), radius, radius)
        else:
            painter.drawRoundedRect(round(x), round(y), round(w), round(h), radius, radius)
        
        # 2. 绘制名字矩形
        color_index = min(state.level, len(self.level_colors) - 1)
        state.color = self.level_colors[color_index]
        painter.setBrush(self.level_colors[color_index])
        painter.drawRect(*state.name_rect)

        # 3. 绘制状态名
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(anchor_x + 5, anchor_y + anchor_height - round(self.rect_2_name_margin/2*self.scale_factor), state.name)

        # 4. 递归绘制子状态
        for child in state.children:
            self._draw_state(painter, child)

    def draw_curve(self, painter, color, start_x, start_y, end_x, end_y):
        # painter_2 = QPainter(self)
        painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充
        control_x, control_y = (start_x + end_x)//3, (start_y+end_y)//3
        
        painter.setPen(QPen(color, 2))
        path = QPainterPath()
        path.moveTo(start_x, start_y)
        path.quadTo(control_x, control_y, end_x, end_y)

        print(f'control=({control_x}, {control_y}) start=({start_x}, {start_y}) end=({end_x}, {end_y})')
        painter.drawPath(path)

    def _draw_transitions(self, painter):
        margin = 5
        drawn_pairs = []
        for key, data in self.merged_transitions.items():
            source = data['source']
            dest = data['dest']
            triggers = "|".join(data['triggers'])
            conditions = "|".join(data['conditions'])

            # 获取源状态的矩形信息和颜色
            source_x, source_y, source_w, source_h = source.name_rect

            # 获取目标状态的矩形信息
            dest_x, dest_y, dest_w, dest_h = dest.name_rect

            # 计算源状态和目标状态的中心
            source_center_x = source_x + source_w / 2
            source_center_y = source_y + source_h / 2
            dest_center_x = dest_x + dest_w / 2
            dest_center_y = dest_y + dest_h / 2

            # 计算连线的方向向量
            dx = dest_center_x - source_center_x
            dy = dest_center_y - source_center_y

            # 计算连线从源状态矩形边缘出发并加上 margin 的起点
            if abs(dx) > abs(dy):
                if dx > 0:
                    start_x = source_x + source_w + margin
                    start_y = source_center_y
                else:
                    start_x = source_x - margin
                    start_y = source_center_y
            else:
                if dy > 0:
                    start_x = source_center_x
                    start_y = source_y + source_h + margin
                else:
                    start_x = source_center_x
                    start_y = source_y - margin

            # 计算连线到达目标状态矩形边缘并加上 margin 的终点
            if abs(dx) > abs(dy):
                if dx > 0:
                    end_x = dest_x - margin
                    end_y = dest_center_y
                else:
                    end_x = dest_x + dest_w + margin
                    end_y = dest_center_y
            else:
                if dy > 0:
                    end_x = dest_center_x
                    end_y = dest_y - margin
                else:
                    end_x = dest_center_x
                    end_y = dest_y + dest_h + margin

            painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充

            if (source_x, source_y) == (dest_x, dest_y):
                # 1. 圆弧
                radius = 30  # 圆弧半径
                arc_center_x = start_x + radius
                arc_center_y = start_y
                start_angle = 180 * 16  # 起始角度，16 是 Qt 角度的缩放因子
                span_angle = -180 * 16  # 跨度角度，负号表示逆时针
                
                self.set_line_style(painter, source, key)

                painter.drawArc(int(arc_center_x - radius), int(arc_center_y - radius), int(radius * 2), int(radius * 2), start_angle, span_angle)

                # 2. 绘制箭头
                arrow_size = self.set_arrow_style(painter, source)

                end_angle = (start_angle + span_angle) / 16
                arrow_x = arc_center_x + radius * math.cos(math.radians(end_angle))
                arrow_y = arc_center_y + radius * math.sin(math.radians(end_angle))
                arrow_angle = math.radians(end_angle + 90)
                arrow_x1 = arrow_x - arrow_size * math.cos(arrow_angle - math.pi / 6)
                arrow_y1 = arrow_y - arrow_size * math.sin(arrow_angle - math.pi / 6)
                arrow_x2 = arrow_x - arrow_size * math.cos(arrow_angle + math.pi / 6)
                arrow_y2 = arrow_y - arrow_size * math.sin(arrow_angle + math.pi / 6)
                # painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充
                painter.drawPolygon(QPointF(arrow_x, arrow_y), QPointF(arrow_x1, arrow_y1), QPointF(arrow_x2, arrow_y2))

                # 3. trigger - condition name
                text_x = round(arc_center_x) - round(self.get_text_width(triggers) / 2)
                text_y = round(arc_center_y - radius - 15)  # 上移 15 像素

                self.draw_trigger_name(text_x, text_y, painter, source, key, triggers, conditions)
            else:
                # 1. 曲线 (贝塞尔曲线路径)
                offset = 0
                reverse_key = (dest, source)
                if reverse_key in self.merged_transitions:
                    if key in drawn_pairs or reverse_key in drawn_pairs:
                        offset = 50
                    else:
                        offset = -50
                        drawn_pairs.append(key)
                # print(f'key={source.name, dest.name} reverse_key={dest.name, source.name} offset={offset}')

                control_x = (start_x + end_x) / 2 + offset
                control_y1 = start_y + (end_y - start_y) * 0.2 + offset
                control_y2 = start_y + (end_y - start_y) * 0.8 + offset
                path = QPainterPath()
                path.moveTo(start_x, start_y)
                # 添加三次贝塞尔曲线
                path.cubicTo(control_x, control_y1, control_x, control_y2, end_x, end_y)

                self.set_line_style(painter, source, key)
                
                painter.drawPath(path)

                # 2. 绘制箭头
                arrow_size = self.set_arrow_style(painter, source)
                # 以最后的曲线斜率为箭头的方向
                angle = math.atan2(path.pointAtPercent(1.0).y() - path.pointAtPercent(0.9).y(), path.pointAtPercent(1.0).x() - path.pointAtPercent(0.9).x())
                arrow_x1 = end_x - arrow_size * math.cos(angle - math.pi / 6)
                arrow_y1 = end_y - arrow_size * math.sin(angle - math.pi / 6)
                arrow_x2 = end_x - arrow_size * math.cos(angle + math.pi / 6)
                arrow_y2 = end_y - arrow_size * math.sin(angle + math.pi / 6)
                # painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充
                painter.drawPolygon(QPointF(end_x, end_y), QPointF(arrow_x1, arrow_y1), QPointF(arrow_x2, arrow_y2))

                # 3. trigger and condition name
                mid_x = round(path.pointAtPercent(0.5).x()) - round(self.get_text_width(triggers) / 2)
                mid_y = round(path.pointAtPercent(0.5).y())

                self.draw_trigger_name(mid_x, mid_y - 15, painter, source, key, triggers, conditions)


    def wheelEvent(self, event):
        # 获取鼠标当前位置
        mouse_x = event.x()
        mouse_y = event.y()

        # 计算缩放因子
        scale_step = 1.1
        if event.angleDelta().y() > 0:
            new_scale = self.scale_factor * scale_step
        else:
            new_scale = self.scale_factor / scale_step

        # 限制缩放范围
        new_scale = max(self.min_scale, min(new_scale, self.max_scale))

        # 计算缩放前后鼠标位置对应的逻辑坐标
        old_logical_x = (mouse_x - self.offset_x) / self.scale_factor
        old_logical_y = (mouse_y - self.offset_y) / self.scale_factor

        # 计算新的偏移量，确保鼠标位置在缩放后保持不变
        new_offset_x = mouse_x - old_logical_x * new_scale
        new_offset_y = mouse_y - old_logical_y * new_scale

        # 更新缩放因子和偏移量
        self.scale_factor = new_scale
        self.offset_x = new_offset_x
        self.offset_y = new_offset_y

        # 重绘界面
        self._adjust_all_states()


    def contextMenuEvent(self, event):
        if self.skip_context_menu_event_once:
            self.skip_context_menu_event_once = False
            return

        state : State = self.inside_the_state(event.x(), event.y())
        if state is not None:
            menu = QMenu(self)

            copy_state_name_action = menu.addAction("Copy state name")
            copy_state_name_action.triggered.connect(lambda b, name=state.name: self.copy_name_from_menu_slot(b, name))

            menu.addSeparator()

            init_action = menu.addAction("Initial state")
            init_action.triggered.connect(lambda b, name=self.get_full_path(state): self.init_state_slot(name))

            menu.addSeparator()

            if state.enter_list is not None:
                gate_menu = QMenu('Enter gates', self)
                menu.addMenu(gate_menu)

                for i, enter_name in enumerate(state.enter_list):
                    gate_name_menu = QMenu(enter_name, self)
                    gate_menu.addMenu(gate_name_menu)

                    copy_gate_name_action = gate_name_menu.addAction("Copy")
                    copy_gate_name_action.triggered.connect(lambda b, name=enter_name: self.copy_name_from_menu_slot(b, name))

            if state.exit_list is not None:
                gate_menu = QMenu('Exit gates', self)
                menu.addMenu(gate_menu)

                for i, enter_name in enumerate(state.exit_list):
                    gate_name_menu = QMenu(enter_name, self)
                    gate_menu.addMenu(gate_name_menu)

                    copy_gate_name_action = gate_name_menu.addAction("Copy")
                    copy_gate_name_action.triggered.connect(lambda b, name=enter_name: self.copy_name_from_menu_slot(b, name))

            menu.exec_(event.globalPos())
            return

        transition = self.above_the_transition(event.x(), event.y())
        if transition is not None:
            menu = QMenu(self)
            _, triggers, conditions_list = transition

            triggers_list = triggers.split('|')

            for i, trigger in enumerate(triggers_list):
                sub_menu = QMenu(trigger, self)
                menu.addMenu(sub_menu)
                
                trigger_it_action = sub_menu.addAction(f'Trigger - [Condition: {conditions_list[i]}()]')
                trigger_it_action.triggered.connect(lambda b, name=trigger: self.trigger_slot(b, name))

                if len(triggers_list) > 1:
                    copy_trigger_action = sub_menu.addAction("Copy trigger name")
                    copy_trigger_action.triggered.connect(lambda b, name=trigger: self.copy_name_from_menu_slot(b, name))

                    copy_condition_action = sub_menu.addAction("Copy condition name")
                    copy_condition_action.triggered.connect(lambda b, name=conditions_list[i]: self.copy_name_from_menu_slot(b, name))

            menu.addSeparator()
            
            copy_triggers_action = menu.addAction("Copy triggers name")
            copy_triggers_action.triggered.connect(lambda b, name=triggers: self.copy_name_from_menu_slot(b, name))

            conditions = "|".join(conditions_list)
            copy_conditions_action = menu.addAction("Copy conditions name")
            copy_conditions_action.triggered.connect(lambda b, name=conditions: self.copy_name_from_menu_slot(b, name))

            menu.exec_(event.globalPos())
            return

    def copy_name_from_menu_slot(self, b, name):
        clipboard = QApplication.clipboard()
        clipboard.setText(name)

    def init_state_slot(self, name):
        # print(f'set_init_state name = {name}')
        self.set_init_state(name)

    def trigger_slot(self, b, name):
        self.trigger_transition(name)

    def inside_the_state(self, x, y):
        for state in reversed(self.states):
            
            [anchor_x, anchor_y, anchor_width, anchor_height] = state.name_rect

            screen_anchor_x = anchor_x * self.scale_factor + self.offset_x
            screen_anchor_y = anchor_y * self.scale_factor + self.offset_y
            screen_anchor_width = anchor_width * self.scale_factor
            screen_anchor_height = anchor_height * self.scale_factor

            if ((screen_anchor_x - self.rect_2_name_margin) <= x <= screen_anchor_x + self.rect_2_name_margin + screen_anchor_width and
                (screen_anchor_y - self.rect_2_name_margin) <= y <= screen_anchor_y + self.rect_2_name_margin + screen_anchor_height):
                return state

        return None
    
    def above_the_transition(self, x, y):
        for key, data in self.merged_transitions.items():
            source = data['source']
            dest = data['dest']
            triggers = "|".join(data['triggers'])
            conditions_list = data['conditions']
            conditions = "|".join(conditions_list)
            triggers_pos = data['triggers_pos']

            # .__text__ 文字绘制方式是从左下角开始
            screen_anchor_x = triggers_pos[0] * self.scale_factor + self.offset_x
            screen_anchor_y = triggers_pos[1] * self.scale_factor + self.offset_y

            screen_anchor_height = self.get_text_height() * self.scale_factor
            # not consider the conditions:
            screen_anchor_width = self.get_text_width(triggers) * self.scale_factor
            if (screen_anchor_x <= x <= screen_anchor_x + screen_anchor_width and
                (screen_anchor_y - screen_anchor_height)<= y <= screen_anchor_y):
                return key, triggers, conditions_list

        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.focus_transition = None
            self.focus_state = None

        state = self.inside_the_state(event.x(), event.y())
        if state is not None:

            if event.button() == Qt.LeftButton:
                state.dragging = True
                state.drag_start_x = event.x()
                state.drag_start_y = event.y()

            self.focus_state = state

        transition = self.above_the_transition(event.x(), event.y())
        if transition is not None:
            transition_key, triggers, connditions_list = transition
            self.focus_transition = transition_key
            # print(f'transition={transition_key, triggers, connditions_list}')

        if event.button() == Qt.RightButton:
            self.is_dragging_all = True
            self.last_pos = event.pos()

        self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging_all:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()
            self.offset_x += dx
            self.offset_y += dy
            self.last_pos = event.pos()

            self.skip_context_menu_event_once = True

            self.update()
        else:
            for state in self.states:
                if state.dragging:
                    # 计算逻辑坐标的移动量
                    dx_screen = event.x() - state.drag_start_x
                    dy_screen = event.y() - state.drag_start_y
                    dx_logical = dx_screen / self.scale_factor
                    dy_logical = dy_screen / self.scale_factor

                    # 更新状态的rect
                    x, y, w, h = state.rect
                    new_x = x + dx_logical
                    new_y = y + dy_logical
                    state.rect = (new_x, new_y, w, h)

                    # 移动子状态
                    self._move_children(state, dx_logical, dy_logical)

                    # 调整父状态的大小
                    self._adjust_parent(state)

                    # 更新拖拽起始位置
                    state.drag_start_x = event.x()
                    state.drag_start_y = event.y()

                    self.update()

    def _move_children(self, parent, dx, dy):
        for child in parent.children:
            x, y, w, h = child.rect
            child.rect = (x + dx, y + dy, w, h)
            self._move_children(child, dx, dy)

    def _adjust_parent(self, state):
        # print(f'{__name__}')        
        parent = state.parent
        while parent:
            all_children = self._get_all_children(parent)
            if all_children:
                # 初始化最小和最大值
                min_x = float('inf')
                min_y = float('inf')
                max_x = float('-inf')
                max_y = float('-inf')

                # 遍历所有子元素
                for child in all_children:
                    # 更新 min_x
                    if child.rect[0] < min_x:
                        min_x = child.rect[0]
                    # 更新 min_y
                    if child.rect[1] < min_y:
                        min_y = child.rect[1]
                    # 更新 max_x
                    if child.children is None or len(child.children) == 0:
                        current_max_x = child.rect[0] + self.get_text_width(child.name) + self.rect_2_name_margin*3
                        if current_max_x > max_x:
                            max_x = current_max_x
                        # 更新 max_y
                        current_max_y = round(child.rect[1]) + round(self.get_text_height()+self.rect_2_name_margin*2)
                        if current_max_y > max_y:
                            max_y = current_max_y

                    else:
                        current_max_x = child.rect[0] + child.rect[2]
                        if current_max_x > max_x:
                            max_x = current_max_x
                        # 更新 max_y
                        current_max_y = child.rect[1] + child.rect[3]
                        if current_max_y > max_y:
                            max_y = current_max_y

                # 增加一些边距
                margin = 10
                name_y_margin = 50
                new_x = min_x - margin
                new_y = min_y - margin - name_y_margin
                new_w = max_x - new_x + margin
                new_h = max_y - new_y + margin

                parent.rect = (new_x, new_y, new_w, new_h)
            parent = parent.parent

    def _get_all_children(self, state):
        all_children = []
        for child in state.children:
            all_children.append(child)
            all_children.extend(self._get_all_children(child))
        return all_children

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            for state in self.states:
                state.dragging = False
        elif event.button() == Qt.RightButton:
            self.is_dragging_all = False

    def _save_state_positions(self):
        def get_parent_chain(state):
            chain = []
            while state:
                chain.append(state.name)
                state = state.parent
            return chain

        def save_state_hierarchy(state_list, parent_chain):
            result = []
            for state in state_list:
                if isinstance(state, dict):
                    name = state['name']
                    children = state.get('children', [])
                    current_chain = [name] + parent_chain
                    state_obj = next((s for s in self.states if s.name == name and get_parent_chain(s) == current_chain), None)
                    if state_obj:
                        state_data = {
                            'name': name,
                            'rect': state_obj.rect,
                            'children': save_state_hierarchy(children, current_chain)
                        }
                        result.append(state_data)
                elif isinstance(state, str):
                    current_chain = [state] + parent_chain
                    state_obj = next((s for s in self.states if s.name == state and get_parent_chain(s) == current_chain), None)
                    if state_obj:
                        state_data = {
                            'name': state,
                            'rect': state_obj.rect
                        }
                        result.append(state_data)
            return result

        state_hierarchy = save_state_hierarchy(self._get_states_hierarchy(), [])
        if len(state_hierarchy) > 0:
            name_without_ext, file_extension = os.path.splitext(self.STATES_CONFIG)
            position_config = f'{name_without_ext}_with_position{file_extension}'
            with open(position_config, 'w') as f:
                json.dump(state_hierarchy, f, indent=4, ensure_ascii=False)


    def _load_state_positions(self):
        def get_parent_chain(state):
            chain = []
            while state:
                chain.append(state.name)
                state = state.parent
            return chain
        try:
            name_without_ext, file_extension = os.path.splitext(self.STATES_CONFIG)
            position_config = f'{name_without_ext}_with_position{file_extension}'

            with open(position_config, 'r') as f:
                state_hierarchy = json.load(f)

                def load_state_hierarchy(state_list, parent_chain):
                    for state_data in state_list:
                        name = state_data['name']
                        rect = state_data.get('rect')
                        current_chain = [name] + parent_chain
                        state_obj = next((s for s in self.states if s.name == name and get_parent_chain(s) == current_chain), None)
                        if state_obj and rect:
                            state_obj.rect = tuple(rect)
                        children = state_data.get('children', [])
                        load_state_hierarchy(children, current_chain)

                load_state_hierarchy(state_hierarchy, [])
        except FileNotFoundError:
            pass


    def _get_states_hierarchy(self):
        hierarchy = []
        for state in self.states:
            if state.parent is None:
                hierarchy.append(self._build_hierarchy(state))
        return hierarchy

    def _build_hierarchy(self, state):
        hierarchy = {'name': state.name}
        if state.children:
            hierarchy['children'] = [self._build_hierarchy(child) for child in state.children]
        return hierarchy

    def _load_states(self):
        try:
            with open(self.STATES_CONFIG, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            text = f'File {self.STATES_CONFIG} is not an valid JSON'
            print(text)
            self.warning_error_msg_box.setText(text)
            self.warning_error_msg_box.setWindowTitle('Warning')
            self.warning_error_msg_box.show()

    def _load_transitions(self):
        merged_json = []
        try:
            # 遍历指定目录下的所有文件
            for filename in os.listdir(self.TRANSITIONS_CONFIG_FOLDER):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.TRANSITIONS_CONFIG_FOLDER, filename)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            merged_json.extend(data)
                    except FileNotFoundError:
                        print(f"文件 {file_path} 未找到。")
                    except json.JSONDecodeError:
                        text = f'File {file_path} is not an valid JSON'
                        print(text)
                        self.warning_error_msg_box.setText(text)
                        self.warning_error_msg_box.setWindowTitle('Warning')
                        self.warning_error_msg_box.show()
            return merged_json
        except FileNotFoundError:
            return None

    def _connect_states(self, transitions):
        for transition in transitions:

            source_name = transition['source']
            dest_name = transition['dest']
            trigger = transition['trigger']
            conditions = transition['conditions']

            if len(dest_name) == 0:
                dest_name = source_name

            source_state = self._find_state_by_name(source_name)
            dest_state = self._find_state_by_name(dest_name)

            if source_state and dest_state:
                source_state.outgoing_transitions.append({
                    'trigger': trigger,
                    'dest': dest_state,
                    'conditions': conditions
                })

        for state in self.states:
            for transition in state.outgoing_transitions:
                source = state
                dest = transition['dest']
                key = (source, dest)
                if key not in self.merged_transitions:
                    self.merged_transitions[key] = {
                        'source': source,
                        'dest': dest,
                        'triggers': [transition['trigger']],
                        'conditions':[transition['conditions']],
                    }
                else:
                    self.merged_transitions[key]['triggers'].append(transition['trigger'])
                    self.merged_transitions[key]['conditions'].append(transition['conditions'])

    def _find_state_by_name(self, name, current_states=None):
        if current_states is None:
            current_states = self.states

        parts = name.split('_', 1)
        current_part = parts[0]
        remaining_name = parts[1] if len(parts) > 1 else None

        for state in current_states:
            if state.name == current_part:
                if remaining_name is None:
                    return state
                return self._find_state_by_name(remaining_name, state.children)

        return None

    def get_full_path(self, state):
        path_parts = []
        current_state = state
        while current_state:
            path_parts.append(current_state.name)
            current_state = current_state.parent
        # 反转列表以保证路径从根到当前 state
        path_parts.reverse()
        full_path = "_".join(path_parts)
        return full_path

    def trigger_transition(self, trigger):
        # to clear all the focus
        self.focus_transition = None
        self.focus_state = None

        try:
            if self.transitions_timer_is_running is True:
                # print(f'transitions_timer_is_running={self.transitions_timer_is_running}')
                # self.warning_error_msg_box.setText('Slow down, it\'s processing.')
                # self.warning_error_msg_box.setWindowTitle('Oops')
                # self.warning_error_msg_box.exec()
                return

            self.called_trigger_signal.emit(trigger)
            getattr(self.model, trigger)()

            # 重绘界面以更新当前状态显示
            self.update()
        except AttributeError as e:
            print(f"Invalid trigger: {trigger}")
        except MachineError as e:
            print(f"Invalid trigger: {trigger} {e}")

    def create_conditions_function(self, old_name, return_code, signal):

        def new_conditions_function(self, event: EventData):
            # print(f"source_name={event.state.name}")
            source = event.transition.source 
            dest = event.transition.dest
            signal.emit(source, dest, old_name, return_code)
            return return_code
        new_conditions_function.__name__ = old_name
        return new_conditions_function
    
    def create_custom_conditions_function(self, old_name, custom_conditions, signal):
        def new_conditions_function(self, event: EventData):
            # print(f"source_name={event.state.name}")
            source = event.transition.source 
            dest = event.transition.dest
            return_code = custom_conditions()
            signal.emit(source, dest, old_name, return_code)
            return return_code
        new_conditions_function.__name__ = old_name
        return new_conditions_function
    
    def create_enter_state_function(self, old_name, signal):
        def enter_state_function(self, event: EventData):
            source = event.transition.source 
            dest = event.transition.dest
            signal.emit(source, dest, old_name)
        enter_state_function.__name__ = old_name
        return enter_state_function
    
    def create_exit_state_function(self, old_name, signal):
        def exit_state_function(self, event: EventData):
            source = event.transition.source 
            dest = event.transition.dest
            signal.emit(source, dest, old_name)
        exit_state_function.__name__ = old_name
        return exit_state_function
    
    def setup_enter_state_function(self, enter_state_function_name):
        new_func = self.create_enter_state_function(enter_state_function_name, self.called_enter_state_signal)
        setattr(Matter, enter_state_function_name, new_func)

    def setup_exit_state_function(self, exit_state_function_name):
        new_func = self.create_exit_state_function(exit_state_function_name, self.called_exit_state_signal)
        setattr(Matter, exit_state_function_name, new_func)

    def setup_conditions_allowed_slot(self, conditions, allowed):
        if conditions is None:
            return
        
        if self.custom_matter is not None:
            custom_conditions = getattr(self.custom_matter, conditions)
            new_func = self.create_custom_conditions_function(conditions, custom_conditions, self.called_condition_signal)
        else:
            new_func = self.create_conditions_function(conditions, bool(allowed.lower() == 'yes'), self.called_condition_signal)

        setattr(Matter, conditions, new_func)

    def focus_slot(self, function_type, focus_name):
        if function_type == FunctionType.state:
            state_name = focus_name[0]
            for state in self.states:
                full_path = self.get_full_path(state)
                if full_path == state_name:
                    self.focus_state = state
                    self.focus_transition = None
                    self.update()
                    return

        elif function_type == FunctionType.trigger:
            source_name = focus_name[0]
            dest_name = focus_name[1]

            print(f'source_name={source_name} dest_name={dest_name}')

            source = None
            dest = None

            for state in self.states:
                full_path = self.get_full_path(state)
                if full_path == source_name:
                    source = state
                    for state in self.states:
                        full_path = self.get_full_path(state)
                        if full_path == dest_name:
                            dest = state
                            break
                    break
            if source is not None and dest is not None:
                self.focus_transition = (source, dest)
                self.focus_state = None
                self.update()
                return

    def get_text_width(self, text):
        new_font = QFont(self.font.family(), self.font.pointSize(), self.font.weight(), self.font.italic())
        new_font.setBold(False)
        font_metrics = QFontMetrics(new_font)
        text_length = font_metrics.horizontalAdvance(text)
        return text_length

    def get_text_height(self):
        new_font = QFont(self.font.family(), self.font.pointSize(), self.font.weight(), self.font.italic())
        new_font.setBold(False)
        font_metrics = QFontMetrics(new_font)
        font_height = font_metrics.height()
        return font_height

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app_name = 'State Machine Computing'
        self.setWindowTitle(app_name)
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('sm.png'))
        self.settings = QSettings("Philips", app_name)

        self.json_viewer = StateMachineJsonViewer()

        self.sm_border_widget = QWidget(self)
        self.sm_border_widget.setLayout(QVBoxLayout())

        # config
        self.config_page = ConfigPage(icon=self.windowIcon())

        # text edit
        self.text_edit = ColorfulTextEdit(self)
        self.text_edit_search = TextEditSearch(self.text_edit)

        # state machine
        self.state_machine = StateMachineWidget(icon=self.windowIcon())
        self.state_machine.called_trigger_signal.connect(self.trigger_name_slot)

        self.state_machine.called_condition_signal.connect(self.condition_message_slot)
        self.state_machine.called_enter_state_signal.connect(self.enter_state_message_slot)
        self.state_machine.called_exit_state_signal.connect(self.exit_state_message_slot)

        self.state_machine.called_set_initial_state_signal.connect(self.state_machine_init_slot)
        self.state_machine.called_new_state_machine_signal.connect(self.new_state_machine_slot)

        self.state_machine.reload_config(self.config_page.config_name_combobox.currentText(),
                                         self.config_page.main_resource_input.text(), 
                                         self.config_page.secondary_resource_input.text(),
                                         self.config_page.enable_default_enter_checkbox.isChecked(),
                                         self.config_page.enable_default_exit_checkbox.isChecked(),
                                         self.config_page.get_matter_lib())
        
        self.state_machine.set_animation(bool(self.config_page.animation_options.currentIndex()))

        # table view
        self.table_view_w_search = TableViewContainsSearchWidget()

        if self.state_machine.json_transitions is not None:
            self.table_view_w_search.set_transitions(self.config_page.config_name_combobox.currentText(), self.state_machine.json_transitions)
            for row, transition in enumerate(self.state_machine.json_transitions):
                condition = transition['conditions']
                self.state_machine.setup_conditions_allowed_slot(condition, 'Yes')
        else:
            self.table_view_w_search.clear_transitions()
        
        self._load_conditions_allowed()

        if self.state_machine.json_states is not None:
            self.json_viewer.set_json_data(self.state_machine.json_states)

        # theme
        self.set_theme(Theme(self.config_page.theme_options.currentIndex()))


        ##############

        self.right_widget = QWidget()
        self.right_widget.setLayout(QVBoxLayout())

        self.clear_btn = QPushButton('Clear')
        self.add_separator_btn = QPushButton('Add Separator')

        text_edit_bottom_widget_left = QWidget()
        text_edit_bottom_widget_left.setLayout(QHBoxLayout())

        text_edit_bottom_widget_right = QWidget()
        text_edit_bottom_widget_right.setLayout(QHBoxLayout())

        text_edit_bottom_widget_left.layout().addWidget(self.add_separator_btn)

        text_edit_bottom_widget_left.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
        text_edit_bottom_widget_left.layout().setContentsMargins(0,0,0,0)
        text_edit_bottom_widget_left.layout().setSpacing(5)

        text_edit_bottom_widget_right.layout().addWidget(self.clear_btn)

        text_edit_bottom_widget_right.layout().setAlignment(Qt.AlignmentFlag.AlignRight)
        text_edit_bottom_widget_right.layout().setContentsMargins(0,0,0,0)
        text_edit_bottom_widget_right.layout().setSpacing(5)

        self.text_edit_bottom_widget = QWidget()
        self.text_edit_bottom_widget.setLayout(QHBoxLayout())

        self.text_edit_bottom_widget.layout().addWidget(text_edit_bottom_widget_left)
        self.text_edit_bottom_widget.layout().addWidget(text_edit_bottom_widget_right)

        self.text_edit_bottom_widget.layout().setContentsMargins(0,0,0,0)
        self.text_edit_bottom_widget.layout().setSpacing(5)

        ###### 

        # layout
        main_widget = QWidget(self)

        main_widget.setLayout(QVBoxLayout())

        self.vert_spliter = QSplitter(Qt.Vertical, self)
        self.vert_spliter.setObjectName("vert_spliter")

        ################
        self.sm_border_widget.layout().addWidget(self.state_machine)
        margin = 4
        self.sm_border_widget.layout().setContentsMargins(margin, margin, margin, margin)
        # sm_border_widget.layout().setSpacing(0)
        ################


        self.right_widget.layout().addWidget(self.text_edit_search)
        self.right_widget.layout().addWidget(self.text_edit_bottom_widget)
        self.right_widget.layout().setContentsMargins(0,0,0,0)
        self.right_widget.layout().setSpacing(5)

        ####

        self.upper_hor_spliter = QSplitter(Qt.Horizontal, self)
        self.upper_hor_spliter.setObjectName("upper_hor_spliter")
        self.upper_hor_spliter.addWidget(self.sm_border_widget)
        self.upper_hor_spliter.addWidget(self.json_viewer)

        # self.upper_hor_spliter.setStyleSheet('border-radius: 10px; border: 2px solid gray;')


        self.hor_spliter = QSplitter(Qt.Horizontal, self)
        self.hor_spliter.setObjectName("hor_spliter")

        self.hor_spliter.addWidget(self.table_view_w_search)
        self.hor_spliter.addWidget(self.right_widget)
        ################

        self.vert_spliter.addWidget(self.upper_hor_spliter)
        self.vert_spliter.addWidget(self.hor_spliter)

        main_widget.layout().addWidget(self.vert_spliter)

        self.setCentralWidget(main_widget)

        ##############

        # menu
        menubar = self.menuBar()
        file_menu = QMenu("&File", self)
        settings_action = file_menu.addAction("Configure")
        settings_action.setShortcut('Ctrl+G')
        settings_action.triggered.connect(self.open_config_page)
        menubar.addMenu(file_menu)

        # load settings
        self.load_settings()

        # connections
        self.table_view_w_search.trigger_signal.connect(self.trigger_slot)
        self.config_page.config_changed_signal.connect(self.reload_config)
        self.config_page.animation_changed_signal.connect(self.state_machine.set_animation)
        self.config_page.theme_changed_signal.connect(self.set_theme)

        # self.table_view_w_search.init_state_signal.connect(self.init_state_slot)
        self.table_view_w_search.table_view.condition_allowed_changed.connect(self.state_machine.setup_conditions_allowed_slot)
        self.table_view_w_search.table_view.focus_signal.connect(self.state_machine.focus_slot)
        self.table_view_w_search.table_view.init_state_signal.connect(self.state_machine.init_state_slot)

        self.add_separator_btn.clicked.connect(lambda:self.text_edit.add_separator())
        self.clear_btn.clicked.connect(lambda: self.text_edit.clear())

        self.json_viewer.state_added_signal.connect(self.state_machine.state_added_slot)
        self.json_viewer.state_removed_signal.connect(self.state_machine.state_removed_slot)
        self.json_viewer.state_rename_signal.connect(self.state_machine.state_rename_slot)

        timer = QTimer()
        timer.singleShot(100, self.state_machine._adjust_all_states)

    def trigger_name_slot(self, trigger):
        self.text_edit.append_log(object_name=self.config_page.config_name_combobox.currentText(),
                                  function_name=trigger, 
                                  function_type=FunctionType.trigger)

    def condition_message_slot(self, source_name, dest_name, function_name, return_code):
        self.text_edit.append_log(object_name=self.config_page.config_name_combobox.currentText(),
                                  function_name=function_name, 
                                  function_params=[source_name.split("_")[-1], dest_name.split("_")[-1]], 
                                  return_code=return_code,
                                  function_type=FunctionType.condition)

        if return_code is True:
            self.state_machine.set_source_conditions_focus(source_name, dest_name, function_name)

    def enter_state_message_slot(self, source_name, dest_name, function_name):
        self.text_edit.append_log(object_name=self.config_page.config_name_combobox.currentText(),
                                  function_name=function_name, 
                                  function_type=FunctionType.state)
        
    def exit_state_message_slot(self, source_name, dest_name, function_name):
        self.text_edit.append_log(object_name=self.config_page.config_name_combobox.currentText(),
                                  function_name=function_name, 
                                  function_type=FunctionType.state)
        
    def state_machine_init_slot(self, state_name):
        self.text_edit.append_log(object_name=self.config_page.config_name_combobox.currentText(),
                                  function_name='set_initial_state', 
                                  function_params=[state_name])
        
    def new_state_machine_slot(self, sm_name):
        self.text_edit.append_log_new_machine(sm_name, self.config_page.config_name_combobox.currentText())

    def _save_conditions_allowed(self):
        conditions_allow = self.table_view_w_search.table_view._get_all_conditions_allowed()
        if conditions_allow is not None:
            
            config_name_conditions_allow = dict()
            config_name_conditions_allow['Conditions'] = conditions_allow

            conditions_allow_filename = f'{self.state_machine.TRANSITIONS_CONFIG_FOLDER}/conditions_allow.ini'
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read_dict(config_name_conditions_allow)
            with open(conditions_allow_filename, 'w') as f:
                config.write(f)

    def _load_conditions_allowed(self):
        conditions_allow_filename = f'{self.state_machine.TRANSITIONS_CONFIG_FOLDER}/conditions_allow.ini'
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(conditions_allow_filename)

        if 'Conditions' in config:
            conditions_allow = dict(config['Conditions'])
            self.table_view_w_search.table_view._set_all_conditions_allowed(conditions_allow)
            for condition in conditions_allow:
                self.state_machine.setup_conditions_allowed_slot(condition, conditions_allow[condition])


    def reload_config(self):
        self._save_conditions_allowed()

        self.state_machine._save_state_positions()
        self.state_machine.reload_config(self.config_page.config_name_combobox.currentText(),
                                         self.config_page.main_resource_input.text(), 
                                         self.config_page.secondary_resource_input.text(),
                                         self.config_page.enable_default_enter_checkbox.isChecked(),
                                         self.config_page.enable_default_exit_checkbox.isChecked(),
                                         self.config_page.get_matter_lib())

        if self.state_machine.json_transitions is not None:
            self.table_view_w_search.set_transitions(self.config_page.config_name_combobox.currentText(), self.state_machine.json_transitions)
            for row, transition in enumerate(self.state_machine.json_transitions):
                condition = transition['conditions']
                self.state_machine.setup_conditions_allowed_slot(condition, 'Yes')
        else:
            self.table_view_w_search.clear_transitions()

        self._load_conditions_allowed()

        if self.state_machine.json_states is not None:
            self.json_viewer.set_json_data(self.state_machine.json_states)


    def set_theme(self, current_theme):
        # print(f'current_theme={current_theme}')
        if current_theme == Theme.black:
            self.text_edit_search.set_black_theme()
            self.table_view_w_search.table_view.set_black_theme()
            self.json_viewer.set_black_theme()
            self.set_black_theme()
        elif current_theme == Theme.white:
            self.text_edit_search.set_white_theme()
            self.table_view_w_search.table_view.set_white_theme()
            self.json_viewer.set_white_theme()
            self.set_white_theme()

    def set_white_theme(self):
        style_sheet = """
                QPushButton {
                    background-color: rgba(0, 150, 180, 0.6);
                    color: white;
                    border: 2px solid rgba(255, 255, 255, 0.5);
                    padding: 5px 15px;
                    border-radius: 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 123, 200, 1);
                    border: 2px solid white;
                }
                QPushButton:pressed {
                    background-color: rgba(0, 86, 179, 1);
                    border: 2px solid white;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #999999;
                    border: 2px solid #b3b3b3;
                }
                QLineEdit {
                    background-color: white;
                    border: 1px solid #ccc;
                    padding: 3px 3px;
                    border-radius: 8px;
                    font-size: 12px;
                    min-height: 18px;
                    color: #333;
                }
                QLineEdit:hover {
                    background-color: #f5f5f5;
                    border: 2px solid #999;
                }
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #e0e0e0;
                }
                QMenu::separator {
                    height: 1px;
                    background: #cccccc;
                    margin: 5px 0;
                }
            """
        combobox_style_sheet = '''
            QComboBox {
                background-color: white;
                border: 1px solid #ccc;
                padding: 3px 6px;
                border-radius: 8px;
                font-size: 12px;
                min-height: 18px;
                color: #333;
            }
            QComboBox:hover {
                border: 2px solid #999;
            }
            QComboBox:disabled {
                background-color: #e0e0e0;
                color: #999;
                border: 1px solid #ccc;
            }
            QComboBox::down-arrow {
                image: url(res/theme/white/down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox::drop-down:disabled {
                background-color: #d0d0d0;
                color: #999;
                border-left-color: #ccc;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left-width: 1px;
                border-left-color: #ccc;
                border-left-style: solid;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #f0f0f0;
                margin-right: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ccc;
                padding: 2px;
                font-size: 12px;
                min-height: 20px;
                border-radius: 8px;
                color: #333;
            }
            QComboBox QAbstractItemView::item {
                padding: 3px 10px;
                color: #333;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #007bff;
                color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e9f6ff;
            }
        '''
        self.config_page.setStyleSheet(style_sheet+combobox_style_sheet)
        self.setStyleSheet(style_sheet+combobox_style_sheet)

        self.sm_border_widget.setStyleSheet("border: 2px solid gray; border-radius: 5px; background: white;")
        self.state_machine.set_white_theme()
    
    def set_black_theme(self):
        style_sheet = """
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border-radius: 8px;
            }
            QLabel {
                font-size: 14px;
                padding: 5px;
            }
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 3px 5px;
                font-size: 14px;
            }
            QLineEdit:hover {
                background-color: #444;
                border: 2px solid #888;
            }

            QCheckBox {
                font-size: 12px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 10px;
                height: 10px;
                background-color: white;
                border: 3px solid white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #2b2b2b;
                border: 3px solid white;
            }

            QPushButton {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 2px solid #444444;
                padding: 5px 15px;
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
                border: 2px solid #666666;
            }
            QPushButton:pressed {
                background-color: #4b4b4b;
                border: 2px solid #888888;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                color: #666666;
                border: 2px solid #333333;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444444;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #3b3b3b;
            }
            QMenu::separator {
                height: 1px;
                background: #444444;
                margin: 5px 0;
            }
    """

        combobox_style_sheet = '''
            QComboBox {
                background-color: #353333;
                border: 1px solid #666;
                padding: 3px 6px;
                border-radius: 8px;
                font-size: 12px;
                min-height: 18px;
                color: white;
            }
            QComboBox:hover {
                border: 2px solid #888;
            }
            QComboBox:disabled {
                background-color: #222;
                color: #666;
                border: 1px solid #444;
            }
            QComboBox::down-arrow {
                image: url(res/theme/black/down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox::drop-down:disabled {
                background-color: #111;
                color: #666;
                border-left-color: #444;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 26px;
                border-left-width: 1px;
                border-left-color: #666;
                border-left-style: solid;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background-color: #222;
                margin-right: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                border: 1px solid #666;
                padding: 2px;
                font-size: 12px;
                min-height: 20px;
                border-radius: 8px;
                color: white;
            }
            QComboBox QAbstractItemView::item {
                padding: 3px 10px;
                color: white;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #555;
                color: white;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #444;
            }
        '''
        self.config_page.setStyleSheet(style_sheet+combobox_style_sheet)
        self.setStyleSheet(style_sheet+combobox_style_sheet)

        self.sm_border_widget.setStyleSheet("border: 2px solid gray; border-radius: 5px; background: black;")
        # self.sm_border_widget.setStyleSheet("border: 2px solid gray; border-radius: 5px; background: #2b2b2b;")
        self.state_machine.set_black_theme()


    def open_config_page(self):
        self.config_page.show()
        self.config_page.activateWindow()

    def trigger_slot(self, row):
        if len(row) >= 5:
            # source = row[0]
            trigger = row[1]
            # conditions = row[2]
            # dest = row[3]
            # allowed = row[4]
            # print(f'trigger_slot source={source}, trigger={trigger}, conditions={conditions}, dest={dest}, allowed={allowed}')
            self.state_machine.trigger_transition(trigger)

    def closeEvent(self, event):
        self._save_conditions_allowed()
        
        self.state_machine._save_state_positions()

        self.save_settings()

        self.config_page.close()

        event.accept()

    def save_settings(self):
        # geometry
        self.settings.setValue("geometry", self.saveGeometry())

        # splitter
        self.settings.setValue(self.vert_spliter.objectName(), self.vert_spliter.saveState())
        self.settings.setValue(self.hor_spliter.objectName(), self.hor_spliter.saveState())
        self.settings.setValue(self.upper_hor_spliter.objectName(), self.upper_hor_spliter.saveState())

        # child widget settings
        self.state_machine.save_settings(self.settings)

    def load_settings(self):
        # geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # splitter
        splitter_state = self.settings.value(self.vert_spliter.objectName())
        if splitter_state:
            self.vert_spliter.restoreState(splitter_state)

        splitter_state = self.settings.value(self.hor_spliter.objectName())
        if splitter_state:
            self.hor_spliter.restoreState(splitter_state)

        splitter_state = self.settings.value(self.upper_hor_spliter.objectName())
        if splitter_state:
            self.upper_hor_spliter.restoreState(splitter_state)

        # child widget settings
        self.state_machine.load_settings(self.settings)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
