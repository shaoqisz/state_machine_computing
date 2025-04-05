import sys, os
import json
import math
import configparser

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, QShortcut, QSizePolicy, QSplitter, QMenu, QMainWindow, QMessageBox
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath, QFont, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSettings, QPointF
from transitions.core import MachineError

from state_machine_core import Matter, CustomStateMachine

from conditions_table_view import TableViewContainsSearchWidget

from config_page import ConfigPage


# 定义不同层级的拖动锚点颜色
LEVEL_COLORS = [
    Qt.GlobalColor.red,
    Qt.GlobalColor.darkGreen,
    Qt.GlobalColor.blue,
    Qt.GlobalColor.darkYellow,
    Qt.GlobalColor.black,
    Qt.GlobalColor.darkGray,
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

class StateMachineWidget(QWidget):
    def __init__(self, STATES_CONFIG, TRANSITIONS_CONFIG_FOLDER, icon=None):
        super().__init__()

        self.icon = icon

        self.warning_error_msg_box = QMessageBox()
        self.warning_error_msg_box.setWindowIcon(self.icon)
        self.warning_error_msg_box.setIcon(QMessageBox.Warning)
        self.warning_error_msg_box.setStandardButtons(QMessageBox.Ok)
        
        self.focus_state = None
        self.is_dragging_all = False
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 5.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # self.STATES_CONFIG = './config/states/states_config.json'
        # self.TRANSITIONS_CONFIG_FOLDER = './config/transitions/pmc'

        self.STATES_CONFIG = STATES_CONFIG # './config/states/states_config.json'
        self.TRANSITIONS_CONFIG_FOLDER = TRANSITIONS_CONFIG_FOLDER # './config/transitions/pmc'


        self.font = QFont()
        self.font.setPointSize(10)

        self.merged_transitions = {}

        self.states = []
        
        self.json_states = self._load_states()
        self.json_transitions = self._load_transitions()

        if self.json_states is not None:
            self._build_states(self.json_states)

        self._load_state_positions()

        self._layout_states()

        self._adjust_all_states()

        initial_state_name = self._find_the_1st_initial_state(self.json_states)
        self.set_init_state(initial_state_name)

        if self.json_transitions is not None:
            # print(f'json_transitions={json_transitions}')
            self._connect_states(self.json_transitions)

    def reload_config(self, STATES_CONFIG, TRANSITIONS_CONFIG_FOLDER):
        self.STATES_CONFIG = STATES_CONFIG
        self.TRANSITIONS_CONFIG_FOLDER = TRANSITIONS_CONFIG_FOLDER
        self.font.setPointSize(10)

        self.merged_transitions = {}

        self.states = []
        
        self.json_states = self._load_states()
        self.json_transitions = self._load_transitions()

        if self.json_states is not None:
            self._build_states(self.json_states)

        self._load_state_positions()

        self._layout_states()

        self._adjust_all_states()

        initial_state_name = self._find_the_1st_initial_state(self.json_states)
        self.set_init_state(initial_state_name)

        if self.json_transitions is not None:
            # print(f'json_transitions={json_transitions}')
            self._connect_states(self.json_transitions)

    def set_init_state(self, state_name=None):
        self.model = Matter()
        extra_args = dict(auto_transitions=False, show_conditions=True, show_state_attributes=True)
        if state_name is not None:
            extra_args['initial'] = state_name

        self.machine = CustomStateMachine(model=self.model,
                                          states=self.json_states,
                                          ignore_invalid_triggers=True, 
                                          transitions=self.json_transitions, 
                                          **extra_args)
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
                    current_parent_path = current_parent_path + [state_data[initial_key]]
                    return '_'.join(current_parent_path)

                children = state_data.get('children', [])
                result = self._find_the_1st_initial_state(children, current_parent_path)
                if result is not None:
                    return result

        return None

    def _build_states(self, state_list, parent=None):
        for state_data in state_list:
            if isinstance(state_data, dict):
                name = state_data['name']
                children = state_data.get('children', [])
                state = State(name, parent=parent)
                self._build_states(children, state)
                state.children = [child for child in self.states if child.parent == state]
                self.states.append(state)
            elif isinstance(state_data, str):
                state = State(state_data, parent=parent)
                self.states.append(state)

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

        painter.translate(self.offset_x, self.offset_y)
        painter.scale(self.scale_factor, self.scale_factor)

        self.font.setPointSizeF(10*self.scale_factor)

        # 找到根状态
        root_states = [state for state in self.states if state.parent is None]
        for root in root_states:
            self._draw_state(painter, root)

        # 绘制转换连线
        self._draw_transitions(painter)

    def set_font_style(self, painter, state):
        if self.focus_state is state:
            self.font.setBold(True)
        else:
            self.font.setBold(False)
        painter.setFont(self.font)

    def set_line_style(self, painter, state):
        if self.focus_state is state:
            pen = QPen(Qt.GlobalColor.red, 4)
        else:
            pen = QPen(state.color, 2)

        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

    def set_arrow_style(self, painter, state):
        # painter.setPen(QPen(QColor(0, 0, 0), 1))
        if self.focus_state is state:
            painter.setBrush(Qt.GlobalColor.red)
            return 18
        painter.setBrush(state.color)
        return 12

    def _draw_state(self, painter : QPainter, state):
        # 名字锚点
        x, y, w, h = state.rect
        anchor_width = (len(state.name) + 5) * 8 * self.scale_factor
        anchor_x = x + 10
        anchor_y = y + 10
        anchor_height = 20*self.scale_factor
        anchor_x, anchor_y, anchor_width, anchor_height = [round(anchor_x), round(anchor_y), round(anchor_width), round(anchor_height)]
        state.name_rect = [anchor_x, anchor_y, anchor_width, anchor_height]

        self.set_font_style(painter, state)

        # 绘制状态矩形
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        if self.model.state == self.get_full_path(state):
            painter.setBrush(Qt.GlobalColor.yellow)
        else:
            painter.setBrush(QColor(200, 200, 200))
        painter.drawRoundedRect(round(x), round(y), round(w), round(h), 10, 10)
        
        # 绘制名字矩形
        color_index = min(state.level, len(LEVEL_COLORS) - 1)
        state.color = LEVEL_COLORS[color_index]
        painter.setBrush(LEVEL_COLORS[color_index])
        painter.drawRect(*state.name_rect)

        # 绘制状态名
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(anchor_x + 5, anchor_y + anchor_height // 2 + 5, state.name)

        # 递归绘制子状态
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

            self.set_font_style(painter, source)

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
                self.set_line_style(painter, source)
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
                text_x = arc_center_x
                text_y = arc_center_y - radius - 15  # 上移 15 像素
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawText(int(text_x), int(text_y), triggers)
                self.merged_transitions[key]['triggers_pos'] = (text_x, text_y)
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
                self.set_line_style(painter, source)
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

                # trigger and condition name
                # weight = 0.5
                # mid_x = start_x * weight + end_x * (1 - weight)
                # mid_y = start_y * weight + end_y * (1 - weight)
                # mid_x = (start_x) * weight + (end_x) * (1 - weight) + offset/2
                # mid_y = (start_y) * weight + (end_y) * (1 - weight) + offset/2
                mid_x = int(path.pointAtPercent(0.5).x())
                mid_y = int(path.pointAtPercent(0.5).y())
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawText(mid_x, mid_y - 15, triggers)
                self.merged_transitions[key]['triggers_pos'] = (mid_x, mid_y - 15)


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
        self.update()


    def contextMenuEvent(self, event):
        name = None
        for state in reversed(self.states):
            [anchor_x, anchor_y, anchor_width, anchor_height] = state.name_rect

            # 转换为屏幕坐标
            screen_anchor_x = anchor_x * self.scale_factor + self.offset_x
            screen_anchor_y = anchor_y * self.scale_factor + self.offset_y
            screen_anchor_width = anchor_width * self.scale_factor
            screen_anchor_height = anchor_height * self.scale_factor

            # '[   ] rect是从左上角开始的
            if (screen_anchor_x <= event.x() <= screen_anchor_x + screen_anchor_width and
                screen_anchor_y <= event.y() <= screen_anchor_y + screen_anchor_height):
                name = state.name
                break
            
        for key, data in self.merged_transitions.items():
            source = data['source']
            dest = data['dest']
            triggers = "|".join(data['triggers'])
            triggers_pos = data['triggers_pos']


            # .__text__ 文字绘制方式是从左下角开始
            screen_anchor_x = triggers_pos[0] * self.scale_factor + self.offset_x
            screen_anchor_y = triggers_pos[1] * self.scale_factor + self.offset_y
            screen_anchor_height = 20 * self.scale_factor
            screen_anchor_width = (len(triggers) + 5) * 8 * self.scale_factor

            if (screen_anchor_x <= event.x() <= screen_anchor_x + screen_anchor_width and
                (screen_anchor_y - screen_anchor_height)<= event.y() <= screen_anchor_y):
                name = triggers
                break
        
        if name is None:
            return
    
        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        copy_action.triggered.connect(lambda b, name=name: self.copy_state_name(b, name))

        copy_action.setEnabled(True)
        menu.exec_(event.globalPos())

    def copy_state_name(self, b, name):
        clipboard = QApplication.clipboard()
        clipboard.setText(name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            
            self.focus_state = None

            # 从后往前遍历状态列表
            for state in reversed(self.states):
                
                [anchor_x, anchor_y, anchor_width, anchor_height] = state.name_rect

                # 转换为屏幕坐标
                screen_anchor_x = anchor_x * self.scale_factor + self.offset_x
                screen_anchor_y = anchor_y * self.scale_factor + self.offset_y
                screen_anchor_width = anchor_width * self.scale_factor
                screen_anchor_height = anchor_height * self.scale_factor

                if (screen_anchor_x <= event.x() <= screen_anchor_x + screen_anchor_width and
                    screen_anchor_y <= event.y() <= screen_anchor_y + screen_anchor_height):
                    state.dragging = True
                    self.focus_state = state
                    state.drag_start_x = event.x()
                    state.drag_start_y = event.y()
                    break
                
        elif event.button() == Qt.RightButton:
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
                min_x = min([child.rect[0] for child in all_children])
                min_y = min([child.rect[1] for child in all_children])
                max_x = max([child.rect[0] + child.rect[2] for child in all_children])
                max_y = max([child.rect[1] + child.rect[3] for child in all_children])

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

            if len(dest_name) == 0:
                dest_name = source_name

            source_state = self._find_state_by_name(source_name)
            dest_state = self._find_state_by_name(dest_name)

            if source_state and dest_state:
                source_state.outgoing_transitions.append({
                    'trigger': trigger,
                    'dest': dest_state
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
                        'triggers': [transition['trigger']]
                    }
                else:
                    self.merged_transitions[key]['triggers'].append(transition['trigger'])

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

    # def _find_state_by_name2(self, name):
    #     parts = name.split('_')
    #     current_states = self.states
    #     current_state = None
    #     for part in parts:
    #         found = False
    #         for state in current_states:
    #             if state.name == part:
    #                 current_states = state.children
    #                 current_state = state
    #                 found = True
    #                 break
    #         if not found:
    #             return None
    #     return current_state

    def trigger_transition(self, trigger):
        try:
            # 触发状态迁移
            getattr(self.model, trigger)()
            # 重绘界面以更新当前状态显示
            self.update()
        except AttributeError as e:
            print(f"Invalid trigger: {trigger}")
        except MachineError as e:
            print(f"Invalid trigger: {trigger} {e}")

    def setup_conditions_allowed_slot(self, conditions, allowed):
        def always_true(self):
            print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} calling always_true')
            return True
        def always_false(self):
            print(f'{sys._getframe().f_code.co_name}:{sys._getframe().f_lineno} calling always_false')
            return False

        if conditions is not None:
            print(f'set Matter.{conditions} always return ({allowed})')
            if allowed.lower() == 'yes':
                setattr(Matter, conditions, always_true)
            else:
                setattr(Matter, conditions, always_false)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        app_name = 'State Machine Computing'
        self.setWindowTitle(app_name)
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon('sm.png'))
        self.settings = QSettings("Philips", app_name)


        widget = QWidget(self)
        widget.setStyleSheet("border: 2px solid gray; border-radius: 5px;")
        widget.setLayout(QVBoxLayout())

        self.config_page = ConfigPage(icon=self.windowIcon())

        self.state_machine = StateMachineWidget(self.config_page.main_resource_input.text(), 
                                                self.config_page.secondary_resource_input.text(),
                                                icon=self.windowIcon())

        self.table_view_w_search = TableViewContainsSearchWidget()
        # self.table_view_w_search.setMaximumHeight(250)

        if self.state_machine.json_transitions is not None:
            self.table_view_w_search.set_transitions(self.config_page.config_name_combobox.currentText(), self.state_machine.json_transitions)
            for row, transition in enumerate(self.state_machine.json_transitions):
                condition = transition['conditions']
                self.state_machine.setup_conditions_allowed_slot(condition, 'Yes')
        else:
            self.table_view_w_search.clear_transitions()

        self._load_conditions_allowed()

        main_widget = QWidget(self)
        main_widget.setLayout(QVBoxLayout())

        self.vert_spliter = QSplitter(Qt.Vertical, self)
        self.vert_spliter.setObjectName("vert_spliter")

        ################
        widget.layout().addWidget(self.state_machine)

        self.vert_spliter.addWidget(widget)
        self.vert_spliter.addWidget(self.table_view_w_search)

        main_widget.layout().addWidget(self.vert_spliter)

        self.setCentralWidget(main_widget)

        ##############

        menubar = self.menuBar()
        settings_menu = QMenu("&Edit", self)
        settings_action = settings_menu.addAction("Configure")
        settings_action.setShortcut('Ctrl+G')

        settings_action.triggered.connect(self.open_config_page)
        menubar.addMenu(settings_menu)

        self.load_settings()

        self.table_view_w_search.trigger_signal.connect(self.trigger_slot)
        self.config_page.config_changed_signal.connect(self.reload_config)

        self.table_view_w_search.init_state_signal.connect(self.init_state_slot)
        self.table_view_w_search.table_view.condition_allowed_changed.connect(self.state_machine.setup_conditions_allowed_slot)

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
        self.state_machine.reload_config(self.config_page.main_resource_input.text(), self.config_page.secondary_resource_input.text())

        if self.state_machine.json_transitions is not None:
            self.table_view_w_search.set_transitions(self.config_page.config_name_combobox.currentText(), self.state_machine.json_transitions)
            for row, transition in enumerate(self.state_machine.json_transitions):
                condition = transition['conditions']
                self.state_machine.setup_conditions_allowed_slot(condition, 'Yes')
        else:
            self.table_view_w_search.clear_transitions()

        self._load_conditions_allowed()

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

    def init_state_slot(self, state_name):
        self.state_machine.set_init_state(state_name)

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

        # child widget settings
        self.state_machine.load_settings(self.settings)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
