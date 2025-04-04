import sys, os
import json
import math

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygonF, QPainterPath
from PyQt5.QtCore import Qt, QSettings, QPointF
from transitions.core import MachineError

from state_machine_core import Matter, CustomStateMachine


from conditions_table_view import TableViewContainsSearchWidget


# 定义不同层级的拖动锚点颜色
LEVEL_COLORS = [
    Qt.GlobalColor.red,
    Qt.GlobalColor.darkGreen,
    Qt.GlobalColor.blue,
    Qt.GlobalColor.darkYellow,
    Qt.GlobalColor.black,
    Qt.GlobalColor.darkGray,
]

STATES_CONFIG = './config/states/states_config.json'
STATES_POSITION_CONFIG = './config/states/states_position_config.json'
TRANSITIONS_CONFIG = './config/transitions/transitions_config.json'
TRANSITIONS_CONFIG_FOLDER = './config/transitions/pmc'


# with open(f'dump_{STATES_CONFIG}', 'w') as f:
#     json.dump(defalut_json_states, f, indent=4, ensure_ascii=False)

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
    def __init__(self):
        super().__init__()

        self.is_dragging_all = False

        self.states = []
        
        self.json_states = self._load_states()
        self.json_transitions = self._load_transitions()

        self._build_states(self.json_states)

        self._load_state_positions()

        self._layout_states()

        self._adjust_all_states()

        self.model = Matter()
        extra_args = dict(auto_transitions=False, initial='XMCMachine_XMCPowerUpSState_XMCWaitCouchTypeState', title='XMCMachine in XMCTask',
                        show_conditions=True, show_state_attributes=True)
        self.machine = CustomStateMachine(model=self.model, states=self.json_states, ignore_invalid_triggers=True,
                                    transitions=self.json_transitions, 
                                    **extra_args)

        if self.json_transitions is not None:
            # print(f'json_transitions={json_transitions}')
            self._connect_states(self.json_transitions)

    def _adjust_all_states(self):
        for state in self.states:
            self._adjust_parent(state)
        self.update()

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

        # current_state = self.model.state
        # print(f'current_state={current_state} {type(current_state)}')

        # 找到根状态
        root_states = [state for state in self.states if state.parent is None]
        for root in root_states:
            self._draw_state(painter, root)

        # 绘制转换连线
        self._draw_transitions(painter)

    def _draw_state(self, painter : QPainter, state):
        x, y, w, h = state.rect
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        if self.model.state == self.get_full_path(state):
            painter.setBrush(Qt.GlobalColor.yellow)
        else:
            painter.setBrush(QColor(200, 200, 200))

        painter.drawRoundedRect(round(x), round(y), round(w), round(h), 10, 10)

        # 绘制拖动锚点在左上方，根据层级选择颜色
        anchor_width = len(state.name) * 8 + 10  # 根据名称长度调整宽度
        anchor_x = x + 10
        anchor_y = y + 10
        anchor_height = 20
        color_index = min(state.level, len(LEVEL_COLORS) - 1)
        
        state.color = LEVEL_COLORS[color_index]
        painter.setBrush(LEVEL_COLORS[color_index])
        
        state.name_rect = [anchor_x, anchor_y, anchor_width, anchor_height]
        painter.drawRect(*state.name_rect)

        # 在拖动锚点内绘制状态名
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
        merged_transitions = {}
        for state in self.states:
            for transition in state.outgoing_transitions:
                source = state
                dest = transition['dest']
                key = (source, dest)
                if key not in merged_transitions:
                    merged_transitions[key] = {
                        'source': source,
                        'dest': dest,
                        'triggers': [transition['trigger']]
                    }
                else:
                    merged_transitions[key]['triggers'].append(transition['trigger'])

        margin = 5
        for key, data in merged_transitions.items():
            source = data['source']
            dest = data['dest']
            triggers = "|".join(data['triggers'])

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

            if (source_x, source_y) == (dest_x, dest_y):
                # 起点和终点相同，绘制自环（圆弧）
                radius = 20  # 圆弧半径
                arc_center_x = start_x + radius
                arc_center_y = start_y
                start_angle = 180 * 16  # 起始角度，16 是 Qt 角度的缩放因子
                span_angle = -180 * 16  # 跨度角度，负号表示逆时针

                # 绘制圆弧
                pen = QPen(source.color, 2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.drawArc(int(arc_center_x - radius), int(arc_center_y - radius),
                int(radius * 2), int(radius * 2), start_angle, span_angle)

                # 计算曲线最大凸起部分（圆弧顶部）的位置
                text_x = arc_center_x
                text_y = arc_center_y - radius - 15  # 上移 15 像素

                # 绘制触发事件名称
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawText(int(text_x), int(text_y), triggers)

                # 绘制箭头
                arrow_size = 10
                end_angle = (start_angle + span_angle) / 16
                arrow_x = arc_center_x + radius * math.cos(math.radians(end_angle))
                arrow_y = arc_center_y + radius * math.sin(math.radians(end_angle))
                arrow_angle = math.radians(end_angle + 90)
                arrow_x1 = arrow_x - arrow_size * math.cos(arrow_angle - math.pi / 6)
                arrow_y1 = arrow_y - arrow_size * math.sin(arrow_angle - math.pi / 6)
                arrow_x2 = arrow_x - arrow_size * math.cos(arrow_angle + math.pi / 6)
                arrow_y2 = arrow_y - arrow_size * math.sin(arrow_angle + math.pi / 6)
                painter.setBrush(source.color)
                painter.setPen(QPen(source.color, 1))
                painter.drawPolygon(QPointF(arrow_x, arrow_y), QPointF(arrow_x1, arrow_y1), QPointF(arrow_x2, arrow_y2))
            else:
                # 起点和终点不同，绘制贝塞尔曲线
                # 计算贝塞尔曲线的控制点
                control_x = (start_x + end_x) / 2
                control_y1 = start_y + (end_y - start_y) * 0.2
                control_y2 = start_y + (end_y - start_y) * 0.8

                # 创建贝塞尔曲线路径
                path = QPainterPath()
                path.moveTo(start_x, start_y)
                # 添加三次贝塞尔曲线
                path.cubicTo(control_x, control_y1, control_x, control_y2, end_x, end_y)

                # 设置画笔，绘制等粗的曲线，颜色取决于开始节点的颜色
                pen = QPen(source.color, 2)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充
                painter.drawPath(path)

                # 计算曲线中点的位置
                mid_x = (start_x + end_x) / 2
                mid_y = (start_y + end_y) / 2

                # 绘制触发事件名称（在连线中间上方）
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawText(int(mid_x), int(mid_y - 15), triggers)

                # 绘制箭头（使用三角形表示方向）
                arrow_size = 18
                angle = math.atan2(end_y - start_y, end_x - start_x)
                arrow_x1 = end_x - arrow_size * math.cos(angle - math.pi / 6)
                arrow_y1 = end_y - arrow_size * math.sin(angle - math.pi / 6)
                arrow_x2 = end_x - arrow_size * math.cos(angle + math.pi / 6)
                arrow_y2 = end_y - arrow_size * math.sin(angle + math.pi / 6)

                painter.setBrush(dest.color)
                painter.setPen(QPen(dest.color, 1))

                painter.drawPolygon(QPointF(end_x, end_y), QPointF(arrow_x1, arrow_y1), QPointF(arrow_x2, arrow_y2))


    # def _draw_transitions(self, painter):

    #     merged_transitions = {}
    #     for state in self.states:
    #         for transition in state.outgoing_transitions:
    #             source = state
    #             dest = transition['dest']
    #             key = (source, dest)
    #             if key not in merged_transitions:
    #                 # trigger_name = transition['trigger']
    #                 # print(f'set key={source.name}-{dest.name} trigger={trigger_name}')
    #                 merged_transitions[key] = {
    #                     'source': source,
    #                     'dest': dest,
    #                     'triggers': [transition['trigger']]
    #                 }
    #             else:
    #                 # print(f'add key={source.name}-{dest.name} trigger={trigger_name}')
    #                 merged_transitions[key]['triggers'].append(transition['trigger'])

    #     margin = 5
    #     for key, data in merged_transitions.items():
    #         source = data['source']
    #         dest = data['dest']
    #         triggers = "|".join(data['triggers'])

    #         # 获取源状态的矩形信息和颜色
    #         source_x, source_y, source_w, source_h = source.name_rect

    #         # 获取目标状态的矩形信息
    #         # dest_state = transition['dest']
    #         dest_x, dest_y, dest_w, dest_h = dest.name_rect

    #         # 计算源状态和目标状态的中心
    #         source_center_x = source_x + source_w / 2
    #         source_center_y = source_y + source_h / 2
    #         dest_center_x = dest_x + dest_w / 2
    #         dest_center_y = dest_y + dest_h / 2

    #         # 计算连线的方向向量
    #         dx = dest_center_x - source_center_x
    #         dy = dest_center_y - source_center_y

    #         # 计算连线从源状态矩形边缘出发并加上 margin 的起点
    #         if abs(dx) > abs(dy):
    #             if dx > 0:
    #                 start_x = source_x + source_w + margin
    #                 start_y = source_center_y
    #             else:
    #                 start_x = source_x - margin
    #                 start_y = source_center_y
    #         else:
    #             if dy > 0:
    #                 start_x = source_center_x
    #                 start_y = source_y + source_h + margin
    #             else:
    #                 start_x = source_center_x
    #                 start_y = source_y - margin

    #         # 计算连线到达目标状态矩形边缘并加上 margin 的终点
    #         if abs(dx) > abs(dy):
    #             if dx > 0:
    #                 end_x = dest_x - margin
    #                 end_y = dest_center_y
    #             else:
    #                 end_x = dest_x + dest_w + margin
    #                 end_y = dest_center_y
    #         else:
    #             if dy > 0:
    #                 end_x = dest_center_x
    #                 end_y = dest_y - margin
    #             else:
    #                 end_x = dest_center_x
    #                 end_y = dest_y + dest_h + margin

    #         # 计算贝塞尔曲线的控制点
    #         control_x = (start_x + end_x) / 2
    #         control_y1 = start_y + (end_y - start_y) * 0.2
    #         control_y2 = start_y + (end_y - start_y) * 0.8

    #         # 创建贝塞尔曲线路径
    #         path = QPainterPath()
    #         path.moveTo(start_x, start_y)
    #         # 添加三次贝塞尔曲线
    #         path.cubicTo(control_x, control_y1, control_x, control_y2, end_x, end_y)

    #         # 设置画笔，绘制等粗的曲线，颜色取决于开始节点的颜色
    #         pen = QPen(source.color, 2)
    #         pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    #         pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    #         painter.setPen(pen)
    #         painter.setBrush(Qt.NoBrush)  # 设置不使用画刷填充
    #         painter.drawPath(path)

    #         # 计算曲线中点的位置
    #         mid_x = (start_x + end_x) / 2
    #         mid_y = (start_y + end_y) / 2

    #         # 绘制触发事件名称（在连线中间上方）
    #         painter.setPen(QPen(QColor(0, 0, 0), 1))
    #         painter.drawText(int(mid_x), int(mid_y - 15), triggers)

    #         # # 绘制箭头（使用三角形表示方向）
    #         arrow_size = 18
    #         angle = math.atan2(end_y - start_y, end_x - start_x)
    #         arrow_x1 = end_x - arrow_size * math.cos(angle - math.pi / 6)
    #         arrow_y1 = end_y - arrow_size * math.sin(angle - math.pi / 6)
    #         arrow_x2 = end_x - arrow_size * math.cos(angle + math.pi / 6)
    #         arrow_y2 = end_y - arrow_size * math.sin(angle + math.pi / 6)

    #         painter.setBrush(dest.color)
    #         painter.setPen(QPen(dest.color, 1))

    #         painter.drawPolygon(QPointF(end_x, end_y), QPointF(arrow_x1, arrow_y1), QPointF(arrow_x2, arrow_y2))


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 从后往前遍历状态列表
            for state in reversed(self.states):
                x, y, w, h = state.rect
                anchor_width = len(state.name) * 8 + 10
                anchor_x = x + 10
                anchor_y = y + 10
                anchor_height = 20
                if (anchor_x <= event.x() <= anchor_x + anchor_width and
                        anchor_y <= event.y() <= anchor_y + anchor_height):
                    state.dragging = True
                    state.drag_offset = (event.x() - x, event.y() - y)
                    break
        elif event.button() == Qt.RightButton:
            self.is_dragging_all = True
            self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_dragging_all:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()
            for state in self.states:
                x, y, w, h = state.rect
                state.rect = (x + dx, y + dy, w, h)
            self.last_pos = event.pos()
            self.update()
        else:
            for state in self.states:
                if state.dragging:
                    dx, dy = state.drag_offset
                    new_x = event.x() - dx
                    new_y = event.y() - dy

                    dx_move = new_x - state.rect[0]
                    dy_move = new_y - state.rect[1]

                    state.rect = (new_x, new_y, state.rect[2], state.rect[3])
                    self._move_children(state, dx_move, dy_move)
                    self._adjust_parent(state)
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
                name_margin = 40
                new_x = min_x - margin
                new_y = min_y - margin - name_margin
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
        with open(STATES_POSITION_CONFIG, 'w') as f:
            json.dump(state_hierarchy, f, indent=4, ensure_ascii=False)


    def _load_state_positions(self):
        def get_parent_chain(state):
            chain = []
            while state:
                chain.append(state.name)
                state = state.parent
            return chain

        try:
            with open(STATES_POSITION_CONFIG, 'r') as f:
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
            with open(STATES_CONFIG, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        
    # def _load_transitions(self):
    #     try:
    #         with open(TRANSITIONS_CONFIG, 'r') as f:
    #             return json.load(f)
    #     except FileNotFoundError:
    #         return None
        
    def _load_transitions(self):
        merged_json = []
        try:
            # 遍历指定目录下的所有文件
            for filename in os.listdir(TRANSITIONS_CONFIG_FOLDER):
                if filename.endswith('.json'):
                    file_path = os.path.join(TRANSITIONS_CONFIG_FOLDER, filename)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            merged_json.extend(data)
                    except FileNotFoundError:
                        print(f"文件 {file_path} 未找到。")
                    except json.JSONDecodeError:
                        print(f"文件 {file_path} 不是有效的 JSON 文件。")
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

    def trigger_transition(self, trigger, conditions=None, allowed='Yes'):
        try:
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

            # 触发状态迁移
            getattr(self.model, trigger)()
            # 重绘界面以更新当前状态显示
            self.update()
        except AttributeError as e:
            print(f"Invalid trigger: {trigger}")
        except MachineError as e:
            print(f"Invalid trigger: {trigger} {e}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('State Machine Drawing')
        self.setGeometry(100, 100, 800, 600)
        self.settings = QSettings("Philips", "State Machine Drawing")

        layout = QVBoxLayout()

        self.state_machine = StateMachineWidget()

        layout.addWidget(self.state_machine)

        self.table_view_w_search = TableViewContainsSearchWidget()
        self.table_view_w_search.setMaximumHeight(250)
        self.table_view_w_search.table_view.add_transitions(self.state_machine.json_transitions) 

        layout.addWidget(self.table_view_w_search)

        self.setLayout(layout)

        self.load_settings()

        self.table_view_w_search.trigger_signal.connect(self.trigger_slot)

    def trigger_slot(self, row):
        if len(row) >= 5:
            source = row[0]
            trigger = row[1]
            conditions = row[2]
            dest = row[3]
            allowed = row[4]
            # print(f'trigger_slot source={source}, trigger={trigger}, conditions={conditions}, dest={dest}, allowed={allowed}')
            self.state_machine.trigger_transition(trigger, conditions, allowed)

    def closeEvent(self, event):
        self.state_machine._save_state_positions()

        self.save_settings()

        event.accept()

    def save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())

    def load_settings(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    
