import sys, os
from PySide6.QtCore import Qt, QPoint, QPointF, Signal, QSize 
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPixmap, QPolygon
import PySide6.QtGui as QtGui 
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow , QSizePolicy
import cv2
import numpy as np

            
class EditorWidget(QWidget):

    # fileDropped = Signal(list)

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
        self.inside = QPixmap()
        self.inside_og = None
        self.ratio = 1.0  # width / height

        self.mouse_in_polygon = False

        self.radius = 10
        self.drag_index = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw template
        if not self.template.isNull():
            scaled_pixmap = self.template.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
        
        # Draw inside shape
        if not self.inside.isNull():
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

        # Highlight widget border when dragging
        if self.drag_index is not None:
            highlight_pen = QPen(QColor(0, 120, 215), 4)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(2, 2, -2, -2))


    def update_inside_shape(self):
        if self.inside_og is not None:
            

            src_pts = np.array([
                [0, 0],
                [self.inside_og.shape[1] - 1, 0],
                [self.inside_og.shape[1] - 1, self.inside_og.shape[0] - 1],
                [0, self.inside_og.shape[0] - 1],
            ], dtype=np.float32)

            dst_pts = np.array([
                [point.x() * self.width(), point.y() * self.height()] for point in self.points_rel
            ], dtype=np.float32)

            transform = cv2.getPerspectiveTransform(
                src_pts, dst_pts
            )

            warped = cv2.warpPerspective(self.inside_og, transform, (self.width(), self.height()))
            if warped.shape[2] == 4:
                warped = cv2.cvtColor(warped, cv2.COLOR_BGRA2RGBA)
            else:
                warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)


            h, w = warped.shape[:2]
            bytes_per_line = warped.strides[0]
            qimage = QtGui.QImage(warped.data, w, h, bytes_per_line, QtGui.QImage.Format_RGBA8888).rgbSwapped()
            self.inside = QPixmap.fromImage(qimage)
            self.update()

    def points(self):
        points = [QPoint(point.x() * self.width(), point.y() * self.height()) for point in self.points_rel]
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
                mouse_pos.x() / self.width(),
                mouse_pos.y() / self.height()
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
        if img.shape[2] == 3:  # BGR → RGB + alpha 255
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = np.dstack((img, np.full(img.shape[:2], 255, dtype=np.uint8)))
        else:  # BGRA → RGBA
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)

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
            print(f"Drop event (inside polygon: {self.mouse_in_polygon})")
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
    

class ToolbarWidget(QWidget):
    def __init__(self):
        super().__init__()

        

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editable Polygon - PySide6")
        self.setMinimumSize(600, 600)

        self.editor = EditorWidget()
        # self.editor.fileDropped.connect(self.pictureDropped)
        self.setCentralWidget(self.editor)

    # def pictureDropped(self, l):
    #     for url in l:
    #         if os.path.exists(url):
    #             print(url)                
    #             self.editor.change_image(url)
                # icon = QtGui.QIcon(url)
                # pixmap = icon.pixmap(72, 72)                
                # icon = QtGui.QIcon(pixmap)
                # item = QtGui.QListWidgetItem(url, self.view)
                # item.setIcon(icon)        
                # item.setStatusTip(url)  


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
