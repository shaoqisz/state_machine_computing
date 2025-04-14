import sys, os
import json
import re
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QVBoxLayout, QTreeView, QFileDialog, QComboBox, QMenu, QInputDialog, QMessageBox, QCheckBox, QHeaderView, QAbstractItemView, QLineEdit
from PyQt5.QtCore import Qt, QSettings, QPointF, QEvent, pyqtSignal, QTimer, QSortFilterProxyModel, QModelIndex, QRegularExpression
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QCursor, QIcon, QPixmap


class RecursiveFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        for column in range(self.sourceModel().columnCount(source_parent)):
            sub_index = self.sourceModel().index(source_row, column, source_parent)
            text = self.sourceModel().data(sub_index, Qt.DisplayRole)
            if text is not None:
                regExp = self.filterRegExp().pattern()
                if regExp:
                    try:
                        if re.search(regExp, str(text)):
                            return True
                    except re.error:
                        pass
                else:
                    regularExp = self.filterRegularExpression()
                    if regularExp.match(str(text)).hasMatch():
                        return True

        index = self.sourceModel().index(source_row, 0, parent=source_parent)
        rows = self.sourceModel().rowCount(index)
        for row in range(rows):
            if self.filterAcceptsRow(row, index):
                return True

        return super().filterAcceptsRow(source_row, source_parent)


class MySearchComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.history = []
        self.history_file = "search_history_tree_view.txt"

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


class StateMachineJsonViewer(QWidget):
    state_added_signal = pyqtSignal(list)
    state_removed_signal = pyqtSignal(list)
    state_rename_signal = pyqtSignal(list, str)

    def __init__(self, json_data=None):
        super().__init__()
        
        self.editing_item_old_text = None

        self.initUI(json_data)

    def set_json_data(self, json_data):
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(['Key', 'Value'])

        for col in range(self.tree_model.columnCount()):
            header_item = self.tree_model.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        self.populate_model(self.tree_model.invisibleRootItem(), json_data)

        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.expandAll()

    def set_white_theme(self):
        self.setStyleSheet("""
            QTreeView {
                font-size: 16px;
                border-radius: 8px;
                padding: 2px;
                border: 1px solid gray;
            }
            QHeaderView::section {
                background-color: white;
                border: none;
                padding: 5px;
                border-right: 1px solid #d9dcdb;
            }
            QHeaderView::section:first {
                border-top-left-radius: 10px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 10px;
                border-right: none;
            }
            QTreeView::item {
                padding: 0px;
                height: 25px;
            }
        """)
    def set_black_theme(self):
        self.setStyleSheet("""
            QTreeView {
                background-color: black;
                gridline-color: gray;
                font-size: 16px;
                border-radius: 8px;
                padding: 2px;
                border: 1px solid gray;
            }
            QHeaderView::section {
                background-color: black;
                border: none;
                padding: 5px;
                border-right: 1px solid gray;
            }
            QHeaderView::section:first {
                border-top-left-radius: 10px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 10px;
                border-right: none;
            }
            QTreeView::item {
                background-color: black;
                padding: 0px;
                height: 25px;
            }
            QTreeView::item:selected {
                background-color: gray;
            }
            QHeaderView::section:horizontal {
                background: black;
                border-bottom: 1px solid gray;
                color: white;
            }
            QHeaderView::section:vertical {
                background: black;
                border-right: 1px solid gray;
                color: white;
            }
            QTableCornerButton::section {
                background-color: black;
                border: 1px solid gray;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 18px;
                margin: 15px 0 15px 0;
            }
            QScrollBar::handle:vertical {
                background: #333333;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical {
                height: 15px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                height: 15px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            """)
        
    def initUI(self, json_data):
        self.setWindowTitle('State Machine Json Viewer')

        layout = QVBoxLayout()

        # 添加搜索框
        self.search_box = MySearchComboBox(self)
        self.search_box.setPlaceholderText("Search in tree")
        self.search_box.currentTextChanged.connect(self.filter_tree_view_slot)

        self.save_search_btn = QPushButton('Save Keywords')
        self.save_search_btn.clicked.connect(self.search_box.on_save_text)
        self.save_search_btn.setMaximumWidth(110)
        self.save_search_btn.setMaximumHeight(110)

        self.regex_cache = {}

        self.regex_check_box = QCheckBox('Regex')
        self.regex_check_box.setCheckState(Qt.CheckState.Unchecked)
        self.regex_check_box.setMaximumWidth(60)
        self.regex_check_box.setMaximumHeight(110)

        self.tree_model = QStandardItemModel(self)
        self.proxy_model = RecursiveFilterProxyModel()
        self.proxy_model.setSourceModel(self.tree_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 不区分大小写
        self.tree_model.itemChanged.connect(self.on_item_changed)

        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.set_json_data(json_data)

        self.tree.setContextMenuPolicy(3)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.edit_item)


        self.search_widget = QWidget()
        self.search_widget.setLayout(QGridLayout())
        self.search_widget.layout().addWidget(self.search_box, 0, 0)
        self.search_widget.layout().addWidget(self.regex_check_box, 0, 1)
        self.search_widget.layout().addWidget(self.save_search_btn, 0, 2)
        self.search_widget.layout().setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.search_widget)

        layout.addWidget(self.tree)

        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def populate_model(self, parent, data):
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = QStandardItem(key)
                if isinstance(value, (dict, list)):
                    self.populate_model(key_item, value)
                    parent.appendRow([key_item, QStandardItem()])
                else:
                    value_item = QStandardItem(str(value))
                    parent.appendRow([key_item, value_item])
        elif isinstance(data, list):
            for index, value in enumerate(data):
                key_item = QStandardItem(f"[{index}]")
                if isinstance(value, (dict, list)):
                    self.populate_model(key_item, value)
                    parent.appendRow([key_item, QStandardItem()])
                else:
                    value_item = QStandardItem(str(value))
                    parent.appendRow([key_item, value_item])

    def get_parent(self, item, times):
        parent = item
        for i in range(times):
            if parent is None:
                break
            parent = parent.parent()
        return parent
    
    def get_item_key_value(self, item, index):
        text_column_1 = ''
        text_column_2 = ''

        if item:
            if index.column() == 0:  # 点击的是第一列
                # print('点击的是第一列')
                text_column_1 = item.text()
                parent_item = item.parent()
                if parent_item:
                    text_column_2 = parent_item.child(item.row(), 1).text()

            elif index.column() == 1:  # 点击的是第二列
                # print('点击的是第二列')
                text_column_2 = item.text()
                parent_item = item.parent()
                if parent_item:
                    text_column_1 = parent_item.child(item.row(), 0).text()
            
        return text_column_1, text_column_2
    
    def get_items_1_2(self, item, index):
        item_column_1 = None
        item_column_2 = None

        if item:
            if index.column() == 0:  # 点击的是第一列
                item_column_1 = item
                parent_item = item.parent()
                if parent_item is None:
                    parent_item = self.tree_model.invisibleRootItem()

                item_column_2 = parent_item.child(item.row(), 1)

            elif index.column() == 1:  # 点击的是第二列
                # print('点击的是第二列')
                item_column_2 = item
                parent_item = item.parent()
                if parent_item is None:
                    parent_item = self.tree_model.invisibleRootItem()
                item_column_1 = parent_item.child(item.row(), 0)
            
        return item_column_1, item_column_2


    def show_context_menu(self, position):
        menu = QMenu(self)

        index = self.tree.indexAt(position)
        if index.isValid():
            _item = self.tree_model.itemFromIndex(self.proxy_model.mapToSource(index))
            item_column_1, item_column_2 = self.get_items_1_2(_item, index)
            # print(f'item_column_1={item_column_1.text()} item_column_2={item_column_2.text()}')

            if item_column_1.parent() is None:
                action = menu.addAction("Save as")
                action.triggered.connect(lambda b: self.save_as_json())

            is_digit = self.is_digit_item(item_column_1)
            has_children = self.has_property(item_column_1, 'children')
            has_on_enter = self.has_property(item_column_1, 'on_enter')
            has_on_exit = self.has_property(item_column_1, 'on_exit')
            parent_item = item_column_1.parent()
            parent_parent_item = self.get_parent(item_column_1, 2)
            parent_parent_parent_item = self.get_parent(item_column_1, 3)

            name_to_set_initial = ''
            parent_to_set_initial = None

            if item_column_1.text() == 'name' and parent_parent_item and parent_parent_item.text() == 'children':
                # print('case1')
                parent_to_set_initial = parent_parent_parent_item
                if parent_to_set_initial:
                    name_to_set_initial = item_column_2.text()

            elif is_digit and item_column_2 and len(item_column_2.text()) > 0 and parent_item and parent_item.text() == 'children':
                # print('case2')
                parent_to_set_initial = parent_parent_item
                if parent_to_set_initial:
                    name_to_set_initial = item_column_2.text()

            elif is_digit and item_column_2 and len(item_column_2.text()) == 0 and parent_item and parent_item.text() == 'children':
                # print('case3')
                parent_to_set_initial = parent_parent_item
                if parent_to_set_initial:
                    for i in range(item_column_1.rowCount()):
                        child = item_column_1.child(i)
                        if child.text() == 'name':
                            name_to_set_initial = child.parent().child(0, 1).text()
                            break

            if parent_to_set_initial:
                # print(f'parent_to_set_initial={parent_to_set_initial.text()} name_to_set_initial={name_to_set_initial}')
                set_initial_state_action = menu.addAction("Set as initial state")
                set_initial_state_action.triggered.connect(lambda b, item=parent_to_set_initial, key='initial', value=name_to_set_initial, index=index: self.set_key_value(item, key, value, index))

            if is_digit and (parent_item is None or parent_item.text() == 'children'):
                if not has_on_enter:
                    action = menu.addAction("Add on_enter [...]")
                    action.triggered.connect(
                        lambda b, gate_name='on_enter', item_column_1=item_column_1, item_column_2=item_column_2, index=index: self.add_gate(gate_name, item_column_1, item_column_2, index))

                if not has_on_exit:
                    action = menu.addAction("Add on_exit [...]")
                    action.triggered.connect(
                        lambda b, gate_name='on_exit', item_column_1=item_column_1, item_column_2=item_column_2, index=index: self.add_gate(gate_name, item_column_1, item_column_2, index))

                if not has_children:
                    action = menu.addAction("Add children [...]")
                    action.triggered.connect(lambda b, item_column_1=item_column_1, item_column_2=item_column_2, index=index: self.add_children_list(item_column_1, item_column_2, index))

            if self.can_add_children(item_column_1):
                action = menu.addAction("Add a child")
                action.triggered.connect(lambda b, item_column_1=item_column_1, index=index: self.add_list_item(item_column_1, index))

            action = menu.addAction("Delete")
            item_names = []
            if item_column_1.text() == 'name':
                # print('case1')
                # name : state_name <---- right click here
                item_names.append( (item_column_1.parent(), item_column_2.text()) )
            elif item_column_1.text() == 'children':
                # print('case2')
                # children : ___  <---- right click here
                #       [0]: ...
                for child_no in range(item_column_1.rowCount()):
                    child_item = item_column_1.child(child_no, 0)
                    child_item_data = item_column_1.child(child_no, 1)
                    # print(f'del child_item={child_item.text()} data={child_item_data.text()}')
                    item_names.append( (child_item, child_item_data.text()) )
            elif is_digit and item_column_2 is None or len(item_column_2.text()) == 0:
                # print(f'case3 is digit and item_column_2={item_column_2}')
                # [0]: ___ <---- right click here
                #     name: state_name
                if item_column_1:
                    for i in range(item_column_1.rowCount()):
                        gp_child = item_column_1.child(i)
                        # print(f'gp_child={gp_child.text()}')
                        if gp_child.text() == "name":
                            item_names.append( (item_column_1, item_column_1.child(i, 1).text()) )
                            break
            else:
                # print('case4')
                # [0]: state_name <---- right click here
                item_names.append( (item_column_1, item_column_2.text() if item_column_2 else '') )

            if len(item_names) > 0:
                action.triggered.connect(lambda b, item_names=item_names: self.delete_items(item_names))

        else:
            action = menu.addAction("Save as")
            action.triggered.connect(lambda b: self.save_as_json())

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))

    def add_list_item(self, parent_item, index):
        value, ok = QInputDialog.getText(self, "Add a child", "Enter child name:")
        if ok:
            row = parent_item.rowCount()
            key_item = QStandardItem(f"[{row}]")
            value_item = QStandardItem(value)
            parent_item.appendRow([key_item, value_item])
            self.tree.expand(index)

            if parent_item.text() == "on_enter" or parent_item.text() == "on_exit":
                print(f'parent_item={parent_item.text()} is\'s not a state that should to emit')
                return

            names = self.get_parent_chain_names(parent_item, value)
            self.state_added_signal.emit(names)

    def add_children_list(self, item_column_1, item_column_2, index):
        is_string_node = self.is_string_node(item_column_2)
        if is_string_node is True:
            self.add_key_value(item_column_1, 'name', item_column_2.text())
            self.add_children(item_column_1)
            item_column_2.setText('')
        else:
            self.add_children(item_column_1)

        self.tree.expand(index)

    def add_children(self, parent_item):
        key_item = QStandardItem("children")
        value_item = QStandardItem("")
        parent_item.appendRow([key_item, value_item])
        index = self.tree_model.indexFromItem(parent_item)
        self.tree.expand(index)

    def add_gate(self, gate_name, item_column_1, item_column_2, index):
        is_string_node = self.is_string_node(item_column_2)
        if is_string_node:
            self.add_key_value(item_column_1, 'name', item_column_1.parent().child(item_column_1.row(), 1).text())
            self.add_key_value(item_column_1, gate_name, '')
            item_column_1.parent().child(item_column_1.row(), 1).setText('')
        else:
            self.add_key_value(item_column_1, gate_name, '')

        self.tree.expand(index)

    def is_digit_item(self, item):
        key = item.text() if item else ""
        if key.startswith('[') and key.endswith(']'):
            key = key[1:-1]

        return key.isdigit()

    def has_property(self, item, name):
        if item is not None:
            for i in range(item.rowCount()):
                child = item.child(i)
                if child.text() == name:
                    return True
        return False

    def can_add_children(self, item):
        if item.text() == "children" or item.text() == "on_enter" or item.text() == "on_exit":
            return True
        return False
    
    def is_string_node(self, item):
        return len(item.text()) > 0
    
    def parent_is_children_or_none(self, item):
        parent = item.parent()
        if parent is None:
            return True
        return parent.text() == 'children'
    
    def parent_is_children(self, item):
        parent = item.parent()
        if parent is None:
            return False
        return parent.text() == 'children'

    def add_key_value(self, parent_item, key, value):
        key_item = QStandardItem(key)
        value_item = QStandardItem(value)
        parent_item.appendRow([key_item, value_item])
        index = self.tree_model.indexFromItem(parent_item)
        self.tree.expand(index)

    def set_key_value(self, parent_item, key, value, index):
        found = False
        if parent_item:
            for child_no in range(parent_item.rowCount()):
                child = parent_item.child(child_no, 0)
                if child.text() == key:
                    child_item_data = parent_item.child(child_no, 1)
                    child_item_data.setText(value)
                    found = True
            if not found:
                key_item = QStandardItem(key)
                value_item = QStandardItem(value)
                parent_item.appendRow([key_item, value_item])

            self.tree.expand(index)

    def get_parent_chain_names(self, parent_item, name):
        names = [name]
        current_item = parent_item
        if current_item:
            while current_item.parent():
                parent = current_item.parent()

                for i in range(parent.rowCount()):
                    child = parent.child(i)
                    if child.text() == 'name':
                        names.append(child.parent().child(0, 1).text())

                current_item = parent
        names.reverse()
        return names

    def delete_items(self, item_names):
        reply = QMessageBox.question(self, 'Confirm Deletion', 'Are you sure you want to delete this item?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        
        for item, name in item_names:
            self.delete_item(item, name)

    def delete_item(self, item, name):
        print(f'item_coitemlumn_1={item.text()} name={name}')
        is_a_state = True

        parent = item.parent()
        names = None
        if parent:
            # print('case5')
            names = self.get_parent_chain_names(parent, name)
            grandparent = parent.parent()
            if grandparent:
                for i in range(grandparent.rowCount()):
                    gp_child = grandparent.child(i)
                    if (gp_child.text() == "on_enter" or gp_child.text() == "on_exit" or gp_child.text() == "initial") and gp_child == parent:
                        is_a_state = False
                        break
            is_digit = self.is_digit_item(item)
            row = item.row()
            parent.removeRow(row)
            if is_digit:
                for i in range(parent.rowCount()):
                    child = parent.child(i)
                    if self.is_digit_item(child):
                        child.setText(f"[{i}]")
        else:
            # print('case6')
            names = [name]
            root = self.tree_model.invisibleRootItem()
            row = item.row()
            root.removeRow(row)

        if is_a_state is False:
            return

        print(f'state_removed_signal names={names}')
        self.state_removed_signal.emit(names)

    def edit_item(self, index):
        if index.column() == 1:
            _item = self.tree_model.itemFromIndex(self.proxy_model.mapToSource(index))
            item_column_1, item_column_2 = self.get_items_1_2(_item, index)
            # print(f"Item in row {index.row()}, column {index.column()} old-name={item_column_2.text()}")
            self.editing_item_old_text = item_column_2.text()
            self.tree.edit(index)

    def on_item_changed(self, renamed_item):
        index = self.tree_model.indexFromItem(renamed_item)
        if index.column() == 1:
            if self.editing_item_old_text is None:
                return
            # new_text = renamed_item.data(Qt.EditRole)
            # print('点击的是第二列')
            item_column_2 = renamed_item
            parent_item = renamed_item.parent()
            if parent_item is None:
                print('root can not be renamed')
                return
            
            if parent_item:
                if parent_item.text() == "on_enter" or parent_item.text() == "on_exit":
                    print('gates were not deal with here')
                    return
                
            item_column_1 = parent_item.child(renamed_item.row(), 0)
            if item_column_1.text() == "initial":
                print('initials were not deal with here')
                return

            item = None
            name = None
            if item_column_1.text() == 'name':
                # print('case1')
                # name : state_name <---- right click here
                item = item_column_1.parent()
                name = item_column_2.text()
            else:
                # print('case4')
                # [0]: state_name <---- right click here
                item = item_column_1
                name = item_column_2.text() if item_column_2 else ''

            print(f'item_column_1={item_column_1.text()} item_column_2={item_column_2.text()}')
            
            names = None
            parent = item.parent()
            if parent:
                names = self.get_parent_chain_names(parent, name)
            else:
                names = [name]
            
            print(f"State row={index.row()}, column {index.column()} was renamed from {self.editing_item_old_text} to {names}")
            self.state_rename_signal.emit(names, self.editing_item_old_text)

    def save_as_json(self):
        root_item = self.tree_model.invisibleRootItem()
        json_data = self.model_to_json(root_item)

        file_path, _ = QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, 'Success', 'JSON file saved successfully.')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to save JSON file: {str(e)}')

    def model_to_json(self, parent_item):
        if parent_item.rowCount() == 0:
            return None

        if all(self.is_digit_item(parent_item.child(i)) for i in range(parent_item.rowCount())):
            result = []
            for i in range(parent_item.rowCount()):
                child = parent_item.child(i)
                child_value_item = child.parent().child(child.row(), 1) if child.parent() else None
                child_value = child_value_item.text().strip() if child_value_item and child_value_item.text().strip() else None
                if child_value is None and child.rowCount() > 0:
                    child_value = self.model_to_json(child)
                if child_value is not None:
                    result.append(child_value)
            return result if result else None
        else:
            result = {}
            for i in range(parent_item.rowCount()):
                child = parent_item.child(i)
                key = child.text()
                value_item = child.parent().child(child.row(), 1) if child.parent() else None
                value = value_item.text().strip() if value_item and value_item.text().strip() else None
                if value is None and child.rowCount() > 0:
                    value = self.model_to_json(child)
                if value is not None:
                    result[key] = value
            return result if result else None


    # def filter_tree_view_slot(self, text):
    #     self.proxy_model.setFilterRegularExpression(text)
    #     self.tree.expandAll()

    def filter_tree_view_slot(self, text):
        if self.regex_check_box.isChecked():
            if text in self.regex_cache:
                regex = self.regex_cache[text]
            else:
                regex = QRegularExpression(text)
                self.regex_cache[text] = regex

            if regex.isValid():
                # print(f"set regex: '{text}'")
                self.proxy_model.setFilterRegularExpression(regex)
                self.tree.expandAll()
                return

        # print(f"set filter wildcard: '{text}'")
        self.proxy_model.setFilterRegularExpression(text)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 不区分大小写
        self.tree.expandAll()

if __name__ == '__main__':
    json_data = [
        {
            "name": "NestedStateMachine",
            "children": [
                {
                    "name": "State1",
                    "on_enter": ["enter1.1", "enter1.2", "enter1.3"],
                    "children": [
                        "Node1",
                        {
                            "name": "Node2",
                            "on_enter": ["enter_node_2.1", "enter_node_2.2", "enter_node_2.3"]
                        }
                    ],
                    "initial": "Node1"
                },
                {
                    "name": "State2",
                    "initial": "Node1"
                }
            ]
        }
    ]

    app = QApplication(sys.argv)
    viewer = StateMachineJsonViewer(json_data)
    viewer.setGeometry(300, 300, 600, 800)
    viewer.set_white_theme()
    viewer.show()
    sys.exit(app.exec_())
