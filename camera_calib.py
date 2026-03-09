# import cv2
# import numpy as np
# import sys

# from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
# from PyQt5.QtCore import QTimer
# from PyQt5.QtGui import QImage, QPixmap


# class CameraAlignmentWindow(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Chip Alignment Camera")

#         self.video_label = QLabel()
#         self.angle_label = QLabel("Angle: --°")

#         layout = QVBoxLayout()
#         layout.addWidget(self.video_label)
#         layout.addWidget(self.angle_label)
#         self.setLayout(layout)

#         self.cap = cv2.VideoCapture(1)  # Adjust index if needed
#         self.timer = QTimer()
#         self.timer.timeout.connect(self.update_frame)
#         self.timer.start(30)

#     def update_frame(self):
#         ret, frame = self.cap.read()
#         if not ret:
#             return

#         # Detection
#         angle, annotated = self.detect_angle(frame)
#         self.angle_label.setText(f"Angle: {angle:.2f}°")

#         # Convert to Qt image
#         rgb_image = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
#         h, w, ch = rgb_image.shape
#         bytes_per_line = ch * w
#         qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
#         self.video_label.setPixmap(QPixmap.fromImage(qt_image))

#     def detect_angle(self, frame):
#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#         blur = cv2.GaussianBlur(gray, (5, 5), 0)
#         edges = cv2.Canny(blur, 50, 150)
#         contours, _ = cv2.findContours(
#             edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
#         )

#         angle = 0
#         for cnt in contours:
#             if cv2.contourArea(cnt) > 1000:
#                 rect = cv2.minAreaRect(cnt)
#                 box = cv2.boxPoints(rect).astype(np.int32)
#                 cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
#                 angle = rect[2]
#                 if angle < -45:
#                     angle += 90
#                 break

#         return angle, frame

#     def closeEvent(self, event):
#         self.cap.release()
#         self.timer.stop()
#         event.accept()


# # Manque pour debug d'ajouter une instance stand alone
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     with open(
#         r"C:\Users\tommy\Desktop\New_LOCARS\src\LOCARS\style.qss", "r"
#     ) as style_file:
#         style_str = style_file.read()
#     app.setStyleSheet(style_str)
#     window = CameraAlignmentWindow()
#     window.show()
#     sys.exit(app.exec_())

import cv2


def list_available_cameras(max_index=5):
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.read()[0]:
            print(f"Camera found at index {i}")
        cap.release()


list_available_cameras()
