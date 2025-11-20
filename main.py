import sys, os
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPixmap, QPolygon
import PySide6.QtGui as QtGui
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QToolBar, QFileDialog
import cv2
import numpy as np


class EditorWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        # Keep the aspect ratio when resizing

        self.setAcceptDrops(True)

        self.points_rel = [
            QPointF(0.25, 0.25),
            QPointF(0.75, 0.25),
            QPointF(0.75, 0.75),
            QPointF(0.25, 0.75),
        ]

        self.template = QPixmap()
        self.template_og = None
        self.inside = QPixmap()
        self.inside_og = None
        self.ratio = 1.0  # width / height

        self.mouse_in_polygon = False

        self.radius = 10
        self.drag_index = None

        self.layer_switch = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw inside shape
        if not self.inside.isNull() and self.layer_switch:
            painter.drawPixmap(0, 0, self.inside)

        # Draw template
        if not self.template.isNull():
            scaled_pixmap = self.template.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)

        # Draw inside shape
        if not self.inside.isNull() and not self.layer_switch:
            painter.drawPixmap(0, 0, self.inside)

        # Draw lines
        pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(pen)

        # painter.drawLine(self.points[-1], self.points[0])
        painter.drawPolygon(self.points())

        # Draw points
        painter.setBrush(QBrush(QColor(255, 80, 80)))
        for p in self.points():
            painter.drawEllipse(p, self.radius, self.radius)


    def update_inside_shape(self):
        if self.inside_og is not None:
            warped = self.warp_inside()
            self.inside = warped
            self.update()

    def points(self):
        points = [
            QPoint(point.x() * self.width(), point.y() * self.height())
            for point in self.points_rel
        ]
        return points

    def mousePressEvent(self, event):
        pos = event.position().toPoint()

        for i, p in enumerate(self.points()):
            if (pos - p).manhattanLength() <= self.radius:
                self.drag_index = i
                break

    def mouseMoveEvent(self, event):
        if self.drag_index is not None:
            # self.points[self.drag_index] = event.position().toPoint()
            mouse_pos = event.position().toPoint()
            self.points_rel[self.drag_index] = QPointF(
                mouse_pos.x() / self.width(), mouse_pos.y() / self.height()
            )

            self.update_inside_shape()
            self.update()

    def mouseReleaseEvent(self, event):
        self.drag_index = None

    def change_template(self, image_path):
        self.template = QPixmap(image_path)
        self.ratio = self.template.width() / self.template.height()
        self.update()

    def change_inside(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

        if img is None:
            return

        # Ensure RGBA
        if img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        elif img.shape[2] == 4:
            # Ensure BGRA order
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGRA)

        self.inside_og = img

        # Recompute polygon warp
        self.update_inside_shape()
        self.update()

    def resizeEvent(self, event):
        w = event.size().width()
        h = int(w / self.ratio)

        # impose la géométrie sans rappeler resize()
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)

        super().resizeEvent(event)
        self.update_inside_shape()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

        mouse_pos = event.position().toPoint()
        polygon = QPolygon(self.points())
        self.mouse_in_polygon = polygon.containsPoint(mouse_pos, Qt.OddEvenFill)

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                # links.append(str(url.toLocalFile()))
                if self.mouse_in_polygon:
                    self.change_inside(str(url.toLocalFile()))
                else:
                    self.change_template(str(url.toLocalFile()))
            # self.fileDropped.emit(links)
        else:
            event.ignore()

    def flip_layer(self):
        self.layer_switch = not self.layer_switch
        self.update()

    def warp_inside(self, original_size=False):
        src_pts = np.array(
            [
                [0, 0],
                [self.inside_og.shape[1] - 1, 0],
                [self.inside_og.shape[1] - 1, self.inside_og.shape[0] - 1],
                [0, self.inside_og.shape[0] - 1],
            ],
            dtype=np.float32,
        )

        if original_size:
            dst_pts = self.polygon_points_in_template_space()
            w, h = self.template.width(), self.template.height()
        else:
            dst_pts = np.array(
                [[p.x(), p.y()] for p in self.points()], dtype=np.float32
            )
            w, h = self.width(), self.height()

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(self.inside_og, M, (w, h))

        warped = cv2.cvtColor(warped, cv2.COLOR_BGRA2RGBA)
        qimage = QtGui.QImage(
            warped.data, w, h, warped.strides[0], QtGui.QImage.Format_RGBA8888
        )
        return QPixmap.fromImage(qimage)

    def polygon_points_in_template_space(self):
        # template size
        tw, th = self.template.width(), self.template.height()

        # how template is drawn on screen
        scaled = self.template.scaled(self.size(), Qt.KeepAspectRatio)
        sw, sh = scaled.width(), scaled.height()

        # offsets (letterboxing)
        ox = (self.width() - sw) / 2
        oy = (self.height() - sh) / 2

        # scale factors
        sx = tw / sw
        sy = th / sh

        # convert each point
        dst = []
        for p in self.points():
            px = (p.x() - ox) * sx
            py = (p.y() - oy) * sy
            dst.append([px, py])

        return np.array(dst, dtype=np.float32)

    def render_pixmap(self):
        template = self.template

        # Final output at template resolution
        final_image = QPixmap(template.size())
        final_image.fill(Qt.transparent)

        painter = QPainter(final_image)
        painter.setRenderHint(QPainter.Antialiasing)

        # Warp inside directly to template resolution
        wrapped_inside = self.warp_inside(original_size=True)

        if self.layer_switch:
            painter.drawPixmap(0, 0, wrapped_inside)

        painter.drawPixmap(0, 0, template)

        if not self.layer_switch:
            painter.drawPixmap(0, 0, wrapped_inside)

        painter.end()
        return final_image

    def export_image(self):
        final_image = self.render_pixmap()
        dialog = QFileDialog(self,
                             "Save Image",
                            os.getcwd() + "/exported_image.png",
                            "PNG Files (*.png);;All Files (*)",
                            )
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        if dialog.exec() == QFileDialog.Accepted:
            save_path = dialog.selectedFiles()[0]
            if not save_path.lower().endswith('.png'):
                save_path += '.png'
            final_image.save(save_path, "PNG")


    def export_image_to_clipboard(self):
        final_image = self.render_pixmap()
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(final_image)


class ToolbarWidget(QToolBar):
    def __init__(self):
        super().__init__()
        self.flip_layer_action = self.addAction("Flip Layer")
        self.flip_layer_action.setToolTip("Flip between template and inside layer")

        self.export_action = self.addAction("Export")
        self.export_to_clipboard_action = self.addAction("Export to Clipboard")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pointing Meme Generator")
        self.setMinimumSize(600, 600)

        self.editor = EditorWidget()
        self.setCentralWidget(self.editor)
        self.toolbar = ToolbarWidget()
        self.addToolBar(self.toolbar)
        self.toolbar.flip_layer_action.triggered.connect(self.editor.flip_layer)
        self.toolbar.export_action.triggered.connect(self.editor.export_image)
        self.toolbar.export_to_clipboard_action.triggered.connect(
            self.editor.export_image_to_clipboard
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
