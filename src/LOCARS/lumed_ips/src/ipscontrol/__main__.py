import sys

from PyQt5.QtWidgets import QApplication, QMainWindow

from ipscontrol.laser_widget import IpsLaserwidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.show()

    window.setCentralWidget(IpsLaserwidget())

    app.exec_()
