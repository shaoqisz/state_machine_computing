import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPlainTextEdit, QHBoxLayout, QLineEdit, QPushButton, QStackedLayout, QLabel, QAction, QMenu
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QTextDocument


class Theme:
    white = 0
    black = 1


class TextEditSearch(QWidget):
    def __init__(self, text_edit=None, parent=None):
        super().__init__(parent)
        self.initUI(text_edit)

    def initUI(self, text_edit):
        # 创建文本编辑框
        self.text_edit = text_edit
        if self.text_edit is None:
            self.text_edit = QPlainTextEdit(self)
            self.text_edit.setPlainText("Example text for testing search functionality. This is an example text that can be searched.")

        self.first_time_to_update_search_widget_position= True
        self.text_edit.textChanged.connect(lambda timer=QTimer() : timer.singleShot(1, self.update_search_widget_position))

        # 创建搜索框组件
        self.search_layout = QHBoxLayout()
        # 减少布局的边距和间距
        self.search_layout.setContentsMargins(5, 5, 5, 5)
        self.search_layout.setSpacing(5)

        self.search_input = QLineEdit()

        self.prev_button = QPushButton("Prev")
        self.prev_button.setFixedWidth(50)
        self.next_button = QPushButton("Next")
        self.next_button.setFixedWidth(50)

        label = QLabel('Find')
        label.setStyleSheet("border: 0px;")
        self.search_layout.addWidget(label)
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.prev_button)
        self.search_layout.addWidget(self.next_button)

        self.search_widget = QWidget()

        self.search_widget.mousePressEvent = self.on_search_widget_mouse_press
        self.search_widget.mouseMoveEvent = self.on_search_widget_mouse_move
        self.search_widget.mouseReleaseEvent = self.on_search_widget_mouse_release

        self.search_widget.setLayout(self.search_layout)
        self.search_widget.setVisible(False)

        self.search_widget_max_size = QSize(300, 30)
        self.search_widget.setMaximumSize(self.search_widget_max_size)

       # 创建堆叠布局
        stacked_layout = QStackedLayout()
        stacked_layout.addWidget(self.text_edit)
        stacked_layout.addWidget(self.search_widget)
        stacked_layout.setCurrentWidget(self.text_edit)

        # 绑定搜索框按钮的点击事件
        self.prev_button.clicked.connect(self.prev_search)
        self.next_button.clicked.connect(self.next_search)
        self.search_input.textChanged.connect(self.search_text)
        self.search_input.returnPressed.connect(self.next_search)

        # 绑定 Ctrl+F 快捷键
        self.text_edit.installEventFilter(self)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(stacked_layout)

        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        self.setLayout(main_layout)
        self.setWindowTitle('Search Text Edit')

        self.set_white_theme()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut('Ctrl+C')

        copy_action.triggered.connect(self.text_edit.copy)
        menu.addAction(copy_action)

        paste_action = QAction("SelectAll", self)
        paste_action.setShortcut('Ctrl+A')
        paste_action.triggered.connect(self.text_edit.selectAll)

        menu.addAction(paste_action)

        menu.addSeparator()

        sub_menu = QMenu('Theme Change', self)
        menu.addMenu(sub_menu)
        
        white_theme_action = sub_menu.addAction("White")
        white_theme_action.setCheckable(True)
        white_theme_action.triggered.connect(self.set_white_theme)

        black_theme_action = sub_menu.addAction("Black")
        black_theme_action.setCheckable(True)

        black_theme_action.triggered.connect(self.set_black_theme)

        if self.current_theme == Theme.white:
            white_theme_action.setChecked(True)
        elif self.current_theme == Theme.black:
            black_theme_action.setChecked(True)

        menu.exec_(event.globalPos())

    def set_white_theme(self):
        self.current_theme = Theme.white
        self.setStyleSheet('background: white; color: black; border: 1px solid gray;')
        # self.search_widget.setStyleSheet("background-color: white; border: 1px solid gray;")

    def set_black_theme(self):
        self.current_theme = Theme.black
        self.setStyleSheet('background: black; color: white; border: 1px solid gray;')
        # self.search_widget.setStyleSheet("background-color: black; border: 1px solid gray;")

    def on_search_widget_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()

    def on_search_widget_mouse_move(self, event):
        if self.offset is not None and event.buttons() == Qt.LeftButton:
            new_pos = self.search_widget.pos() + event.pos() - self.offset
            self.search_widget.move(new_pos)

    def on_search_widget_mouse_release(self, event):
        self.offset = None
        self.update_search_widget_position()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
            self.search_widget.setVisible(not self.search_widget.isVisible())
            if self.search_widget.isVisible():
                self.update_search_widget_position()
                self.search_input.setFocus()  # 让搜索输入框获取焦点
        elif event.key() == Qt.Key_Escape and self.search_widget.isVisible():
            self.search_widget.setVisible(False)
            self.text_edit.setFocus()  # 让文本编辑框重新获得焦点
        else:
            super().keyPressEvent(event)

    # def eventFilter(self, obj, event):
    #     if event.type() == event.KeyPress:
    #         if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
    #             self.search_widget.setVisible(not self.search_widget.isVisible())
    #             if self.search_widget.isVisible():
    #                 self.update_search_widget_position()
    #                 self.search_input.setFocus()  # 让搜索输入框获取焦点
    #             return True
    #     return super().eventFilter(obj, event)

    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key_Escape and self.search_widget.isVisible():
    #         self.search_widget.setVisible(False)
    #         self.text_edit.setFocus()  # 让文本编辑框重新获得焦点
    #     else:
    #         super().keyPressEvent(event)

    def update_search_widget_position(self):
        left_margin = 2
        top_margin = 2
        text_edit_geometry = self.text_edit.geometry()

        # 检查滚动条是否可见
        scrollbar_width = 2
        if self.text_edit.verticalScrollBar().isVisible():
            scrollbar_width += self.text_edit.verticalScrollBar().width()

        # 计算 search_widget 的最大可用宽度
        available_width = text_edit_geometry.width() - left_margin - scrollbar_width
        w = min(self.search_widget_max_size.width(), available_width)
        h = min(self.search_widget_max_size.height(), text_edit_geometry.height())

        self.search_widget.resize(w, h)

        # 计算 search_widget 的位置
        x, y = self.search_widget.pos().x(), self.search_widget.pos().y()

        if self.first_time_to_update_search_widget_position is True:
            self.first_time_to_update_search_widget_position = False
            
            x = text_edit_geometry.x() + text_edit_geometry.width() - w - scrollbar_width # right
            y = text_edit_geometry.y() + text_edit_geometry.height() - h - top_margin # down
        else:

            if text_edit_geometry.width() / 2 > (self.search_widget.geometry().x() + self.search_widget.geometry().width()/2):
                x = text_edit_geometry.x() + left_margin # left
            else:
                x = text_edit_geometry.x() + text_edit_geometry.width() - w - scrollbar_width # right

            if text_edit_geometry.height() / 2 > (self.search_widget.geometry().y() + self.search_widget.geometry().height()/2):
                y = text_edit_geometry.y() + top_margin # up 
            else:
                y = text_edit_geometry.y() + text_edit_geometry.height() - h - top_margin # down

        self.search_widget.move(x, y)

    def resizeEvent(self, event):
        # 窗口大小改变时更新搜索框位置
        if self.search_widget.isVisible():
            self.update_search_widget_position()
        return super().resizeEvent(event)

    def search_text(self):
        search_text = self.search_input.text()
        if search_text:
            found = self.text_edit.find(search_text)
            if not found:
                # 若未找到，移动到文档开头重新搜索
                self.text_edit.moveCursor(self.text_edit.textCursor().Start)
                self.text_edit.find(search_text)

    def prev_search(self):
        search_text = self.search_input.text()
        if search_text:
            found = self.text_edit.find(search_text, QTextDocument.FindBackward)
            if not found:
                # 若未找到，移动到文档末尾重新搜索
                self.text_edit.moveCursor(self.text_edit.textCursor().End)
                self.text_edit.find(search_text, QTextDocument.FindBackward)

    def next_search(self):
        self.search_text()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # text_edit = QPlainTextEdit(self)

        text_edit_search = TextEditSearch(text_edit=None)
        layout.addWidget(text_edit_search)

        self.setLayout(layout)

        self.setWindowTitle('TextEditSearch')
        self.setGeometry(300, 200, 600, 800)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
