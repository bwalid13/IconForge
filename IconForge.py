# -*- coding: utf-8 -*-

"""
IconForge: An advanced image to .ico converter.

This script uses PyQt6 for the graphical user interface and Pillow for image manipulation.
Features:
- Load multiple images (PNG, JPG, etc.).
- Preview the icon with a real-time adjustable corner radius.
- Select which sizes to include in the final .ico file.
- Choose the bit depth (32-bit with transparency or 8-bit palettized).
- Convert and save images to the .ico format.

Dependencies to install:
pip install PyQt6 Pillow
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QLabel, QSlider, QCheckBox, QRadioButton,
    QGroupBox, QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QPainter, QColor, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QUrl, QPointF, QTimer
from PIL import Image, ImageQt

# --- Constants ---
MAX_FILE_SIZE_MB = 4
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
# Added TGA to the list of supported formats
SUPPORTED_IMAGE_FORMATS = "Supported Images (*.png *.jpg *.jpeg *.bmp *.gif *.tga)"
ICON_SIZES = [16, 32, 48, 64, 128, 256]

class IconForgeApp(QWidget):
    """
    Main class for the IconForge application.
    """
    def __init__(self):
        super().__init__()
        self.current_image_path = None
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface."""
        self.setWindowTitle("IconForge - Icon Converter")
        self.setGeometry(100, 100, 800, 550)
        self.setAcceptDrops(True) # Enable drag-and-drop

        # --- Set Custom App Icon from file, with a fallback ---
        icon_path = "app_icon.png"
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
        else:
            # Fallback: create a default icon if the file is missing
            print("Warning: 'app_icon.png' not found. Using default icon.")
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw a nice background
            gradient = QLinearGradient(0, 0, 0, 64)
            gradient.setColorAt(0.0, QColor("#4a90e2"))
            gradient.setColorAt(1.0, QColor("#007ACC"))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(pixmap.rect(), 10, 10)

            # Draw a simplified "image" symbol inside
            painter.setPen(QColor(255, 255, 255, 200))
            painter.setBrush(QColor(255, 255, 255, 70))
            # Draw a mountain shape
            points = [QPointF(15, 50), QPointF(28, 35), QPointF(38, 45), QPointF(50, 25), QPointF(50, 50)]
            painter.drawPolygon(points)
            # Draw a sun
            painter.setBrush(QColor("#ffeb3b"))
            painter.drawEllipse(QPointF(42, 22), 5, 5)
            
            painter.end()
            app_icon = QIcon(pixmap)
        
        self.setWindowIcon(app_icon)


        # --- Main Layouts ---
        main_layout = QHBoxLayout(self)
        left_panel = QVBoxLayout()
        center_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        # --- Left Panel: File List ---
        file_group = QGroupBox("Files to Convert")
        file_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.setToolTip("Drag and drop images here or use the buttons.")
        self.file_list.currentItemChanged.connect(self.update_preview)

        add_button = QPushButton("Add Images...")
        add_button.clicked.connect(self.add_images)
        
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_selected_image)

        clear_button = QPushButton("Clear List")
        clear_button.clicked.connect(self.clear_list)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)

        file_layout.addLayout(button_layout)
        file_layout.addWidget(self.file_list)
        file_layout.addWidget(clear_button)
        file_group.setLayout(file_layout)
        left_panel.addWidget(file_group)

        # --- Center Panel: Preview ---
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_label = QLabel("Select an image to preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(256, 256)
        self.preview_label.setFrameShape(QFrame.Shape.StyledPanel)
        self.preview_label.setStyleSheet("border: 2px dashed #aaa; border-radius: 15px;")
        
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        center_panel.addWidget(preview_group)

        # --- Right Panel: Options ---
        options_group = QGroupBox("Conversion Options")
        options_layout = QVBoxLayout()

        # Corner Radius
        radius_group = QGroupBox("Corner Radius")
        radius_layout = QHBoxLayout()
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 512) # Increased range
        self.radius_slider.setToolTip("Adjust the radius of the rounded corners.")
        self.radius_slider.valueChanged.connect(self.update_preview)
        self.radius_value_label = QLabel("0")
        self.radius_value_label.setFixedWidth(30)
        radius_layout.addWidget(self.radius_slider)
        radius_layout.addWidget(self.radius_value_label)
        radius_group.setLayout(radius_layout)
        
        # Sizes
        sizes_group = QGroupBox("Sizes to include (.ico)")
        sizes_layout = QVBoxLayout()
        self.size_checkboxes = {}
        for size in ICON_SIZES:
            self.size_checkboxes[size] = QCheckBox(f"{size} x {size}")
            self.size_checkboxes[size].setChecked(True)
            sizes_layout.addWidget(self.size_checkboxes[size])
        sizes_group.setLayout(sizes_layout)

        # Bit Depth
        bit_depth_group = QGroupBox("Bit Depth")
        bit_depth_layout = QVBoxLayout()
        self.bit_32 = QRadioButton("32-bit (Max quality, transparency)")
        self.bit_32.setChecked(True)
        self.bit_8 = QRadioButton("8-bit (256 colors, compatibility)")
        bit_depth_layout.addWidget(self.bit_32)
        bit_depth_layout.addWidget(self.bit_8)
        bit_depth_group.setLayout(bit_depth_layout)
        
        # Save Option
        self.save_separately_checkbox = QCheckBox("Save each size as a separate file")
        self.save_separately_checkbox.setToolTip("If checked, creates files like 'img_16.ico', 'img_32.ico', etc.")

        options_layout.addWidget(radius_group)
        options_layout.addWidget(sizes_group)
        options_layout.addWidget(bit_depth_group)
        options_layout.addWidget(self.save_separately_checkbox) # Added checkbox
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        right_panel.addWidget(options_group)

        # --- Bottom Panel: Actions ---
        bottom_panel = QVBoxLayout()
        self.convert_button = QPushButton("Convert and Save")
        self.convert_button.setFixedHeight(40)
        self.convert_button.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.convert_button.clicked.connect(self.run_conversion)
        
        progress_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setFixedWidth(200)
        self.progress_bar = QProgressBar()
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)

        bottom_panel.addWidget(self.convert_button)
        bottom_panel.addLayout(progress_layout)

        # --- Final Assembly ---
        main_layout.addLayout(left_panel, 35)
        main_layout.addLayout(center_panel, 30)
        main_layout.addLayout(right_panel, 35)
        
        container_widget = QWidget()
        container_widget.setLayout(main_layout)

        final_layout = QVBoxLayout(self)
        final_layout.addWidget(container_widget)
        final_layout.addLayout(bottom_panel)

        self.apply_stylesheet()

    def apply_stylesheet(self):
        """Applies a stylesheet for a modern look."""
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: Segoe UI, sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
            }
            QPushButton {
                background-color: #555;
                border: 1px solid #666;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #6A6A6A;
            }
            QPushButton:pressed {
                background-color: #4A4A4A;
            }
            #convert_button { /* Specific style for the main button */
                background-color: #007ACC;
                color: white;
            }
            #convert_button:hover {
                background-color: #0089E0;
            }
            QListWidget {
                background-color: #3C3C3C;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #3C3C3C;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007ACC;
                border: 1px solid #007ACC;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #007ACC;
                border-radius: 5px;
            }
        """)
        self.convert_button.setObjectName("convert_button")

    def reset_status(self):
        """Resets the progress bar and status label to their initial state."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")

    # --- Drag-and-Drop Functions ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.add_files_to_list(files)
        
    # --- Application Logic ---
    def add_images(self):
        """Opens a dialog to select image files."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "", SUPPORTED_IMAGE_FORMATS
        )
        if files:
            self.add_files_to_list(files)

    def add_files_to_list(self, file_paths):
        """Validates and adds a list of files to the QListWidget."""
        for path in file_paths:
            if os.path.getsize(path) > MAX_FILE_SIZE_BYTES:
                print(f"File ignored (too large > {MAX_FILE_SIZE_MB}MB): {os.path.basename(path)}")
                continue
            if path not in [self.file_list.item(i).text() for i in range(self.file_list.count())]:
                 self.file_list.addItem(path)
        
        if self.file_list.count() > 0 and self.file_list.currentItem() is None:
            self.file_list.setCurrentRow(0)

    def remove_selected_image(self):
        """Removes the selected item from the list."""
        selected_items = self.file_list.selectedItems()
        if not selected_items: return
        for item in selected_items:
            self.file_list.takeItem(self.file_list.row(item))
        self.update_preview()
        
    def clear_list(self):
        """Clears the file list completely."""
        self.file_list.clear()
        self.preview_label.clear()
        self.preview_label.setText("Select an image...")
        self.current_image_path = None

    def update_preview(self):
        """Updates the preview with the current image and options."""
        current_item = self.file_list.currentItem()
        if not current_item:
            self.preview_label.clear()
            self.preview_label.setText("No image selected")
            self.current_image_path = None
            return

        self.current_image_path = current_item.text()
        radius = self.radius_slider.value()
        self.radius_value_label.setText(str(radius))

        try:
            with Image.open(self.current_image_path) as pil_img:
                pil_img = pil_img.convert("RGBA")
                
                if radius > 0:
                    pil_img = self.apply_rounded_corners_pil(pil_img, radius)

                q_image = ImageQt.ImageQt(pil_img)
                pixmap = QPixmap.fromImage(q_image)
                
                self.preview_label.setPixmap(
                    pixmap.scaled(
                        256, 256,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        except Exception as e:
            print(f"Preview Error: {e}")
            self.preview_label.setText("Format Error")
            
    @staticmethod
    def apply_rounded_corners_pil(image: Image.Image, radius: int) -> Image.Image:
        """Applies rounded corners to a Pillow image."""
        mask = Image.new('L', image.size, 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        
        safe_radius = min(radius, image.width // 2, image.height // 2)

        draw.rounded_rectangle((0, 0) + image.size, radius=safe_radius, fill=255)

        output = image.copy()
        output.putalpha(mask)
        return output

    def run_conversion(self):
        """Runs the conversion process for all files in the list."""
        if self.file_list.count() == 0:
            self.show_message("No Files", "Please add at least one image.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Choose Save Directory")
        if not output_dir:
            return
        
        radius = self.radius_slider.value()
        selected_sizes = [size for size, checkbox in self.size_checkboxes.items() if checkbox.isChecked()]
        use_32bit = self.bit_32.isChecked()
        save_separately = self.save_separately_checkbox.isChecked()

        if 256 in selected_sizes and not use_32bit:
            self.show_message("Warning", "The 256x256 size is only compatible with 32-bit mode. It will be ignored.", "warning")
            selected_sizes.remove(256)

        if not selected_sizes:
            self.show_message("No Sizes Selected", "Please select at least one icon size.", "warning")
            return

        # Setup progress bar and status
        self.status_label.setText("Converting...")
        QApplication.processEvents() # Force UI update
        
        if save_separately:
            total_conversions = self.file_list.count() * len(selected_sizes)
            self.progress_bar.setMaximum(total_conversions)
        else:
            self.progress_bar.setMaximum(self.file_list.count())
        
        self.progress_bar.setValue(0)
        conversion_count = 0
        
        for i in range(self.file_list.count()):
            path = self.file_list.item(i).text()
            base_name = os.path.splitext(os.path.basename(path))[0]
            
            try:
                with Image.open(path) as img:
                    img_rgba = img.convert("RGBA")
                    
                    if radius > 0:
                        img_rgba = self.apply_rounded_corners_pil(img_rgba, radius)
                    
                    if save_separately:
                        for size in selected_sizes:
                            output_path = os.path.join(output_dir, f"{base_name}_{size}.ico")
                            sizes_for_pil = [(size, size)]
                            img_rgba.save(
                                output_path, format='ICO', sizes=sizes_for_pil,
                                bitmap_format='bmp' if not use_32bit else 'png'
                            )
                            conversion_count += 1
                            self.progress_bar.setValue(conversion_count)
                    else:
                        output_path = os.path.join(output_dir, f"{base_name}.ico")
                        sizes_for_pil = [(s, s) for s in selected_sizes]
                        img_rgba.save(
                            output_path, format='ICO', sizes=sizes_for_pil,
                            bitmap_format='bmp' if not use_32bit else 'png'
                        )
                        conversion_count += 1
                        self.progress_bar.setValue(conversion_count)

            except Exception as e:
                self.status_label.setText("Error!")
                print(f"Error converting {path}: {e}")
                self.show_message("Conversion Error", f"Could not convert {os.path.basename(path)}.\n\n{e}", "critical")
                QTimer.singleShot(4000, self.reset_status)
                return # Stop the process on error
        
        self.status_label.setText(f"Success! {conversion_count} file(s) created.")
        QTimer.singleShot(4000, self.reset_status)


    def show_message(self, title, message, icon_type="information"):
        """Displays a message box to the user."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if icon_type == "warning":
            msg_box.setIcon(QMessageBox.Icon.Warning)
        elif icon_type == "critical":
            msg_box.setIcon(QMessageBox.Icon.Critical)
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = IconForgeApp()
    ex.show()
    sys.exit(app.exec())

