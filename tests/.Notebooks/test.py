import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel

class FileExplorerApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Explorer")
        self.setGeometry(100, 100, 400, 200)

        self.layout = QVBoxLayout()

        # Label to display selected file
        self.file_label = QLabel("No file selected", self)
        self.layout.addWidget(self.file_label)

        # Button to open the file explorer
        self.open_button = QPushButton("Open File Explorer", self)
        self.open_button.clicked.connect(self.open_file_dialog)
        self.layout.addWidget(self.open_button)

        # Button to open the selected file
        self.open_file_button = QPushButton("Open File", self)
        self.open_file_button.clicked.connect(self.open_selected_file)
        self.layout.addWidget(self.open_file_button)

        self.setLayout(self.layout)

    def open_file_dialog(self):
        # Open a file explorer dialog to select a file
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a File")
        if file_path:
            self.file_label.setText(f"Selected File: {file_path}")
            self.selected_file = file_path  # Store the selected file path

    def open_selected_file(self):
        # Open the selected file
        if hasattr(self, 'selected_file'):
            try:
                with open(self.selected_file, 'r') as file:
                    content = file.read()
                    print(f"File Content:\n{content}")  # Print the file content to the console
            except Exception as e:
                print(f"Error opening file: {e}")
        else:
            print("No file selected.")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = FileExplorerApp()
    window.show()

    sys.exit(app.exec())
