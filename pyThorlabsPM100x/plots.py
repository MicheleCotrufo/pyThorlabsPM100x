### v0.1 (2022-02-15)


import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import pyqtgraph as pg
import logging


class PlotObject:
    def __init__(self,  app,  mainwindow, parent):#, GetData, GetNameData, GetPlotConfig, SetPlotConfig, GetPlottingStyle, PlotSize, **kwargs):
        # app           = The pyqt5 QApplication() object
        # mainwindow    = Main Window of the application
        # parent        = a QWidget (or QMainWindow) object that will be the parent for the gui of this device.

        self.mainwindow = mainwindow
        self.app = app
        self.parent = parent
        
        self.ConfigPopupOpen = 0 #This variable is 1 when the popup for plot configuration is open, and 0 otherwise


        self.Max = 0 #Keep track of the maximum of minimum values plotted in this plot (among all possible curves). It is used for resizing purposes
        self.Min = 0

        #Create the figure

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.showGrid(x=True, y=True)
        #self.graphWidget.setMenuEnabled(False)
        vbox = Qt.QVBoxLayout()
        vbox.addWidget(self.graphWidget) 
        #vbox.addStretch(1)

        self.parent.setLayout(vbox)

        X = []
        Y = []


        ## plot data: x, y values
        self.data = self.graphWidget.plot(X,Y)

