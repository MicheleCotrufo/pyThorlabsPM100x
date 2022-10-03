import PyQt5
import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import pyThorlabsPM100x
    
app = Qt.QApplication([])
window = Qt.QWidget()

#The GUI needs to be contained inside a widget object
widget_containing_interface_GUI = Qt.QWidget()
widget_containing_interface_GUI.setStyleSheet(".QWidget {\n" \
            + "border: 1px solid black;\n" \
            + "border-radius: 4px;\n" \
            + "}") 


#Create the interface object for the powermeter
Interface = pyThorlabsPM100x.interface(app=app,mainwindow=window)
Interface.verbose = False #set the verbosity of the interface logger to False
# At any time during the software execution, the power read by the instrument can be accessed via Interface.output['Power']
# Moreover, one could also set up a signal to automatically call another function whenever the power is updated, by
#
#       Interface.sig_updated_data.connect(foo)    
#
# Every time the power is read from the instrument, the function foo is called and the list [power,power_units] is passed as argument

#Create the GUI for the powermeter
gui = pyThorlabsPM100x.gui(interface = Interface, parent=widget_containing_interface_GUI,plot=False)

#Create additional GUI
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