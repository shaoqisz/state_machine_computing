import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QMainWindow, QMenuBar, QMenu, QFormLayout, QGridLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, Qt


class ConfigPage(QWidget):
    config_changed_signal = pyqtSignal()
    def __init__(self, icon=None):
        super().__init__()
        
        self.icon = icon

        self.initUI()
        self.load_config()

    def initUI(self):

        self.setWindowTitle("Configure")
        if self.icon is not None:
            self.setWindowIcon(self.icon)
            
        layout = QGridLayout()

        # 主资源文件配置
        self.main_resource_label = QLabel("State Machine File")
        self.main_resource_input = QLineEdit()
        self.main_resource_button = QPushButton("Select File")
        self.main_resource_button.clicked.connect(self.select_main_resource)

        layout.addWidget(self.main_resource_label, 0, 1)
        layout.addWidget(self.main_resource_input, 0, 2)
        layout.addWidget(self.main_resource_button, 0, 3)

        # 辅资源路径配置
        self.secondary_resource_label = QLabel("Transitions File")
        self.secondary_resource_input = QLineEdit()
        self.secondary_resource_button = QPushButton("Select Directory")

        layout.addWidget(self.secondary_resource_label, 1, 1)
        layout.addWidget(self.secondary_resource_input, 1, 2)
        layout.addWidget(self.secondary_resource_button, 1, 3)

        # 保存按钮
        self.save_button = QPushButton("Apply")
        self.save_button.clicked.connect(self.save_config)
        layout.addWidget(self.save_button, 2, 3)

        self.secondary_resource_button.clicked.connect(self.select_secondary_resource)

        self.setLayout(layout)

        self.resize(700, 150)

    def select_main_resource(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select", "", "Json File (*.json)")
        if file_path:
            self.main_resource_input.setText(file_path)

    def select_secondary_resource(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select")
        if dir_path:
            self.secondary_resource_input.setText(dir_path)

    def save_config(self):
        config = {
            "main_resource": self.main_resource_input.text(),
            "secondary_resource": self.secondary_resource_input.text()
        }
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

        self.config_changed_signal.emit()

    def load_config(self):
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
                self.main_resource_input.setText(config.get("main_resource", ""))
                self.secondary_resource_input.setText(config.get("secondary_resource", ""))


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
    