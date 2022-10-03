import PyQt5
import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import pyThorlabsPM100x
    
app = Qt.QApplication([])
window = Qt.QWidget()

 #Create the interface object
Interface = pyThorlabsPM100x.interface(app=app,mainwindow=window)
Interface.verbose = False #set the verbosity of the interface logger to False

#The GUI needs to be contained inside a widget object
widget_containing_interface_GUI = Qt.QWidget()
widget_containing_interface_GUI.setStyleSheet(".QWidget {\n" \
            + "border: 1px solid black;\n" \
            + "border-radius: 4px;\n" \
            + "}") #This line changes the style of ONLY this QWdiget
    

gui = pyThorlabsPM100x.gui(interface = Interface, parent=widget_containing_interface_GUI,plot=False)
gridlayoutwidget = Qt.QWidget()
gridlayout = Qt.QGridLayout()
gridlayout.addWidget(Qt.QLabel("Additional GUI 1"), 0, 0)
gridlayout.addWidget(Qt.QLabel("Additional GUI 2"), 1, 0)
gridlayout.addWidget(Qt.QLabel("Additional GUI 3"), 0, 1)
gridlayout.addWidget(Qt.QLabel("Additional GUI 4"), 1, 1)
gridlayoutwidget.setLayout(gridlayout)

layout = Qt.QHBoxLayout()
layout.addWidget(widget_containing_interface_GUI)
layout.addWidget(gridlayoutwidget)
window.setLayout(layout)


window.show()
app.exec()# Start the event loop.