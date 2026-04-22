import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt

from main import process_input


class ChatbotUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Train Ticket Chatbot")
        self.resize(700, 500)

        # Information state
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

        # main layout

        main_layout = QHBoxLayout()
        
        # Chat area on the left
        chat_layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.input_field)
        chat_layout.addWidget(self.send_button)


        # Journey information on the right
        info_layout = QVBoxLayout()

        self.info_title = QLabel("Journey Info")
        self.info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_title.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.info_box = QLabel()
        self.info_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_box.setFrameStyle(QFrame.Shape.Box)
        self.info_box.setStyleSheet("padding: 10px;")

        info_layout.addWidget(self.info_title)
        info_layout.addWidget(self.info_box)



        main_layout.addLayout(chat_layout, 3)
        main_layout.addLayout(info_layout, 1)

        self.setLayout(main_layout)

        # Initial display
        self.update_journey_display()

        # basic styling
        self.setStyleSheet("""
            QWidget {
                font-family: Arial;
                font-size: 14px;
            }
            QTextEdit {
                background-color: #777;
            }
            QLineEdit {
                padding: 5px;
            }
            QPushButton {
                padding: 6px;
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)


    # Updating the right panel

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


    # Sending a message

    def send_message(self):
        user_input = self.input_field.text().strip()

        if not user_input:
            return

        self.chat_display.append(f"You: {user_input}")

        response = process_input(user_input, self.journey)

        self.chat_display.append(f"Bot: {response}")

        self.input_field.clear()

        # Update side panel after every message
        self.update_journey_display()



# Running the UI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatbotUI()
    window.show()
    sys.exit(app.exec())