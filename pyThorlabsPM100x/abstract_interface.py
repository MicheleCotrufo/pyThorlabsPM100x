''' Abstract class containing methods for any interface of any instrument'''
import PyQt5.QtCore as QtCore
import logging

class abstract_interface():
    def __init__(self, app, mainwindow, name_logger=__package__):
        # app           = The pyqt5 QApplication() object
        # mainwindow    = Main Window of the application
        # name_logger   = The name of the logger used for this particular istance of the interface object. If none is specified, the name of package is used as logger name

        self.mainwindow = mainwindow
        self.app = app
        self.mainwindow.child = self #make sure that the window embedding this interface knows about its child (this is mainly used to link the closing events when using multiple windows)
 
        self._verbose = True #Keep track of whether this instance of the interface should produce logs or not
        self._name_logger = ''
        self.name_logger = name_logger #Setting this property will also create the logger,set defaulat output style, and store the logger object in self.logger
    
    @property
    def verbose(self):
        return self.verbose

    @verbose.setter
    def verbose(self,verbose):
        #When the verbose property of this interface is changed, we also update accordingly the level of the logger object
        if verbose: loglevel = logging.INFO
        else: loglevel = logging.CRITICAL
        self.logger.setLevel(level=loglevel)

    @property
    def name_logger(self):
        return self._name_logger

    @name_logger.setter
    def name_logger(self,name):
        #Create logger, and set default output style.
        self._name_logger = name
        self.logger = logging.getLogger(self._name_logger)
        self.verbose = self._verbose #This will automatically set the logger verbosity too
        if not self.logger.handlers:
            formatter = logging.Formatter(f"[{self.name_logger}]: %(message)s")
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
        self.logger.propagate = False

    def set_trigger(self,external_function,delay=0):
        '''
        This method allows to use this device as a trigger for other operations. Every time that this interface object acquires data from the device (i.e. every time 
        the function self.update is executed with self.continuous_read == True), the function external_function is also called. external_function must be a valid function which does not 
        require any input parameter.
        The optional parameter delay sets a delay (in seconds) between the call to the function update and the call to the function external_function
        '''
        if external_function == None:
            self.trigger = None
            return
        if not(callable(external_function)):
            self.logger.error(f"Input parameter external_function must be a valid function")  
            return  
        self.logger.info(f"Creating a trigger for this device...")
        self.trigger = [external_function, delay]

    def send_trigger(self):
        if(self.trigger[1])>0:
            self.logger.info(f"Trigger will be sent in {self.trigger[1]} seconds.")
            QtCore.QTimer.singleShot(int(self.trigger[1]*1e3), self._send_trigger)
        else:
            self._send_trigger()

    def _send_trigger(self):
        self.logger.info(f"Trigger sent.")
        self.trigger[0]()

    def update(self):
        if hasattr(self,'trigger'):
            if not(self.trigger==None):
                self.send_trigger()

    def close(self):     
        try:
            if (self.instrument.connected == True):
                self.disconnect_device()
        except Exception as e:
            self.logger.error(f"{e}")
            if hasattr(self,'plot_window'):
                if self.gui.plot_window:
                    self.gui.plot_window.close()

class abstract_gui():
    def __init__(self,interface,parent):
        self.interface = interface
        self.parent = parent

    def initialize(self):
        self.parent.setLayout(self.container) 
        self.parent.resize(self.parent.minimumSize())
        return

    def disable_widget(self,widgets):
        for widget in widgets:
            if widget:
                widget.setEnabled(False)   

    def enable_widget(self,widgets):
        for widget in widgets:
            if widget:
                widget.setEnabled(True) 