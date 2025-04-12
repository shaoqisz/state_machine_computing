import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox, QHeaderView, QAbstractItemView

class StateMachineJsonViewer(QWidget):
    def __init__(self, json_data=None):
        super().__init__()

        self.initUI(json_data)
        # self.set_white_theme()

    def set_white_theme(self):
        self.setStyleSheet("""
            QTreeView {
                font-size: 16px;
                border-radius: 8px;
                padding: 5px;
                border: 1px solid gray;
            }
            QHeaderView::section {
                border: 1px solid #d9dcdb;
            }
            QTreeView::item {
                padding: 5px;
                height: 12px;
            }
        """)
    def set_black_theme(self):
        self.setStyleSheet("""
            QTreeView {
                background-color: black;
                gridline-color: gray;
                font-size: 16px;
                border-radius: 8px;
                padding: 5px;
                height: 12px;
            }
            QHeaderView::section {
                background-color: black;
                border: 1px solid gray;
                padding: 5px;
            }
            QTreeView::item {
                background-color: black;
                padding: 5px;
                height: 12px;
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
        

    def set_json_data(self, json_data):
        self.tree.clear()
        self.populate_tree(self.tree.invisibleRootItem(), json_data)
        self.tree.expandAll()

    def initUI(self, json_data):
        self.setWindowTitle('State Machine Json Viewer')
        # self.setGeometry(300, 300, 600, 800)

        layout = QVBoxLayout()

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Key', 'Value'])

        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.set_json_data(json_data)

        self.tree.setContextMenuPolicy(3)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.edit_item)

        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_as_json)

        layout.addWidget(self.tree)
        # layout.addWidget(save_button)

        layout.setContentsMargins(0,0,0,0)

        self.setLayout(layout)

    def populate_tree(self, parent, data):
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, key)
                if isinstance(value, (dict, list)):
                    self.populate_tree(item, value)
                else:
                    item.setText(1, str(value))
        elif isinstance(data, list):
            for index, value in enumerate(data):
                item = QTreeWidgetItem(parent)
                item.setText(0, f"[{index}]")
                if isinstance(value, (dict, list)):
                    self.populate_tree(item, value)
                else:
                    item.setText(1, str(value))

    def get_parent(self, item, times):
        parent = item
        for i in range(times):
            if parent is None:
                break
            parent = parent.parent()
        return parent

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)

        is_digit = self.is_digit_item(item)
        has_children = self.has_property(item, 'children')

        has_on_enter = self.has_property(item, 'on_enter')
        has_on_exit = self.has_property(item, 'on_exit')

        parent_is_children_none = self.parent_is_children_none(item)

        name_to_set_initial = ''
        parent_to_set_initial = None
        if item.text(0) == 'name': 
            parent_to_set_initial = self.get_parent(item, 3) # item.parent().parent().parent()
            if parent_to_set_initial:
                name_to_set_initial = item.text(1)

        elif is_digit and len(item.text(1)) > 0 and parent_is_children_none: 
            parent_to_set_initial = self.get_parent(item, 2) # item.parent().parent()
            if parent_to_set_initial:
                name_to_set_initial = item.text(1)

        elif is_digit and len(item.text(1)) == 0 and parent_is_children_none:
            parent_to_set_initial = self.get_parent(item, 2) # item.parent().parent()
            if parent_to_set_initial:
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.text(0) == 'name':
                        name_to_set_initial = child.text(1)
                        break

        if parent_to_set_initial:
            set_initial_state_action = menu.addAction("Set as initial state")
            set_initial_state_action.triggered.connect(lambda b, item=parent_to_set_initial, key='initial', value=name_to_set_initial: 
                                                       self.set_key_value(item, key, value))


        if is_digit and parent_is_children_none:
            if not has_on_enter:
                action = menu.addAction("Add on_enter [...]")
                action.triggered.connect(lambda b, item=item, gate_name='on_enter': self.add_gate(item, gate_name))

            if not has_on_exit:
                action = menu.addAction("Add on_exit [...]")
                action.triggered.connect(lambda b, item=item, gate_name='on_exit': self.add_gate(item, gate_name))

            if not has_children:
                action = menu.addAction("Add children [...]")
                action.triggered.connect(lambda b, item=item: self.add_children_list(item))

        if self.can_add_children(item):
            action = menu.addAction("Add a child")
            action.triggered.connect(lambda b, item=item: self.add_list_item(item))

        action = menu.addAction("Delete")
        if item.text(0) == 'name':
            action.triggered.connect(lambda b, item=item: self.delete_item(item.parent()))
        else:
            action.triggered.connect(lambda b, item=item: self.delete_item(item))

        action = menu.exec_(self.tree.viewport().mapToGlobal(position))


    def add_children_list(self, parent_item):
        is_string_node = self.is_string_node(parent_item)
        if is_string_node is True:
            self.add_key_value(parent_item, 'name', parent_item.text(1))
            self.add_children(parent_item)
            parent_item.setText(1, '')
        else:
            self.add_children(parent_item)

        parent_item.setExpanded(True)

    def add_gate(self, parent_item, gate_name):
        is_string_node = self.is_string_node(parent_item)
        if is_string_node is True:
            self.add_key_value(parent_item, 'name', parent_item.text(1))
            self.add_key_value(parent_item, gate_name, '')
            parent_item.setText(1, '')
        else:
            self.add_key_value(parent_item, gate_name, '')
        
        parent_item.setExpanded(True)

    def is_digit_item(self, item):
        key = item.text(0)
        if key.startswith('[') and key.endswith(']'):
            key = key[1:-1]
        
        return key.isdigit()

    def has_property(self, item, name):
        if item is not None:
            for i in range(item.childCount()):
                child = item.child(i)
                if child.text(0) == name:
                    return True
        return False
    
    def can_add_children(self, item):
        if item.text(0) == "children" or item.text(0) == "on_enter" or item.text(0) == "on_exit":
            return True
        return False
    
    def is_string_node(self, item):
        return len(item.text(1)) > 0
    
    def parent_is_children_none(self, item):
        parent = item.parent()
        if parent is None:
            return True
        return parent.text(0) == 'children'
    
    def add_key_value(self, parent_item, key, value):
        new_item = QTreeWidgetItem(parent_item)
        new_item.setText(0, key)
        new_item.setText(1, value)
        parent_item.setExpanded(True)

    def set_key_value(self, parent_item, key, value):
        found = False
        if parent_item:
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == key:
                    child.setText(1, value)
                    found = True
            if not found:
                new_item = QTreeWidgetItem(parent_item)
                new_item.setText(0, key)
                new_item.setText(1, value)

            parent_item.setExpanded(True)

    def add_children(self, parent_item):
        new_list_item = QTreeWidgetItem(parent_item)
        new_list_item.setText(0, "children")
        new_list_item.setText(1, "")
        parent_item.setExpanded(True)

    def add_list_item(self, parent_item):
        value, ok = QInputDialog.getText(self, "Add List Item", "Enter list item:")
        if ok:
            index = parent_item.childCount()
            new_item = QTreeWidgetItem(parent_item)
            new_item.setText(0, f"[{index}]")
            new_item.setText(1, value)
            parent_item.setExpanded(True)

    def delete_item(self, item, need_confirm=False):
        if need_confirm is True:
            reply = QMessageBox.question(self, 'Confirm Deletion', 'Are you sure you want to delete this item?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
                
        parent = item.parent()
        if parent:
            
            is_digit = self.is_digit_item(item)
            index = parent.indexOfChild(item)
            parent.takeChild(index)
            if is_digit:
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    if self.is_digit_item(child):
                        child.setText(0, f"[{i}]")
        else:
            root = self.tree.invisibleRootItem()
            index = root.indexOfChild(item)
            root.takeChild(index)


    def edit_item(self, item, column):
        # if column == 0 and item.text(0).startswith('['):
        #     return
        if column == 0:
            return
        item.setFlags(item.flags() | 0x0002)
        self.tree.editItem(item, column)

    def save_as_json(self):
        root_item = self.tree.invisibleRootItem()
        json_data = self.tree_to_json(root_item)
        try:
            with open('output.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, 'Success', 'JSON file saved successfully.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to save JSON file: {str(e)}')

    def tree_to_json(self, parent_item):
        if all(child.text(0).startswith('[') for child in [parent_item.child(i) for i in range(parent_item.childCount())]):
            result = []
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.childCount() > 0:
                    child_value = self.tree_to_json(child)
                    if child_value:
                        result.append(child_value)
                elif child.text(1).strip():
                    result.append(child.text(1))
            return result
        else:
            result = {}
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                key = child.text(0)
                if child.childCount() > 0:
                    value = self.tree_to_json(child)
                    if value:
                        result[key] = value
                elif child.text(1).strip():
                    result[key] = child.text(1)
            return result


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
    viewer.show()
    sys.exit(app.exec_())