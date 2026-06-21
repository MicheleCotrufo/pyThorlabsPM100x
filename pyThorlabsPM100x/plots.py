''' Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes'''

"""
Live power plot widget for pyThorlabsPM100x.

Provides :class:`PlotObject`, a thin wrapper around a ``pyqtgraph.PlotWidget``
that is embedded in the GUI's floating plot window to display the accumulated
power readings in real time.
"""
# v0.1 (2022-02-15)

import PyQt5.QtWidgets as Qt
import pyqtgraph as pg


class PlotObject:
    """
    A pyqtgraph-based live plot embedded inside a parent Qt widget.

    Creates a ``PlotWidget`` with a grid, sets it as the layout of ``parent``,
    and exposes a single ``data`` curve that the GUI updates on each acquisition
    by calling ``self.data.setData(x, y)``.

    Attributes
    ----------
    app : Qt.QApplication
        The shared PyQt5 application object.
    parent : Qt.QWidget
        The widget that hosts this plot (its layout is set to a ``QVBoxLayout``
        containing the ``PlotWidget``).
    graphWidget : pg.PlotWidget
        The pyqtgraph plot widget. Use this to set axis labels, titles, or any
        other plot properties after construction.
    data : pg.PlotDataItem
        The plot curve. Call ``data.setData(x, y)`` to update the displayed data.
    ConfigPopupOpen : int
        Flag (0/1) indicating whether a configuration popup is currently open.
        Reserved for future use.
    """

    def __init__(self,  app, parent):
        """
        Parameters
        ----------
        app : Qt.QApplication
            The shared PyQt5 application object.
        parent : Qt.QWidget
            The Qt widget that will host the plot. Its layout is replaced with a
            ``QVBoxLayout`` containing the ``PlotWidget``.
        """
        self.app = app
        self.parent = parent
        
        self.ConfigPopupOpen = 0 #This variable is 1 when the popup for plot configuration is open, and 0 otherwise

        self.Max = 0 #Keep track of the maximum and minimum values plotted in this plot (among all possible curves). It is used for resizing purposes
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