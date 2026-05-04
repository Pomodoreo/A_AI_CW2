import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame,
    QScrollArea
)
from PyQt6.QtCore import Qt

from main import process_input


class ChatBubble(QFrame):
    def __init__(self, text, is_user=True):
        super().__init__()

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(5, 2, 5, 2)

        # Label (You / Bot)
        role = QLabel("You" if is_user else "Bot")
        role.setStyleSheet("font-size:10px; color:#888;")

        # Message bubble
        bubble_layout = QHBoxLayout()
        bubble_layout.setContentsMargins(0, 0, 0, 0)

        message = QLabel(text)
        message.setWordWrap(True)
        message.setMaximumWidth(300)
        
        message.setTextFormat(Qt.TextFormat.RichText)
        message.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        message.setOpenExternalLinks(True)

        if is_user:
            bubble = QFrame()
            bubble.setStyleSheet("""
                QFrame {
                    background-color:#6c5ce7;
                    border-radius:10px;
                    padding:6px;
                }
                QLabel { color:white; font-size:13px; }
            """)
            inner = QVBoxLayout()
            inner.setContentsMargins(6, 4, 6, 4)
            inner.addWidget(message)
            bubble.setLayout(inner)

            bubble_layout.addStretch()
            bubble_layout.addWidget(bubble)

            outer_layout.addWidget(role, alignment=Qt.AlignmentFlag.AlignRight)

        else:
            bubble = QFrame()
            bubble.setStyleSheet("""
                QFrame {
                    background-color:#2f2f2f;
                    border-radius:10px;
                    padding:6px;
                }
                QLabel { color:white; font-size:13px; }
            """)
            inner = QVBoxLayout()
            inner.setContentsMargins(6, 4, 6, 4)
            inner.addWidget(message)
            bubble.setLayout(inner)

            bubble_layout.addWidget(bubble)
            bubble_layout.addStretch()

            outer_layout.addWidget(role, alignment=Qt.AlignmentFlag.AlignLeft)

        outer_layout.addLayout(bubble_layout)
        self.setLayout(outer_layout)


class ChatbotUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Train Chatbot")
        self.resize(900, 600)

        self.journey = {
            "from": None,
            "to": None,
            "from_options": None,
            "to_options": None,
            "date": None,
            "return_date": None,
            "ticket_type": None,
            "time": None,
            "return_time": None
        }

        self.init_ui()
        self.update_journey_display()

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # Chat area
        chat_container = QFrame()
        chat_container.setStyleSheet("""
            QFrame {
                background-color:#1e1e1e;
                border-radius:10px;
            }
        """)
        chat_layout = QVBoxLayout()

        # Scrollable chat
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border:none;")

        self.chat_widget = QWidget()
        self.chat_box = QVBoxLayout(self.chat_widget)
        self.chat_box.addStretch()

        self.scroll.setWidget(self.chat_widget)

        # Input row
        input_row = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.setStyleSheet(self.input_style())

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet(self.button_style())

        input_row.addWidget(self.input_field)
        input_row.addWidget(self.send_button)

        chat_layout.addWidget(self.scroll)
        chat_layout.addLayout(input_row)
        chat_container.setLayout(chat_layout)

        # Side Panel
        side_panel = QFrame()
        side_panel.setFixedWidth(250)
        side_panel.setStyleSheet("""
            QFrame {
                background-color:#2f2f2f;
                border-radius:10px;
                padding:10px;
            }
        """)

        side_layout = QVBoxLayout()

        title = QLabel("Journey Info")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:white;")

        self.info_box = QLabel()
        self.info_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_box.setStyleSheet("color:#ccc;")

        side_layout.addWidget(title)
        side_layout.addWidget(self.info_box)
        side_layout.addStretch()

        side_panel.setLayout(side_layout)

        # ===== FINAL LAYOUT =====
        main_layout.addWidget(chat_container, 3)
        main_layout.addWidget(side_panel, 1)

        self.setStyleSheet("background-color:#121212; color:white;")

    # Styles
    def input_style(self):
        return """
            QLineEdit {
                background-color:#2a2a2a;
                color:white;
                padding:8px;
                border-radius:6px;
                border:1px solid #444;
            }
        """

    def button_style(self):
        return """
            QPushButton {
                background-color:#6c5ce7;
                color:white;
                padding:8px 12px;
                border-radius:6px;
                font-weight:bold;
            }
            QPushButton:hover {
                background-color:#7d6ef0;
            }
        """

    # Chat handling
    def add_message(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        self.chat_box.insertWidget(self.chat_box.count() - 1, bubble)

        # auto scroll
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def send_message(self):
        user_input = self.input_field.text().strip()

        if not user_input:
            return

        self.add_message(user_input, True)

        response = process_input(user_input, self.journey)

        self.add_message(response, False)

        self.input_field.clear()
        self.update_journey_display()

    # Side Panel
    def update_journey_display(self):
        def format_value(val):
            return str(val) if val else "—"

        def format_time(val):
            if not val:
                return "—"
            return f"{val[:2]}:{val[2:]}"

        text = f"""
From: {format_value(self.journey['from'])}
To: {format_value(self.journey['to'])}

Date: {format_value(self.journey['date'])}
Time: {format_time(self.journey['time'])}

Return Date: {format_value(self.journey['return_date'])}
Return Time: {format_time(self.journey['return_time'])}

Ticket: {format_value(self.journey['ticket_type'])}
        """

        self.info_box.setText(text.strip())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI()
    window.show()
    sys.exit(app.exec())