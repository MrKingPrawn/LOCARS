import os

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = (
    "/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms"
)

import sys
import numpy as np
import pyvisa
import tomli
from PyQt5.QtCore import QSize, QTimer, pyqtSignal, pyqtSlot, QFile, QTextStream
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QWidget,
    QCheckBox,
    QGridLayout,
    QPushButton,
    QVBoxLayout,
)
from LOCARS_ui import Ui_MainWindow
from scipy.interpolate import interp1d
from PyQt5.QtGui import QFont, QColor, QPalette
import threading
import time
from functools import partial
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QPainter
from PyQt5.QtWidgets import QWidget

rm = pyvisa.ResourceManager()

# Page Classes
##############################################################log PAGE NOW########################################################
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from pathlib import Path
import datetime


class LogWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LOCARS Log Console")
        self.resize(700, 300)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        # Determine save path: Desktop or fallback to current dir
        today = datetime.date.today().isoformat()
        desktop_path = Path.home() / "Desktop"
        if not desktop_path.exists():
            desktop_path = Path.cwd()

        self.log_path = desktop_path / f"log_{today}_LOCARS.txt"

        try:
            self.log_file = open(self.log_path, "w", encoding="utf-8")
            self.text_edit.append(f"📝 Log file created at: {self.log_path}")
        except Exception as e:
            self.text_edit.append(f"❌ Failed to create log file: {e}")
            self.log_file = None

    def write(self, msg):
        msg = msg.strip()
        if msg:
            self.text_edit.append(msg)
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(msg + "\n")
                self.log_file.flush()
            except Exception as e:
                self.text_edit.append(f"❌ Log write failed: {e}")

    def flush(self):
        # Needed for compatibility with sys.stdout
        pass

    def closeEvent(self, event):
        try:
            if self.log_file and not self.log_file.closed:
                self.log_file.close()
        except Exception:
            pass
        event.accept()


##############################################################CHIP PAGE NOW########################################################
import os
import tomli
from PyQt5.QtWidgets import QWidget, QCheckBox, QGridLayout
from PyQt5.QtCore import Qt


class ChipPage(QWidget):
    def __init__(self, ui, printer):
        super().__init__()
        self.ui = ui  # Access main UI
        self.checkboxes = []  # Store checkbox references
        self.well_coordinates = {}  # Store coordinates with labels
        self.printer = printer

        # Connect chip selection buttons to loading function
        self.ui.button_32x.clicked.connect(lambda: self.load_chip_toml("32X.toml"))
        self.ui.button_32T.clicked.connect(lambda: self.load_chip_toml("32T.toml"))
        self.ui.button_96puits.clicked.connect(
            lambda: self.load_chip_toml("wellplate.toml")
        )

        # ✅ Connect Toggle & Save buttons
        self.ui.toggle_all_wells.clicked.connect(self.toggle_checkboxes)
        self.ui.save_toggledwells.clicked.connect(
            self.handle_save_active_wells
        )  # FIXED!

        # ✅ Use the QGridLayout instead of QLabel
        self.grid_layout = self.ui.wells_generated

    def load_chip_toml(self, filename):
        """Load the selected .toml file and generate the well grid."""
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Get script directory
        toml_path = os.path.join(base_dir, "..", "chips_toml", filename)  # Go up to src

        if not os.path.exists(toml_path):
            print(f"Error: {toml_path} not found.")
            return

        with open(toml_path, "rb") as f:
            chip_data = tomli.load(f)

        # Extract chip specs to dynamically generate well positions
        chip_specs = chip_data["Specs"]
        self.generate_wells(
            rows=chip_specs["rows"],
            cols=chip_specs["columns"],
            well_width=chip_specs["well_width"],
            well_height=chip_specs["well_height"],
            start_x=chip_specs["first_x"],
            start_y=chip_specs["first_y"],
        )

    def generate_wells(self, rows, cols, well_width, well_height, start_x, start_y):
        """Generate checkboxes inside QGridLayout based on chip specifications."""
        # Clear previous checkboxes
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.checkboxes = []  # Reset checkbox list
        self.well_coordinates = {}  # Reset coordinates dictionary

        for row in range(rows):
            for col in range(cols):
                well_x = start_x + col * well_width
                well_y = start_y + row * well_height
                well_label = f"({row+1}, {chr(65+col)})"  # Example: (1, A), (2, B)

                # Store coordinates in dictionary
                self.well_coordinates[well_label] = (well_x, well_y)

                # Create checkbox
                checkbox = QCheckBox(well_label)
                self.grid_layout.addWidget(checkbox, row, col)  # Place in grid
                self.checkboxes.append(checkbox)

        self.rows = rows
        self.cols = cols

    def toggle_checkboxes(self):
        """Toggle all checkboxes on/off."""
        new_state = not all(checkbox.isChecked() for checkbox in self.checkboxes)
        for checkbox in self.checkboxes:
            checkbox.setChecked(new_state)

    def handle_save_active_wells(self):
        """Handles saving wells and sending them to the AcquisitionPage."""
        try:
            active_wells = self.save_active_wells()  # ✅ Make sure it's from ChipPage

            # ✅ Ensure acquisition_page exists
            if (
                not hasattr(self.ui, "acquisition_page")
                or self.ui.acquisition_page is None
            ):
                print("❌ Acquisition Page is not initialized. Cannot update grid.")
                return

            # ✅ Ensure well coordinates exist
            if not self.well_coordinates:
                print("❌ No well coordinates found. Ensure chip is loaded first.")
                return

            print(f"🔎 Updating follow-up grid with {len(active_wells)} active wells")
            if hasattr(self.ui, "acquisition_page") and isinstance(
                self.ui.acquisition_page, AcquisitionPage
            ):
                print(
                    f"✅ Updating followup grid with {len(active_wells)} active wells."
                )
                self.ui.acquisition_page.update_followup_grid(
                    self.well_coordinates, active_wells
                )
            else:
                print("❌ Acquisition page not initialized yet.")

        except Exception as e:
            print(f"❌ Error in handle_save_active_wells: {e}")

    def save_active_wells(self):
        """Save selected wells and update AcquisitionPage."""
        active_wells = []
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                label = checkbox.text()
                if label in self.well_coordinates:
                    active_wells.append((label, self.well_coordinates[label]))

        # ✅ Update QLabel with the number of active wells
        self.ui.well_number.setText(f"{len(active_wells)} Active wells")

        # ✅ Fix: Use `self.ui.acquisition_page` Safely
        if hasattr(self.ui, "acquisition_page") and isinstance(
            self.ui.acquisition_page, AcquisitionPage
        ):
            print(f"✅ Updating followup grid with {len(active_wells)} active wells.")
            self.ui.acquisition_page.update_followup_grid(
                self.well_coordinates, active_wells
            )
        else:
            print("❌ Acquisition page not initialized yet.")

        return active_wells  # ✅ Return the list if needed


##############################################################PRINTER PAGE NOW########################################################


import threading
from PyQt5.QtWidgets import QWidget, QGridLayout, QCheckBox
from PyQt5.QtCore import Qt
from functools import partial
import pyvisa


class PrinterControlPage(QWidget):
    def __init__(
        self,
        ui,
        chip_page,
        printer,
    ):
        super().__init__()
        self.ui = ui  # Pass the main UI reference
        self.chip_page = chip_page
        self.printer = printer  # ✅ Use global printer reference from LOCARS
        self.wells = chip_page.well_coordinates

        # Timer for continuous movement
        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self.perform_continuous_move)

        self.current_direction = None
        self.current_increment = None
        self.moving = False
        self.movement_thread = None
        active_wells = self.chip_page.save_active_wells()
        # ✅ Fix: Ensure `self.ui.acquisition_page` exists before using it
        if hasattr(self.ui, "acquisition_page") and isinstance(
            self.ui.acquisition_page, AcquisitionPage
        ):
            active_wells = self.chip_page.save_active_wells()
            self.ui.acquisition_page.update_followup_grid(
                self.chip_page.well_coordinates, active_wells
            )
        else:
            print("❌ Acquisition page not initialized in PrinterControlPage.")

        # Initialize spinboxes and buttons
        self.initialize_spinboxes()
        self.connect_buttons()

    def initialize_spinboxes(self):
        """Set speed ranges for X, Y, and Z movement spinboxes."""
        self.ui.spinBox_xspeed.setRange(10, 5000)
        self.ui.spinBox_xspeed.setValue(2000)
        self.ui.spinBox_yspeed.setRange(10, 5000)
        self.ui.spinBox_yspeed.setValue(2000)
        self.ui.spinBox_zspeed.setRange(10, 5000)
        self.ui.spinBox_zspeed.setValue(1000)

    def connect_buttons(self):
        self.ui.minus_one_x.pressed.connect(
            partial(self.start_continuous_move, "X", -1)
        )
        self.ui.minus_one_x.released.connect(self.stop_continuous_move)
        self.ui.minus_ten_x.pressed.connect(
            partial(self.start_continuous_move, "X", -10)
        )
        self.ui.minus_ten_x.released.connect(self.stop_continuous_move)
        self.ui.minus_pointone_x.pressed.connect(
            partial(self.start_continuous_move, "X", -0.1)
        )
        self.ui.minus_pointone_x.released.connect(self.stop_continuous_move)
        self.ui.plus_one_x.pressed.connect(partial(self.start_continuous_move, "X", 1))
        self.ui.plus_one_x.released.connect(self.stop_continuous_move)
        self.ui.plus_ten_x.pressed.connect(partial(self.start_continuous_move, "X", 10))
        self.ui.plus_ten_x.released.connect(self.stop_continuous_move)
        self.ui.plus_pointone_x.pressed.connect(
            partial(self.start_continuous_move, "X", 0.1)
        )
        self.ui.plus_pointone_x.released.connect(self.stop_continuous_move)

        self.ui.minus_one_y.pressed.connect(
            partial(self.start_continuous_move, "Y", -1)
        )
        self.ui.minus_one_y.released.connect(self.stop_continuous_move)
        self.ui.minus_ten_y.pressed.connect(
            partial(self.start_continuous_move, "Y", -10)
        )
        self.ui.minus_ten_y.released.connect(self.stop_continuous_move)
        self.ui.minus_pointone_y.pressed.connect(
            partial(self.start_continuous_move, "Y", -0.1)
        )
        self.ui.minus_pointone_y.released.connect(self.stop_continuous_move)
        self.ui.plus_one_y.pressed.connect(partial(self.start_continuous_move, "Y", 1))
        self.ui.plus_one_y.released.connect(self.stop_continuous_move)
        self.ui.plus_ten_y.pressed.connect(partial(self.start_continuous_move, "Y", 10))
        self.ui.plus_ten_y.released.connect(self.stop_continuous_move)
        self.ui.plus_pointone_y.pressed.connect(
            partial(self.start_continuous_move, "Y", 0.1)
        )
        self.ui.plus_pointone_y.released.connect(self.stop_continuous_move)

        self.ui.minus_one_z.pressed.connect(
            partial(self.start_continuous_move, "Z", -1)
        )
        self.ui.minus_one_z.released.connect(self.stop_continuous_move)
        self.ui.minus_ten_z.pressed.connect(
            partial(self.start_continuous_move, "Z", -10)
        )
        self.ui.minus_ten_z.released.connect(self.stop_continuous_move)
        self.ui.minus_pointone_z.pressed.connect(
            partial(self.start_continuous_move, "Z", -0.1)
        )
        self.ui.minus_pointone_z.released.connect(self.stop_continuous_move)
        self.ui.plus_one_z.pressed.connect(partial(self.start_continuous_move, "Z", 1))
        self.ui.plus_one_z.released.connect(self.stop_continuous_move)
        self.ui.plus_ten_z.pressed.connect(partial(self.start_continuous_move, "Z", 10))
        self.ui.plus_ten_z.released.connect(self.stop_continuous_move)
        self.ui.plus_pointone_z.pressed.connect(
            partial(self.start_continuous_move, "Z", 0.1)
        )
        self.ui.plus_pointone_z.released.connect(self.stop_continuous_move)

        self.ui.home_x.clicked.connect(partial(self.home_axis, "G28 X"))
        self.ui.home_y.clicked.connect(partial(self.home_axis, "G28 Y"))
        self.ui.home_z.clicked.connect(partial(self.home_axis, "G28 Z"))
        self.ui.home_all.clicked.connect(partial(self.home_axis, "G28"))

        # Single move on click
        self.ui.minus_one_x.clicked.connect(partial(self.send_gcode_once, "X", -1))
        self.ui.minus_ten_x.clicked.connect(partial(self.send_gcode_once, "X", -10))
        self.ui.minus_pointone_x.clicked.connect(
            partial(self.send_gcode_once, "X", -0.1)
        )
        self.ui.plus_one_x.clicked.connect(partial(self.send_gcode_once, "X", 1))
        self.ui.plus_ten_x.clicked.connect(partial(self.send_gcode_once, "X", 10))
        self.ui.plus_pointone_x.clicked.connect(partial(self.send_gcode_once, "X", 0.1))

        self.ui.minus_one_y.clicked.connect(partial(self.send_gcode_once, "Y", -1))
        self.ui.minus_ten_y.clicked.connect(partial(self.send_gcode_once, "Y", -10))
        self.ui.minus_pointone_y.clicked.connect(
            partial(self.send_gcode_once, "Y", -0.1)
        )
        self.ui.plus_one_y.clicked.connect(partial(self.send_gcode_once, "Y", 1))
        self.ui.plus_ten_y.clicked.connect(partial(self.send_gcode_once, "Y", 10))
        self.ui.plus_pointone_y.clicked.connect(partial(self.send_gcode_once, "Y", 0.1))

        self.ui.minus_one_z.clicked.connect(partial(self.send_gcode_once, "Z", -1))
        self.ui.minus_ten_z.clicked.connect(partial(self.send_gcode_once, "Z", -10))
        self.ui.minus_pointone_z.clicked.connect(
            partial(self.send_gcode_once, "Z", -0.1)
        )
        self.ui.plus_one_z.clicked.connect(partial(self.send_gcode_once, "Z", 1))
        self.ui.plus_ten_z.clicked.connect(partial(self.send_gcode_once, "Z", 10))
        self.ui.plus_pointone_z.clicked.connect(partial(self.send_gcode_once, "Z", 0.1))

    def send_gcode_once(self, direction, increment):
        """Send a single movement G-code command."""
        speed = getattr(self.ui, f"spinBox_{direction.lower()}speed").value()

        if self.printer is None:
            print("❌ No printer connected. Cannot send G-code.")
            return

        gcode_command = f"G91\nG1 {direction}{increment} F{speed}\nG90"
        send_gcode(self.printer, gcode_command)

    def start_continuous_move(self, direction, increment):
        """Start moving continuously in a given direction."""
        self.current_direction = direction
        self.current_increment = increment
        self.current_speed = getattr(
            self.ui, f"spinBox_{direction.lower()}speed"
        ).value()
        self.moving = True

        if self.movement_thread is None or not self.movement_thread.is_alive():
            self.movement_thread = threading.Thread(target=self.continuous_move)
            self.movement_thread.start()

    def stop_continuous_move(self):
        """Stop continuous movement."""
        self.moving = False

    def continuous_move(self):
        """Continuously move the printer while the button is pressed."""
        while self.moving:
            gcode_command = f"G91\nG1 {self.current_direction}{self.current_increment} F{self.current_speed}\nG90"
            send_gcode(self.printer, gcode_command)
            time.sleep(0.1)

    def perform_continuous_move(self):
        """Perform one step of continuous movement."""
        gcode_command = f"G91\nG1 {self.current_direction}{self.current_increment} F{self.current_speed}\nG90"
        send_gcode(self.printer, gcode_command)

    def home_axis(self, gcode_command):
        """Send a homing command to the printer."""
        if self.printer is None:
            print("❌ No printer connected. Cannot home.")
            return
        send_gcode(self.printer, gcode_command)

    def move_to_wells(self):
        """Move to selected wells."""
        move_to_wells(self.printer, self.wells)


def send_gcode(printer, gcode):
    """Send a G-code command to the printer without reconnecting."""
    if printer is None:
        print("❌ No printer connected.")
        return
    try:
        printer.write(gcode)
        time.sleep(0.001)
    except pyvisa.errors.InvalidSession:
        print("⚠️ Session invalid. Printer must be reconnected manually.")


def move_to_wells(printer, wells):
    """Move the printer to each well and home afterwards."""
    if printer is None:
        print("❌ No printer connected. Cannot move.")
        return

    for well in wells:
        name, coords = well
        x, y = coords
        gcode_command = f"G1 X{x} Y{y}"
        send_gcode(printer, gcode_command)

    send_gcode(printer, "G28 X")
    send_gcode(printer, "G28 Y")


##############################################################Calibration PAGE NOW########################################################
class CalibrationPage(QWidget):
    def __init__(self, ui, printer):
        super().__init__()
        self.ui = ui
        self.printer = printer  # ✅ Get printer reference directly from LOCARS

        # ✅ Initialize Calibration Point
        self.calibration_points = {
            "calibrate_1": None,
        }

        # ✅ Connect Calibration Button
        self.ui.calibrate_1.clicked.connect(lambda: self.calibrate_point("calibrate_1"))

        # ✅ Find Z-axis calibration elements
        self.threshold_input = self.ui.threshold_input
        self.z_calibration_button = self.ui.z_calibration_button
        self.z_calibration_button.clicked.connect(self.calibrate_zaxis)

        # must match the objectName in your .ui
        assert hasattr(self.ui, "calibrate_3"), "UI has no widget named calibrate_3!"
        self.ui.calibrate_3.clicked.connect(self.open_camera_alignment)
        print("✅ Calibrate_3 hooked up.")

        # ✅ Status Labels for Output Messages
        self.calibration_coord = self.ui.calibration_coord

    def calibrate_point(self, point_name):
        """Sets the calibration point (X, Y, Z) = (0, 0, 0) using G92."""
        if self.printer is None:
            print("❌ No printer connection detected. Cannot calibrate.")
            return

        try:
            send_gcode(self.printer, "G90")  # Absolute positioning
            send_gcode(self.printer, "G92 X0 Y0 Z0")  # Set current position as origin
            print(f"✅ Calibration point {point_name} set at (0, 0, 0) using G92.")

            # ✅ Store calibration point
            self.calibration_points[point_name] = (0, 0)

        except pyvisa.errors.InvalidSession:
            print("⚠️ Session invalid. Ensure printer is properly connected.")

    def open_camera_alignment(self):
        print("📸 Opening camera alignment window...")
        self.camera_window = CameraAlignmentWindow()
        self.camera_window.show()

    def calibrate_zaxis(self):
        """Moves the printer to the correct Z height based on chip depth and threshold."""
        if not hasattr(self.ui, "specs") or self.ui.specs is None:
            self.calibration_coord.setText("❌ Select a TOML file first.")
            return

        # ✅ Get depth from TOML file
        depth = self.ui.specs.get("depth", 0)

        try:
            input_threshold = float(self.threshold_input.text())
        except ValueError:
            self.calibration_coord.setText(
                "❌ Invalid input. Please enter a numeric value."
            )
            return

        self.z_height_mm = depth + input_threshold  # Calculate adjusted Z height

        if self.printer is None:
            print("❌ No printer connection detected. Cannot move Z-axis.")
            return

        try:
            send_gcode(self.printer, "G28 Z")  # Home Z-axis
            print("✅ Homed Z-axis successfully.")

            send_gcode(
                self.printer, f"G1 Z{self.z_height_mm} F1000"
            )  # Move to target height
            send_gcode(self.printer, "M114")  # Request position to verify
            self.calibration_coord.setText(f"✅ Moved to Z: {self.z_height_mm} mm")

        except pyvisa.errors.InvalidSession:
            print("⚠️ Session invalid. Ensure printer is properly connected.")


##############################################################Camera PAGE ########################################################
import cv2
import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor


class CameraAlignmentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chip Alignment Camera")

        self.video_label = QLabel()
        self.angle_label = QLabel("Angle: --°")

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.angle_label)
        self.setLayout(layout)

        self.cap = cv2.VideoCapture(2)  # Adjust camera index as needed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # ROI drawing state
        self.drawing_roi = False
        self.roi_start = None
        self.roi_end = None

        # Bind mouse events to label
        self.video_label.mousePressEvent = self.start_roi
        self.video_label.mouseMoveEvent = self.update_roi
        self.video_label.mouseReleaseEvent = self.finish_roi

    def start_roi(self, event):
        self.drawing_roi = True
        self.roi_start = event.pos()
        self.roi_end = event.pos()

    def update_roi(self, event):
        if self.drawing_roi:
            self.roi_end = event.pos()

    def finish_roi(self, event):
        self.drawing_roi = False
        self.roi_end = event.pos()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        draw_rect = False
        if self.roi_start and self.roi_end:
            x1, y1 = min(self.roi_start.x(), self.roi_end.x()), min(
                self.roi_start.y(), self.roi_end.y()
            )
            x2, y2 = max(self.roi_start.x(), self.roi_end.x()), max(
                self.roi_start.y(), self.roi_end.y()
            )
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))

            if x2 > x1 and y2 > y1:
                roi = frame[y1:y2, x1:x2].copy()
                angle, annotated_roi = self.detect_angle(roi)
                frame[y1:y2, x1:x2] = annotated_roi
                draw_rect = True
            else:
                angle = 0
        else:
            angle, frame = self.detect_angle(frame)

        # Overlay rectangle on frame
        if draw_rect:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)

        self.angle_label.setText(f"Angle: {angle:.2f}°")

        # Convert to QImage and display
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def detect_angle(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 30, 100)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best_rect = None
        max_match_score = -1

        for cnt in contours:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = box.astype(np.int32)

            # Heuristic: how rectangular is this shape?
            aspect_ratio = max(rect[1]) / min(rect[1]) if min(rect[1]) > 0 else 0
            area = cv2.contourArea(cnt)

            if area > 0 and 1.0 < aspect_ratio < 10.0:
                score = area  # You can make this smarter later
                if score > max_match_score:
                    max_match_score = score
                    best_rect = rect

        angle = 0
        if best_rect:
            box = cv2.boxPoints(best_rect).astype(np.int32)
            cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
            angle = best_rect[2]
            if angle < -45:
                angle += 90
        else:
            # Fallback: Use full ROI if no contour was good
            h, w = frame.shape[:2]
            box = np.array([[0, 0], [w, 0], [w, h], [0, h]])
            cv2.drawContours(frame, [box], 0, (0, 0, 255), 2)

        return angle, frame

    def closeEvent(self, event):
        self.cap.release()
        self.timer.stop()
        event.accept()


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
##############################################################Timer PAGE NOW########################################################
import threading
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit


class TimerPage(QWidget):
    def __init__(self, ui, acquisition_page, printer):
        super().__init__()
        self.ui = ui  # Access main UI elements
        self.acquisition_page = (
            acquisition_page  # ✅ Store reference to acquisition page
        )
        self.initialize_ui()
        self.initialize_timers()
        self.printer = printer

        # ✅ Use correct reference to acquisition function
        self.acquisition_function = self.acquisition_page.move_to_wells_and_home

        # Pause flag
        self.paused = False

    def initialize_ui(self):
        """Find and connect UI elements to functions safely."""
        # Labels
        self.well_number = self.ui.well_number  # ✅ Updated reference
        self.totaltimer_label = self.ui.totaltimer
        self.intervaltimer_label = self.ui.intervaltimer

        # Line edits
        self.totaltime_lineEdit = self.ui.totaltime_lineEdit
        self.time_interval_lineEdit = self.ui.time_interval_lineEdit

        # Buttons
        self.start_button = self.ui.start_button
        self.pause_button = self.ui.pause_button
        self.stop_button = self.ui.stop_button

        # ✅ Corrected reference for acquisition function
        self.start_button.clicked.connect(self.start_experiment)
        self.pause_button.clicked.connect(self.pause_experiment)
        self.stop_button.clicked.connect(self.stop_experiment)

    def initialize_timers(self):
        """Create and connect timers."""
        self.total_timer = QTimer(self)
        self.interval_timer = QTimer(self)
        self.update_timer = QTimer(self)

        # Connect timers to corresponding functions
        self.total_timer.timeout.connect(
            self.stop_experiment
        )  # Stops everything when total time runs out
        self.update_timer.timeout.connect(self.update_countdowns)

        self.total_time_remaining = 0
        self.interval_time_remaining = 0
        self.interval_time_ms = 0  # Interval time in milliseconds

    def start_experiment(self):
        """Start the total and interval timers."""
        try:
            # Get total time in hours and convert to milliseconds
            total_time_hours = float(self.totaltime_lineEdit.text())
            total_time_ms = int(total_time_hours * 60 * 60 * 1000)  # Convert to integer
            self.total_time_remaining = total_time_ms // 1000  # Convert to seconds

            # Get interval time in minutes and convert to milliseconds
            interval_time_minutes = float(self.time_interval_lineEdit.text())
            self.interval_time_ms = int(
                interval_time_minutes * 60 * 1000
            )  # Convert to integer
            self.interval_time_remaining = (
                self.interval_time_ms // 1000
            )  # Convert to seconds

            # Start the total timer
            self.total_timer.start(total_time_ms)

            # Start the interval timer and update UI
            self.update_countdowns()
            self.interval_timer.timeout.connect(self.handle_interval_timeout)
            self.interval_timer.start(self.interval_time_ms)

            # Start the update timer to refresh countdown every second
            self.update_timer.start(1000)

        except ValueError:
            pass  # Ignore if inputs are invalid

    def pause_experiment(self):
        """Pause or resume the timers."""
        self.paused = not self.paused
        if self.paused:
            self.total_timer.stop()
            self.interval_timer.stop()
            self.update_timer.stop()
            self.pause_button.setText("Resume")
        else:
            self.total_timer.start(self.total_time_remaining * 1000)
            self.interval_timer.start(self.interval_time_remaining * 1000)
            self.update_timer.start(1000)
            self.pause_button.setText("Pause")

    def stop_experiment(self):
        """Stop all timers and reset labels on both Timer and Acquisition pages."""
        # Stop all timers
        self.total_timer.stop()
        self.interval_timer.stop()
        self.update_timer.stop()

        # Clear the timer displays on Timer Page
        self.totaltimer_label.setText("")
        self.intervaltimer_label.setText("")

        # Clear the timer displays on Acquisition Page (if they exist)
        if hasattr(self.ui, "totaltimer2"):
            self.ui.totaltimer2.setText("")
        if hasattr(self.ui, "intervaltimer2"):
            self.ui.intervaltimer2.setText("")

        # Reset pause state and button text
        self.paused = False
        self.pause_button.setText("Pause")

    def update_countdowns(self):
        """Update the countdown labels for total and interval timers in both Timer and Acquisition pages."""
        if self.total_time_remaining > 0:
            self.total_time_remaining -= 1

            # Update interval timer countdown
            if self.interval_time_remaining > 0:
                self.interval_time_remaining -= 1
            else:
                self.handle_interval_timeout()  # Trigger acquisition when interval ends

            # Format total time
            hours, remainder = divmod(self.total_time_remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_total_time = f"{hours:02}:{minutes:02}:{seconds:02}"

            # Format interval time
            minutes, seconds = divmod(self.interval_time_remaining, 60)
            formatted_interval_time = f"{minutes:02}:{seconds:02}"

            # Update labels on Timer Page
            self.totaltimer_label.setText(formatted_total_time)
            self.intervaltimer_label.setText(formatted_interval_time)

            # Update labels on Acquisition Page (if they exist)
            if hasattr(self.ui, "totaltimer2"):
                self.ui.totaltimer2.setText(formatted_total_time)
            if hasattr(self.ui, "intervaltimer2"):
                self.ui.intervaltimer2.setText(formatted_interval_time)

    def handle_interval_timeout(self):
        """Execute the acquisition function when the interval time ends."""
        if not self.paused:
            threading.Thread(target=self.acquisition_function).start()

            # Reset interval countdown after execution
            self.interval_time_remaining = self.interval_time_ms // 1000
            self.interval_timer.start(
                self.interval_time_ms
            )  # Restart the interval timer


##############################################################Acquisition PAGE NOW########################################################
import oras.backend.external_trigger as ext


import threading
from PyQt5.QtWidgets import QWidget, QPushButton, QGridLayout, QCheckBox
from PyQt5.QtCore import QMutex
import pyvisa

# Mutex to prevent simultaneous printer commands
printer_lock = QMutex()


class AcquisitionPage(QWidget):
    def __init__(self, ui, chip_page, calibration_page, printer):
        super().__init__()
        self.ui = ui
        self.chip_page = chip_page
        self.calibration_page = calibration_page
        self.checkboxes = []  # Store checkbox references
        self.printer = printer  # ✅ Use global printer reference

        # ✅ Connect button to function
        self.gotowells_button = self.ui.GOTOWELLS
        self.gotowells_button.clicked.connect(self.move_to_wells_and_home)

        # ✅ Ensure that grid_generated_followup exists before using it
        if hasattr(self.ui, "grid_generated_followup"):
            self.grid_layout_followup = self.ui.grid_generated_followup
        else:
            print("⚠️ Warning: grid_generated_followup not found in UI.")
            self.grid_layout_followup = QGridLayout()  # Fallback

        self.clear_followup_grid()

        # ✅ FIXED: Connect the button properly
        self.chip_page.ui.save_toggledwells.clicked.connect(
            lambda: self.update_followup_grid(
                self.chip_page.well_coordinates, self.chip_page.save_active_wells()
            )
        )

    def clear_followup_grid(self):
        """Removes all widgets from grid_generated_followup."""
        for i in reversed(range(self.grid_layout_followup.count())):
            widget = self.grid_layout_followup.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def update_followup_grid(self, all_wells, active_wells):
        try:
            if not all_wells:
                print("⚠️ No wells available.")
                return

            if not isinstance(active_wells, list):
                print("❌ active_wells is not a list. Check save function.")
                return

            print(f"🔍 Updating followup grid with {len(active_wells)} active wells.")

            self.clear_followup_grid()
            self.checkboxes = []  # Reset stored checkboxes

            rows = self.chip_page.rows
            cols = self.chip_page.cols

            checked_wells = {
                cb.text() for cb in self.chip_page.checkboxes if cb.isChecked()
            }

            for row in range(rows):
                for col in range(cols):
                    well_label = f"({row+1}, {chr(65+col)})"
                    if well_label in all_wells:
                        checkbox = QCheckBox(well_label)
                        checkbox.setChecked(False)
                        if well_label not in checked_wells:
                            checkbox.setEnabled(False)

                        self.grid_layout_followup.addWidget(checkbox, row, col)
                        self.checkboxes.append(checkbox)

            print(f"✅ Generated followup grid with {rows} rows and {cols} columns.")

        except Exception as e:
            print(f"❌ error in update_followup_grid: {e}")

    def move_to_wells_and_home(self):
        """Moves the printer to each selected well in sequence and starts acquisition."""

        # ✅ Lock printer commands to prevent concurrent execution
        printer_lock.lock()

        try:
            # ✅ Ensure the printer is connected
            if self.printer is None:
                print("❌ No printer connected.")
                return

            # ✅ Retrieve calibration point
            calibration_points = self.calibration_page.calibration_points
            if (
                "calibrate_1" not in calibration_points
                or calibration_points["calibrate_1"] is None
            ):
                print("❌ Calibration point 'calibrate_1' is not set.")
                return

            origin_x, origin_y = calibration_points["calibrate_1"]

            # ✅ Retrieve selected (active) wells instead of all wells
            active_wells = self.chip_page.save_active_wells()
            if not active_wells:
                print("❌ No active wells selected.")
                return

            print(f"✅ Total active wells to visit: {len(active_wells)}")

            send_gcode(self.printer, "G91")  # Relative mode
            send_gcode(self.printer, "G1 Z10 F250")  # Raise Z
            send_gcode(self.printer, "G90")  # Back to absolute mode

            # ✅ Move to each active well and perform acquisition
            for index, (name, (x, y)) in enumerate(active_wells):
                target_x = origin_x + y  # Apply calibration correction
                target_y = origin_y + x
                gcode_command_xy = f"G1 X{target_x} Y{target_y} F2000"

                print(
                    f"🔵 Moving to well {index+1}/{len(active_wells)}: {name} at ({target_x}, {target_y})"
                )

                try:

                    send_gcode(self.printer, gcode_command_xy)

                    send_gcode(self.printer, "G91")
                    send_gcode(self.printer, "G1 Z-10 F250")
                    send_gcode(self.printer, "G90")
                    time.sleep(3)

                    # ext.set_file_name(f"Puit{name}")
                    ext.set_comment(f"Acquisition au puit {name}")
                    time.sleep(3)
                    ext.start_acquisition(blocking=True)

                    send_gcode(self.printer, "G91")
                    send_gcode(self.printer, "G1 Z10 F250")
                    send_gcode(self.printer, "G90")

                    # ✅ Check only the corresponding checkbox for this well
                    for checkbox in self.checkboxes:
                        if checkbox.text() == name:
                            checkbox.setChecked(True)
                            break

                    time.sleep(1)

                except pyvisa.errors.InvalidSession:
                    print(
                        "❌ Session invalid during well movement. Skipping this well."
                    )
                    continue  # Skip to next well safely

            # ✅ Return to calibration point at the end
            send_gcode(self.printer, f"G1 X{origin_x} Y{origin_y} F2000")
            print(f"🔵 Returning to calibration point at ({origin_x}, {origin_y})")
            send_gcode(self.printer, "G91")
            send_gcode(self.printer, "G1 Z-10 F250")
            send_gcode(self.printer, "G90")

        finally:
            printer_lock.unlock()  # ✅ Always release the lock


##############################################################Settings PAGE NOW########################################################
class SettingsPage(QWidget):
    def __init__(self, ui, chip_page, printer_page, printer):
        super().__init__()
        self.ui = ui  # Access the main UI
        self.chip_page = chip_page  # Reference to ChipPage
        self.printer_page = printer_page  # Reference to PrinterControlPage
        self.printer = printer  # ✅ Use global printer reference

        # Store the laser control window instance to prevent multiple windows
        self.laser_control_window = None

        # Connect IPS_laser button to open the laser control window
        self.ui.IPS_laser.clicked.connect(self.open_laser_control)
        self.ui.send_gcode_button.clicked.connect(self.send_manual_gcode)

        # Debugging print statement to confirm the button is connected
        print("✅ send_gcode_button connected to send_manual_gcode.")

    def open_laser_control(self):
        """Opens the IPS Laser control window."""
        if (
            self.laser_control_window is None
            or not self.laser_control_window.isVisible()
        ):
            self.laser_control_window = IpsLaserwidget()  # Create instance
            self.laser_control_window.show()  # Show the window

    def send_manual_gcode(self):
        """Sends manual G-code from the input field to the printer."""
        gcode_command = self.ui.manual_input.text().strip()

        if self.printer is None:
            print("❌ No printer connected. Cannot send G-code.")
            return  # Stop execution

        # Ensure G-code is valid
        if not gcode_command or not gcode_command[0].isalpha():
            print("❌ Invalid G-code command entered.")
            return  # Stop execution if the command is invalid

        # ✅ Send the G-code properly
        send_gcode(self.printer, gcode_command)
        print(f"✅ Sent G-code command: {gcode_command}")

        # ✅ Clear input after sending
        self.ui.manual_input.clear()


##############################################################LOCARS PAGE NOW########################################################
import sys
import os
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtGui import QFont, QColor, QPalette
import pyvisa
from PyQt5.QtWidgets import QWidget, QGridLayout, QCheckBox
from PyQt5.QtCore import QTimer  # ✅ Move QTimer here!

lumed_ips_path = r"/media/lumed/KINGSTON/GUI/New_LOCARS/src/LOCARS/lumed_ips/src"

if lumed_ips_path not in sys.path:
    sys.path.append(lumed_ips_path)

from ipscontrol.laser_widget import IpsLaserwidget


class LOCARS(QMainWindow):
    def __init__(self):
        super(LOCARS, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.icon_only_widget.hide()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.Chip_button.setChecked(True)

        self.setWindowTitle("LOCARS")

        # ✅ Connect to printer once and share across pages
        self.printer = self.connect_to_printer()
        self.log_window = LogWindow()
        self.log_window.show()

        try:
            sys.stdout = self.log_window
            sys.stderr = self.log_window
            print("✅ Logging started.")
        except Exception as e:
            print(f"❌ Failed to redirect stdout: {e}")
        # Set font: Arial, 16, Bold
        font = QFont("Arial", 16, QFont.Bold)
        self.ui.label_actual_section.setFont(font)

        # Set color: Dark Grey
        palette = self.ui.label_actual_section.palette()
        palette.setColor(QPalette.WindowText, QColor(95, 98, 99))  # DarkGrey
        self.ui.label_actual_section.setPalette(palette)
        self.ui.label_actual_section.setText("Chip Model Selection and Well Generation")

        # ✅ Instantiate Pages in correct order
        self.chip_page = ChipPage(self.ui, self.printer)
        self.calibration_page = CalibrationPage(self.ui, self.printer)
        self.acquisition_page = AcquisitionPage(
            self.ui, self.chip_page, self.calibration_page, self.printer
        )
        self.ui.acquisition_page = self.acquisition_page  # ✅ Store reference in UI

        self.printer_control_page = PrinterControlPage(
            self.ui, self.chip_page, self.printer
        )
        self.timer_page = TimerPage(self.ui, self.acquisition_page, self.printer)
        self.settings_page = SettingsPage(
            self.ui, self.chip_page, self.printer_control_page, self.printer
        )

        # ✅ Add Pages to stackedWidget
        self.ui.stackedWidget.addWidget(self.chip_page)
        self.ui.stackedWidget.addWidget(self.printer_control_page)
        self.ui.stackedWidget.addWidget(self.calibration_page)
        self.ui.stackedWidget.addWidget(self.timer_page)
        self.ui.stackedWidget.addWidget(self.acquisition_page)
        self.ui.stackedWidget.addWidget(self.settings_page)
        # Page Titles for QLabel
        self.page_titles = [
            "Chip Model Selection and Well Generation",
            "Printer Controls",
            "Calibration of the System",
            "Timer Initialization",
            "Acquisition and Measurements",
            "Settings",
        ]

        # Connect buttons to page change function
        self.ui.Chip_button.toggled.connect(
            lambda checked: self.change_page(0, checked)
        )
        self.ui.printer_button.toggled.connect(
            lambda checked: self.change_page(1, checked)
        )
        self.ui.calibration_button.toggled.connect(
            lambda checked: self.change_page(2, checked)
        )
        self.ui.timer_button.toggled.connect(
            lambda checked: self.change_page(3, checked)
        )
        self.ui.acquisition_button.toggled.connect(
            lambda checked: self.change_page(4, checked)
        )
        self.ui.settings_button.toggled.connect(
            lambda checked: self.change_page(5, checked)
        )

    def detect_available_ports(self):
        """Lists all available VISA serial ports."""
        rm = pyvisa.ResourceManager()
        ports = rm.list_resources()
        return [port for port in ports if "ASRL" in port] if ports else None

    def connect_to_printer(self):
        """Tries to connect to the 3D printer by testing all available VISA serial ports."""
        available_ports = self.detect_available_ports()
        if not available_ports:
            print("❌ No available VISA serial ports found.")
            return None

        rm = pyvisa.ResourceManager()
        for port in available_ports:
            try:
                print(f"🔍 Trying port: {port}...")
                printer = rm.open_resource(port)
                printer.baud_rate = 115200
                printer.timeout = 2000  # Timeout in milliseconds
                printer.write_termination = "\n"
                printer.read_termination = "\n"
                time.sleep(2)

                printer.write("M115")
                response = printer.read()

                if "FIRMWARE" in response or "Marlin" in response or response:
                    print(f"✅ Connected to printer on {port}")
                    return printer

                printer.close()
            except pyvisa.VisaIOError as e:
                print(f"❌ Could not connect to {port}: {e}")

        print("⚠️ No valid printer connection found.")
        return None

    def change_page(self, index, checked):
        """Function for changing menu pages and updating QLabel."""
        if checked:
            self.ui.stackedWidget.setCurrentIndex(index)
            self.ui.label_actual_section.setText(self.page_titles[index])

            # Set font: Arial, 16, Bold
            font = QFont("Arial", 16, QFont.Bold)
            self.ui.label_actual_section.setFont(font)

            # Set color: Dark Grey
            palette = self.ui.label_actual_section.palette()
            palette.setColor(QPalette.WindowText, QColor(95, 98, 99))  # DarkGrey
            self.ui.label_actual_section.setPalette(palette)

    def closeEvent(self, event):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    with open(
        r"/media/lumed/KINGSTON/GUI/New_LOCARS/src/LOCARS/style.qss", "r"
    ) as style_file:
        style_str = style_file.read()

    app.setStyleSheet(style_str)
    window = LOCARS()
    window.show()
    sys.exit(app.exec_())


# RUN COMMAND

# export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms
# QT_DEBUG_PLUGINS=1 /bin/python3 /home/lumed/Desktop/Tommy/New_LOCARS/src/LOCARS/LOCARS.py
