import sys
import json
import os
from enum import Enum 
import importlib


from PyQt5.QtWidgets import QApplication, QWidget, QCheckBox, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QMessageBox, QInputDialog, QPushButton, QLineEdit, QFileDialog, QMainWindow, QMenuBar, QMenu, QFormLayout, QGridLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, Qt



class Theme(Enum):
    white = 0
    black = 1

class ConfigPage(QWidget):
    config_changed_signal = pyqtSignal()
    animation_changed_signal = pyqtSignal(bool)
    theme_changed_signal = pyqtSignal(Theme)

    def __init__(self, icon=None):
        super().__init__()
        
        self.icon = icon

        self.initUI()
        self.load_config()

        self.connect_signal_and_slot()

    def initUI(self):

        self.setWindowTitle("Configure")
        if self.icon is not None:
            self.setWindowIcon(self.icon)

        main_layout = QVBoxLayout()

        layout = QGridLayout()

        # 主资源文件配置
        self.main_resource_label = QLabel("State Machine File")
        self.main_resource_input = QLineEdit()
        self.main_resource_button = QPushButton("Select")

        row = 0
        column = 0
        self.config_name_combobox = QComboBox()

        layout.addWidget(QLabel('Name'), row, 0)
        column += 1
        layout.addWidget(self.config_name_combobox, row, column)
        column += 1

        two_buttons_widget = QWidget()
        two_buttons_widget.setLayout(QHBoxLayout())
        self.delete_config_button = QPushButton("-")
        self.add_config_button = QPushButton("+")
        two_buttons_widget.layout().addWidget(self.delete_config_button)
        two_buttons_widget.layout().addWidget(self.add_config_button)
        layout.addWidget(two_buttons_widget, row, column)
        two_buttons_widget.setMaximumWidth(100)
        two_buttons_widget.layout().setContentsMargins(0,0,0,0)
        two_buttons_widget.layout().setSpacing(4)

        row += 1
        column = 0
        layout.addWidget(self.main_resource_label, row, column)
        column += 1
        layout.addWidget(self.main_resource_input, row, column)
        column += 1
        layout.addWidget(self.main_resource_button, row, column)
        column += 1

        row += 1
        column = 0
        self.secondary_resource_label = QLabel("Transitions Directory")
        self.secondary_resource_input = QLineEdit()
        self.secondary_resource_button = QPushButton("Select")

        layout.addWidget(self.secondary_resource_label, row, column)
        column += 1
        layout.addWidget(self.secondary_resource_input, row, column)
        column += 1
        layout.addWidget(self.secondary_resource_button, row, column)
        column += 1

        self.enable_custom_matter = QCheckBox('Custom Matter')
        self.enable_custom_matter.setChecked(False)
        self.custom_matter_input = QLineEdit()
        self.custom_matter_button = QPushButton("Select")
        self.custom_matter_input.setEnabled(False)
        self.custom_matter_button.setEnabled(False)

        row += 1
        column = 0
        layout.addWidget(self.enable_custom_matter, row, column)
        column += 1
        layout.addWidget(self.custom_matter_input, row, column)
        column += 1
        layout.addWidget(self.custom_matter_button, row, column)
        column += 1

        row += 1
        column = 0
        self.animation_options = QComboBox()
        self.animation_options.addItems(['No', 'Yes'])
        layout.addWidget(QLabel('Transition Animation'), row, column)
        column += 1
        layout.addWidget(self.animation_options, row, column)

        row += 1
        column = 0

        default_gate_widget = QWidget()
        default_gate_widget.setLayout(QHBoxLayout())
        default_gate_widget.layout().setContentsMargins(0,0,0,0)
        self.enable_default_enter_checkbox = QCheckBox("Default enter()")
        self.enable_default_exit_checkbox = QCheckBox("Default exit()")
        default_gate_widget.layout().addWidget(self.enable_default_enter_checkbox)
        default_gate_widget.layout().addWidget(self.enable_default_exit_checkbox)
        default_gate_widget.setToolTip('Default gates only synthesized when no one was specified')
        default_gate_widget.setMaximumHeight(36)

        layout.addWidget(QLabel('Default Gate'), row, column)
        column += 1
        layout.addWidget(default_gate_widget, row, column)

        row += 1
        column = 0
        self.theme_options = QComboBox()
        self.theme_options.addItems(['White', 'Black'])
        layout.addWidget(QLabel('Theme'), row, column)
        column += 1
        layout.addWidget(self.theme_options, row, column)

        main_layout.addLayout(layout)

        self.setLayout(main_layout)

        # self.resize(700, 150)

    def get_matter_lib(self):
        lib = None
        if self.enable_custom_matter.isChecked() and len(self.custom_matter_input.text()) > 0:
            # lib = importlib.import_module(self.custom_matter_input.text())
            module_path = self.custom_matter_input.text().replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]

            # 获取模块所在的目录
            module_dir = '/'.join(self.custom_matter_input.text().split('/')[:-1])
            if module_dir:
                # 将模块所在的目录添加到 sys.path 中
                sys.path.append(module_dir)

            try:
                # 导入模块
                lib = importlib.import_module(module_path)
                return lib
            except ImportError as e:
                print(f"导入模块时出错: {e}")
                return None

    def enable_custom_matter_slot(self, state):
        enabled = (state == Qt.CheckState.Checked)
        self.custom_matter_input.setEnabled(enabled)
        self.custom_matter_button.setEnabled(enabled)

        reply = QMessageBox.question(self, 'Reminder', f'This setting must to reload config to take effect. Do you want to reload it now?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config_changed_signal.emit()

    def connect_signal_and_slot(self):
        self.main_resource_button.clicked.connect(self.select_main_resource)
        self.add_config_button.clicked.connect(self.add_new_config)
        self.delete_config_button.clicked.connect(self.delete_current_config)
        self.config_name_combobox.currentIndexChanged.connect(self.on_config_selected)
        self.secondary_resource_button.clicked.connect(self.select_secondary_resource)
        self.custom_matter_button.clicked.connect(self.select_custom_matter)

        self.animation_options.currentIndexChanged.connect(lambda enabled=bool(self.animation_options.currentIndex()): self.animation_changed_signal.emit(enabled))

        self.theme_options.currentIndexChanged.connect(self.theme_options_changed)

        self.enable_default_enter_checkbox.stateChanged.connect(self.enable_default_gate_checkbox_changed)
        self.enable_default_exit_checkbox.stateChanged.connect(self.enable_default_gate_checkbox_changed)

        self.enable_custom_matter.stateChanged.connect(self.enable_custom_matter_slot)


    def enable_default_gate_checkbox_changed(self, state):
        reply = QMessageBox.question(self, 'Reminder', f'This setting must to reload config to take effect. Do you want to reload it now?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.config_changed_signal.emit()

    def theme_options_changed(self, index):
        theme = Theme(index)
        self.theme_changed_signal.emit(theme)

    def select_main_resource(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select", "", "Json File (*.json)")
        if file_path:
            base_path = os.getcwd()
            relative_path = os.path.relpath(file_path, base_path)
            self.main_resource_input.setText(relative_path)

    def select_secondary_resource(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select")
        if dir_path:
            base_path = os.getcwd()
            relative_path = os.path.relpath(dir_path, base_path)
            self.secondary_resource_input.setText(relative_path)

    def select_custom_matter(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select", "", "Python File (*.py)")
        if file_path:
            base_path = os.getcwd()
            relative_path = os.path.relpath(file_path, base_path)
            self.custom_matter_input.setText(relative_path)


    def add_new_config(self):
        config_name, ok = QInputDialog.getText(self, "New Config", "Input the config name:")
        if ok and config_name:
            self.configs[config_name] = {
                "main_resource": "",
                "secondary_resource": ""
            }
            self.config_name_combobox.addItem(config_name)
            self.config_name_combobox.setCurrentText(config_name)
            self.main_resource_input.setText("")
            self.secondary_resource_input.setText("")

    def delete_current_config(self):
        current_config_name = self.config_name_combobox.currentText()
        if current_config_name:
            reply = QMessageBox.question(self, 'Delete', f'Are you sure you want to delete {current_config_name} ?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.configs[current_config_name]
                index = self.config_name_combobox.currentIndex()
                self.config_name_combobox.removeItem(index)
                if self.config_name_combobox.count() > 0:
                    self.config_name_combobox.setCurrentIndex(0)
                    self.load_config_to_ui()
                else:
                    self.main_resource_input.setText("")
                    self.secondary_resource_input.setText("")

    def save_config(self):
        current_config_name = self.config_name_combobox.currentText()
        if current_config_name:
            self.configs[current_config_name] = {
                "main_resource": self.main_resource_input.text(),
                "secondary_resource": self.secondary_resource_input.text(),
                "enable_custom_matter": self.enable_custom_matter.isChecked(),
                "custom_matter": self.custom_matter_input.text()
            }
            data = {
                "configs": self.configs,
                "current_config": current_config_name,
                "animation_enabled": self.animation_options.currentIndex(),

                "enable_default_enter": self.enable_default_enter_checkbox.isChecked(),
                "enable_default_exit": self.enable_default_exit_checkbox.isChecked(),

                "current_theme": self.theme_options.currentIndex()
            }
            with open("config.json", "w") as f:
                json.dump(data, f, indent=4)

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                data = json.load(f)
                self.configs = data.get("configs", {})
                current_config = data.get("current_config")
                animation_enabled = data.get("animation_enabled")

                enable_default_enter = data.get("enable_default_enter")
                enable_default_exit = data.get("enable_default_exit")

                current_theme = data.get("current_theme")


            if animation_enabled:
                self.animation_options.setCurrentIndex(animation_enabled)

            if enable_default_enter:
                self.enable_default_enter_checkbox.setChecked(enable_default_enter)

            if enable_default_exit:
                self.enable_default_exit_checkbox.setChecked(enable_default_exit)

            if current_theme:
                self.theme_options.setCurrentIndex(current_theme)

            
            for config_name in self.configs.keys():
                self.config_name_combobox.addItem(config_name)

            if current_config and current_config in self.configs:
                self.config_name_combobox.setCurrentText(current_config)
                self.load_config_to_ui()
            elif self.config_name_combobox.count() > 0:
                self.config_name_combobox.setCurrentIndex(0)
                self.load_config_to_ui()
        else:
            self.configs = {}

    def load_config_to_ui(self):
        current_config_name = self.config_name_combobox.currentText()
        if current_config_name:
            config = self.configs[current_config_name]
            self.main_resource_input.setText(config.get("main_resource", ""))
            self.secondary_resource_input.setText(config.get("secondary_resource", ""))
            enable_custom_matter = config.get("enable_custom_matter")
            custom_matter = config.get("custom_matter")
            if enable_custom_matter and enable_custom_matter is True:
                self.enable_custom_matter.setChecked(True)
                self.custom_matter_input.setEnabled(True)
                self.custom_matter_button.setEnabled(True)
            else:
                self.enable_custom_matter.setChecked(False)

            if custom_matter:
                self.custom_matter_input.setText(custom_matter)

    def on_config_selected(self):
        self.load_config_to_ui()

        self.config_changed_signal.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def closeEvent(self, a0):
        self.save_config()
        return super().closeEvent(a0)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # 创建菜单栏
        menubar = self.menuBar()
        settings_menu = QMenu("Settings", self)
        settings_action = settings_menu.addAction("Open Config Page")
        settings_action.triggered.connect(self.open_config_page)
        menubar.addMenu(settings_menu)

        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('Config Page Example')
        self.show()

    def open_config_page(self):
        self.config_page = ConfigPage()
        self.setCentralWidget(self.config_page)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec_())
    