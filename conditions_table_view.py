
import sys
import os
import struct

import json
import importlib

# QT5
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QItemDelegate, QMenu, QGridLayout, QApplication, QWidget, QTableView, QTableView, QRadioButton, QComboBox, QButtonGroup, QPushButton, QCheckBox, QHeaderView, QSplitter, QAction, QVBoxLayout, QMessageBox, QFileDialog, QStyledItemDelegate, QStyle, QHBoxLayout, QLabel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QCursor, QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer, QTextStream, QFile, QIODevice, QItemSelectionModel, QThread, QSortFilterProxyModel, QModelIndex, QRegularExpression
import csv
import re
import signal

import warnings
import time
import six
import threading


class ComboBoxDelegate(QItemDelegate):
    # 定义自定义信号，用于发出行号和新值的信息
    value_changed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = [ 'No', 'Yes']

    def createEditor(self, parent, option, index):
        # print('createEditor')
        editor = QComboBox(parent)
        editor.addItems(self.items)

        # 连接 ComboBox 的 currentTextChanged 信号到自定义槽函数
        editor.currentTextChanged.connect(lambda text: self.on_value_changed(index.row(), text))

        return editor

    def setEditorData(self, editor, index):
        # print('setEditorData')
        text = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(text)

    def setModelData(self, editor, model, index):
        # print('setModelData')
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        # print('updateEditorGeometry')
        editor.setGeometry(option.rect)


    def on_value_changed(self, row, text):
        # 发出自定义信号，携带行号和新值
        self.value_changed.emit(row, text)


class RecursiveFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        for column in range(self.sourceModel().columnCount(source_parent)):
            sub_index = self.sourceModel().index(source_row, column, source_parent)
            text = self.sourceModel().data(sub_index, Qt.DisplayRole)
            if text is not None:
                regExp = self.filterRegExp().pattern()
                if regExp:
                    # print('regExp')
                    try:
                        if re.search(regExp, str(text)):
                            return True
                    except re.error:
                        pass
                else:
                    # print('regularExp')
                    regularExp = self.filterRegularExpression()
                    if regularExp.match(str(text)).hasMatch():
                        return True
        
        index = self.sourceModel().index(source_row, 0, parent=source_parent)
        # 递归检查子项是否匹配
        rows = self.sourceModel().rowCount(index)
        for row in range(rows):
            if self.filterAcceptsRow(row, index):
                return True

        return super().filterAcceptsRow(source_row, source_parent)


class MyTableView(QTableView):
    condition_allowed_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.regex_cache = {}
        self.initUI()

        self.search_regex_option = Qt.CheckState.Unchecked

        self.setStyleSheet("font-size: 12px;")

        self.__setupTableView()

    def initUI(self):
        self.table_model = QStandardItemModel(self)
        self.proxy_model = RecursiveFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 不区分大小写
        self.setModel(self.proxy_model)

    def contextMenuEvent(self, event):
        # 1. 获取鼠标位置对应的模型索引
        index = self.indexAt(event.pos())
        if not index.isValid():
            return  # 点击空白处不处理
        
        column = index.column()
        
        # 3. 构建右键菜单（根据列显示不同操作）
        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        copy_action.triggered.connect(lambda: self.copy_item_text(index, column))
        
        # 4. 显示菜单（可根据列禁用某些操作）
        if column == 0:  # 第一列禁用某些操作示例
            copy_action.setEnabled(True)
        menu.exec_(event.globalPos())

    def copy_item_text(self, index, column):
        source_index = self.proxy_model.mapToSource(index)
        
        item_text = self.table_model.itemData(source_index)[0]

        clipboard = QApplication.clipboard()
        clipboard.setText(item_text)

    def __setupTableView(self):
        self.table_model.clear()
        database_table_header = ['Source', 'Trigger', 'Condition', 'Dest', 'Condition Allowed']
        self.table_model.setHorizontalHeaderLabels(database_table_header)

        self.setColumnWidth(0, 500)
        self.setColumnWidth(1, 300)
        self.setColumnWidth(2, 300)
        self.setColumnWidth(3, 500)

        horizontal_header = self.horizontalHeader()

        horizontal_header.setSectionResizeMode(0, horizontal_header.Interactive)
        horizontal_header.setSectionResizeMode(1, horizontal_header.Interactive)
        horizontal_header.setSectionResizeMode(2, horizontal_header.Interactive)
        horizontal_header.setSectionResizeMode(3, horizontal_header.Interactive)

        horizontal_header.setSectionResizeMode(4, horizontal_header.Stretch)

        self.setSelectionBehavior(QTableView.SelectRows)

        delegate = ComboBoxDelegate(self)
        self.setItemDelegateForColumn(4, delegate)
        # 连接自定义信号到槽函数
        delegate.value_changed.connect(self.on_delegate_value_changed)

    def on_delegate_value_changed(self, row, text):
        proxy_index = self.proxy_model.index(row, 2) # condition
        source_index = self.proxy_model.mapToSource(proxy_index)
        if source_index.isValid():
            condition = self.table_model.itemData(source_index)[0]
            # print(f'condition={condition} return {text}')
            for row in range(self.table_model.rowCount()):
                condition_item = self.table_model.item(row, 2)
                allowed_item = self.table_model.item(row, 4)
                if condition_item and condition_item and condition == condition_item.text() and allowed_item.text() != text:
                    allowed_item.setText(text)
                    # print(f'on_delegate_value_changed condition_item={condition_item.text()} allowed={allowed_item.text()}')
                    self.condition_allowed_changed.emit(condition_item.text(), allowed_item.text())

    def set_transitions(self, json_transitions):
        self.clear_transitions()

        for row, transition in enumerate(json_transitions):
            source = transition['source']
            trigger = transition['trigger']
            conditions = transition['conditions']
            dest = transition['dest']

            column = 0
            item = QStandardItem('-' if len(source) == 0 else source)
            item.setEditable(False)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_model.setItem(row, column, item)
            
            column = column + 1
            item = QStandardItem('-' if len(trigger) == 0 else trigger)
            item.setEditable(False)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_model.setItem(row, column, item)
            
            column = column + 1
            item = QStandardItem('-' if len(conditions) == 0 else conditions)
            item.setEditable(False)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_model.setItem(row, column, item)
            
            # print(f'set_transitions condition_item={item.text()} allowed=Yes')
            
            column = column + 1
            item = QStandardItem('-' if len(dest) == 0 else dest)
            item.setEditable(False)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_model.setItem(row, column, item)

            column = column + 1
            item = QStandardItem(str('Yes'))
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table_model.setItem(row, column, item)
    


    def get_selected_row(self):
        selections = self.selectionModel()
        selected = selections.selectedIndexes()
        if selected:
            # 获取代理模型中的索引
            proxy_index = selected[0]
            # 将代理模型中的索引转换为源模型中的索引
            source_index = self.proxy_model.mapToSource(proxy_index)
            row = source_index.row()
            row_data = []
            for column in range(self.table_model.columnCount()):
                item = self.table_model.item(row, column)
                if item is not None:
                    row_data.append(item.text())
            return row_data
        return None

    def clear_transitions(self):
        self.table_model.clear()
        self.__setupTableView()

    def filter_tree_view_slot(self, text):
        if self.search_regex_option == Qt.CheckState.Checked:
            # print('search_regex_option is checked')
            if text in self.regex_cache:
                regex = self.regex_cache[text]
            else:
                regex = QRegularExpression(text)
                self.regex_cache[text] = regex

            if regex.isValid():
                # print(f"set regex: '{text}'")
                self.proxy_model.setFilterRegularExpression(text)
                return

        # print(f"set filter wildcard: '{text}'")
        self.proxy_model.setFilterWildcard(text)

    def regex_check_box_state_changed_slot(self, state):
        print(f'regex_check_box_state_changed_slot state={state}')
        self.search_regex_option = state

    def _get_all_conditions_allowed(self):
        condition_allowed = dict()
        for row in range(self.table_model.rowCount()):
            condition_item = self.table_model.item(row, 2)
            allowed_item = self.table_model.item(row, 4)
            if condition_item and condition_item:
                # print(f'current condition_item={condition_item.text()} allowed={allowed_item.text()}')
                condition_allowed[condition_item.text()] = allowed_item.text()
        return condition_allowed
    
    def _set_all_conditions_allowed(self, conditions_allowed):
        for row in range(self.table_model.rowCount()):
            condition_item = self.table_model.item(row, 2)
            allowed_item = self.table_model.item(row, 4)

            # 检查 item 是否为 None
            if condition_item and allowed_item:
                condition_text = condition_item.text()
                if condition_text in conditions_allowed:
                    value = conditions_allowed[condition_text]
                    try:
                        allowed_item.setText(value)
                        # print(f'_set_all_conditions_allowed condition_item={condition_item.text()} allowed={value}')
                    except Exception as e:
                        print(f"更新允许状态时出现错误: {e} value={value}")

class MySearchComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.history = []
        self.history_file = "search_history.txt"

        self.setEditable(True)
        self.load_history()
        self.setCurrentText('')
    
    def on_save_text(self):
        keyword = self.currentText().strip()
        if not keyword:
            return

        self.update_history(keyword)

        
    def update_history(self, keyword):
        print(f'update_history keyward={keyword}')

        if keyword in self.history:
            self.history.remove(keyword)
            
        # 插入到列表开头
        self.history.insert(0, keyword)
        
        # 限制历史记录数量
        if len(self.history) > 100:
            self.history = self.history[:100]
            
        # 更新下拉列表
        self.clear()
        self.addItems(self.history)
        
        # 保存到文件
        self.save_history()

        self.setCurrentIndex(0)

    def save_history(self):
        # print(f'save_history')
        with open(self.history_file, "w", encoding="utf-8") as f:
            for item in self.history:
                f.write(f"{item}\n")

    def load_history(self):
        # print(f'load_history')
        """从文件加载历史记录"""
        if os.path.exists(self.history_file):
            with open(self.history_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
                # 去重处理并保留顺序
                seen = set()
                self.history = []
                for line in lines:
                    if line and line not in seen:
                        seen.add(line)
                        self.history.append(line)
                self.addItems(self.history)

class TableViewContainsSearchWidget(QWidget):
    trigger_signal = pyqtSignal(list)
    init_state_signal = pyqtSignal(str)

    def __init__(self, parent=None, table_view=None):
        super().__init__()
        self.setup_ui(table_view)

    def setup_ui(self, table_view):
        self.table_view = table_view
        if self.table_view is None:
            self.table_view = MyTableView()

        self.search_box = MySearchComboBox()
        self.search_box.currentTextChanged.connect(self.table_view.filter_tree_view_slot)
        self.search_box.setMinimumWidth(100)

        self.regex_check_box = QCheckBox('Regex')
        self.regex_check_box.setCheckState(Qt.CheckState.Unchecked)
        self.regex_check_box.stateChanged.connect(self.table_view.regex_check_box_state_changed_slot)
        self.regex_check_box.setMaximumWidth(80)
        self.regex_check_box.setMaximumHeight(110)

        self.trigger_btn = QPushButton('Trigger')
        self.trigger_btn.clicked.connect(self.on_trigger_clicked)
        self.trigger_btn.setMaximumWidth(110)
        self.trigger_btn.setMaximumHeight(110)

        self.save_search_btn = QPushButton('Save Keywords')
        self.save_search_btn.clicked.connect(self.search_box.on_save_text)
        self.save_search_btn.setMaximumWidth(110)
        self.save_search_btn.setMaximumHeight(110)

        self.init_state_btn = QPushButton('Init State')
        self.init_state_btn.clicked.connect(self.on_init_state_btn_clicked)
        self.init_state_btn.setMaximumWidth(110)
        self.init_state_btn.setMaximumHeight(110)

        self.search_widget = QWidget()
        self.search_widget.setLayout(QGridLayout())

        row = 0
        self.search_widget.layout().addWidget(self.search_box,      row, 0)
        self.search_widget.layout().addWidget(self.trigger_btn,     row, 1)
        self.search_widget.layout().addWidget(self.regex_check_box, row, 2)
        self.search_widget.layout().addWidget(self.save_search_btn, row, 3)
        self.search_widget.layout().addWidget(self.init_state_btn,  row, 4)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.search_widget)
        self.layout().addWidget(self.table_view)

        self.search_widget.layout().setContentsMargins(0,0,0,0)
        self.search_widget.layout().setSpacing(5)

        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(5)

    def on_trigger_clicked(self):
        row = self.table_view.get_selected_row()
        if row is not None:
            self.trigger_signal.emit(row)
            # print(f'trigger row={row}')

    def on_init_state_btn_clicked(self):
        row = self.table_view.get_selected_row()
        if row is not None:
            self.init_state_signal.emit(row[0])

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        table_view = MyTableView()
        self.table_view_w_search = TableViewContainsSearchWidget(table_view=table_view, parent=self)

        table_view.add_conditions([ ('A1111111111111111111111', 1), ('B22222222222222222222', 0)])
        # table_view.clear_data()
        table_view.get_condition_ret('A1111111111111111111111')
        table_view.get_condition_ret('B22222222222222222222')

        bottom_widget = QWidget()
        bottom_widget.setLayout(QHBoxLayout())

        layout.addWidget(self.table_view_w_search)
        layout.addWidget(bottom_widget)
        self.setLayout(layout)

        self.setWindowTitle('Table View')
        self.setGeometry(300, 200, 600, 800)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())