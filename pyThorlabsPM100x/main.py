import os
import PyQt5
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import logging
import sys
import argparse

import abstract_instrument_interface
from pyThorlabsPM100x.driver import ThorlabsPM100x
from pyThorlabsPM100x.plots import PlotObject

graphics_dir = os.path.join(os.path.dirname(__file__), 'graphics')

class interface(abstract_instrument_interface.abstract_interface):
    """
    Create a high-level interface with the device, and act as a connection between the low-level
    interface (i.e. the driver) and the gui.
    Several general-purpose attributes and methods are defined in the class abstract_interface defined in abstract_instrument_interface
    ...

    Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_interface for general attributes)
    ----------
    instrument
        Instance of driver.ThorlabsPM100x
    connected_device_name : str
        Name of the physical device currently connected to this interface 
    continuous_read : bool 
        When this is set to True, the data from device are acquired continuosly at the rate set by refresh_time
    refresh_time : float, 
        The time interval (in seconds) between consecutive reeading from the device driver (default = 0.2)
    stored_data : list
        List used to store data acquired by this interface
    power_units : str
        The power units of this device
    current_power_string : str 
        Last power read from powermeter, as a string


    Methods defined in this class (see the abstract class abstract_instrument_interface.abstract_interface for general methods)
    -------
    refresh_list_devices()
        Get a list of compatible devices from the driver. Store them in self.list_devices, send signal to populate the combobox in the GUI.
    connect_device(device_full_name)
        Connect to the device identified by device_full_name
    disconnect_device()
        Disconnect the currently connected device
    close()
        Closes this interface, close plot window (if any was open), and calls the close() method of the parent class, which typically calls the disconnect_device method
    
    set_disconnected_state()
        
    set_connecting_state()
    
    set_connected_state()
    
    set_refresh_time(refresh_time)
    
    set_wavelength(wl)
    
    read_wavelength()
    
    change_power_range(direction)
    
    set_auto_power_range(status)
    
    read_auto_power_range()
    
    set_zero_powermeter()
    
    start_reading()
    
    pause_reading()
    
    stop_reading()
    
    update()

    """

    output = {'Power':0}  #We define this also as class variable, to make it possible to see which data is produced by this interface without having to create an object

    def __init__(self, **kwargs):
        self.output = {'Power':0} 
        
        ### Default values of settings (might be overwritten by settings saved in .json files later)
        self.settings = {   'refresh_time': 0.2,
                            'auto_power_range': True
                            }
        
        self.list_devices = []          #list of devices found   
        self.continuous_read = False    # When this is set to True, the data from device are acquired continuosly at the rate set by self.refresh_time
        self.stored_data = [] # List used to store data acquired by device
        self.current_power_string = " " # Last power read from powermeter, as a string
        self.connected_device_name = ''
        ###
        self.instrument = ThorlabsPM100x() 
        ###
        self.gui_class = gui
        ###
        super().__init__(**kwargs)

############################################################
### Functions to interface the GUI and low-level driver
############################################################

    def refresh_list_devices(self):
        '''
        Get a list of all devices connected, by using the method list_devices() of the driver. For each device obtain its identity and its address.
        For each device, create the string "identity -->  address" and add the string to the corresponding combobox in the GUI 
        '''
        self.gui.combo_Devices.clear()                      #First we empty the combobox       
        self.list_devices = []
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices() #Then we read the list of devices
        self.list_devices = list_valid_devices
        if(len(list_valid_devices)>0):
            list_IDNs_and_devices = [dev[1] + " --> " + dev[0] for dev in list_valid_devices] 
            self.gui.combo_Devices.addItems(list_IDNs_and_devices)  
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 

    def connect_device(self,device_full_name):
        if(device_full_name==''): 
            self.logger.error("No valid device has been selected.")
            return
        self.set_connecting_state()
        device_name = device_full_name.split(' --> ')[1].lstrip()   # We extract the device address from the device name
        self.logger.info(f"Connecting to device {device_name}...")
        try:
            (Msg,ID) = self.instrument.connect_device(device_name)      # Try to connect by using the method ConnectDevice of the powermeter object
            if(ID==1):  #If connection was successful
                self.logger.info(f"Connected to device {device_name}.")
                self.connected_device_name = device_name
                self.set_connected_state()
                self.start_reading()
            else: #If connection was not successful
                self.logger.error(f"Error: {Msg}")
                self.set_disconnected_state()
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.set_disconnected_state()

    def disconnect_device(self):
        self.logger.info(f"Disconnecting from device {self.connected_device_name}...")
        (Msg,ID) = self.instrument.disconnect_device()
        if(ID==1): # If disconnection was successful
            self.logger.info(f"Disconnected from device {self.connected_device_name}.")
            self.continuous_read = 0 # We set this variable to 0 so that the continuous reading from the powermeter will stop
            self.set_disconnected_state()
        else: #If disconnection was not successful
            self.logger.error(f"Error: {Msg}")
            self.set_disconnected_state() #When disconnection is not succeful, it is typically because the device alredy lost connection
                                          #for some reason. In this case, it is still useful to have all widgets reset to disconnected state      
    def close(self,**kwargs):
        if hasattr(self.gui,'plot_window'):
            if self.gui.plot_window:
                self.gui.plot_window.close()
        super().close(**kwargs)           
    
    def set_disconnected_state(self):
        self.gui.set_disconnected_state()

    def set_connecting_state(self):
        self.gui.set_connecting_state()

    def set_connected_state(self):
        self.power_units = self.instrument.power_units
        self.gui.set_connected_state()
        self.read_wavelength()
        #self.read_status_power_autorange()
        self.set_auto_power_range(self.settings['auto_power_range'])
        self.read_power_range()

    def set_refresh_time(self, refresh_time):
        try: 
            refresh_time = float(refresh_time)
            if self.settings['refresh_time'] == refresh_time: #in this case the number in the refresh time edit box is the same as the refresh time currently stored
                return True
        except ValueError:
            self.logger.error(f"The refresh time must be a valid number.")
            self.gui.edit_RefreshTime.setText(f"{self.settings['refresh_time']:.3f}")
            return False
        if refresh_time < 0.001:
            self.logger.error(f"The refresh time must be positive and >= 1ms.")
            self.gui.edit_RefreshTime.setText(f"{self.settings['refresh_time']:.3f}")
            return False
        self.logger.info(f"The refresh time is now {refresh_time} s.")
        self.settings['refresh_time'] = refresh_time
        self.gui.edit_RefreshTime.setText(f"{self.settings['refresh_time']:.3f}")
        return True

    def set_wavelength(self, wl):
        try:
            if int(self.instrument.wavelength) == int(wl): #in this case the number in the refresh time edit box is the same as the wavelength currently set
                    return True
            self.logger.info(f"Setting the wavelength to {wl} for the device {self.connected_device_name}...")
        except ValueError:
            self.logger.error(f"The wavelength must be a valid number.")
            self.gui.edit_Wavelength.setText(str(self.instrument.wavelength))
            return False
        try: 
            self.instrument.wavelength = wl
            self.logger.info(f"Wavelength set correctly.")
        except Exception as e:
            self.logger.error(f"An error occurred while setting the wavelength: {e}")
            self.gui.edit_Wavelength.setText(str(self.instrument.wavelength))
            return False
        self.read_power_range() #The boundaries of the power ranges might change when the wavelength is changed, so we need to update it after changing the wavelength
        return True
        
    def read_wavelength(self):
        self.logger.info(f"Reading current wavelength from device {self.connected_device_name}...") 
        self.wavelength = self.instrument.wavelength
        if self.wavelength == None:
            self.logger.error(f"An error occurred while reading the wavelength from this device.")
            return
        self.gui.edit_Wavelength.setText(str(int(self.wavelength)))
        self.logger.info(f"Current wavelength is {self.wavelength}.") 
        return

    def change_power_range(self,direction):
        if direction == +1:
            string = 'increase'
        else: 
            string = 'decrease'
        self.logger.info(f"Trying to {string} the power range...")
        self.instrument.move_to_next_power_range(direction)
        self.read_power_range()
        return

    def read_power_range(self):
        self.logger.info(f"Reading current power range from device {self.connected_device_name}...") 
        self.power_range = self.instrument.power_range
        if self.power_range == None:
            self.logger.error(f"An error occurred while reading the power range from this device.")
            return
        self.gui.edit_PowerRange.setText(f"{self.power_range:.2e}")
        self.gui.edit_PowerRange.setCursorPosition(1)
        self.logger.info(f"Current power range is {self.power_range}.") 

    def set_auto_power_range(self,status):
        status = bool(status)
        status_string = 'ON' if status else 'OFF'
        self.logger.info(f"Setting the auto-ranging function to {status_string} for the device {self.connected_device_name}...")    
        try:
            self.instrument.auto_power_range  = status
            self.gui.set_auto_power_range_state(status)
            self.logger.info(f"Setting changed succesfully.")
            self.settings['auto_power_range'] = status
            self.gui.box_PowerRangeAuto.setChecked(status)
        except Exception as e:
            self.logger.error(f"An error occurred while setting the auto-ranging status: {e}")

        #self.read_auto_power_range()
        self.read_power_range()

    def read_auto_power_range(self):
        self.logger.info(f"Reading the status of the auto-ranging function for the device {self.connected_device_name}...")   
        try:
            auto_power_range = self.instrument.auto_power_range
            status_string = 'ON' if auto_power_range else 'OFF'
            self.gui.box_PowerRangeAuto.setChecked(auto_power_range)
            self.gui.set_auto_power_range_state(status)
            self.logger.info(f"The auto-ranging function is currently set to {status_string}.")
            self.settings['auto_power_range'] = auto_power_range
            return auto_power_range
        except Exception as e:
            self.logger.error(f"An error occurred while reading the auto-ranging status: {e}")

    def set_zero_powermeter(self):
        try: 
            ID = self.instrument.set_zero()
            self.logger.info(f"Zero-ing the device {self.connected_device_name}...")
            if ID == 1:
                self.logger.info(f"Device was succesfully zeroed.")
            else:
                self.logger.error(f"An error occurred while zero-ing this device.")
        except Exception as e:
            self.logger.error(f"An error occurred while zero-ing this device: {e}")
        return

    def start_reading(self):
        if(self.instrument.connected == False):
            self.logger.error(f"No device is connected.")
            return
        #self.logger.info(f"Updating wavelength and refresh time before starting reading...")
        if not(self.gui.press_enter_refresh_time()): #read the current value in the refresh_time textbox, and validates it. The function returns True/False if refresh_time was valid
            return
        if not(self.gui.press_enter_wavelength()): #read the current value in the refresh_time textbox, and validates it. The function returns True/False if refresh_time was valid
            return
        
        self.gui.set_reading_state() # Change some widgets

        self.continuous_read = True #Until this variable is set to True, the function UpdatePower will be repeated continuosly 
        self.logger.info(f"Starting reading from device {self.connected_device_name}...")
        # Call the function self.update(), which will do stome suff (read power and store it in a global variable) and then call itself continuosly until the variable self.continuous_read is set to False
        self.update()
        return
 
    def pause_reading(self):
        #Sets self.continuous_read to False (this will force the function update() to stop calling itself)
        self.continuous_read = False
        self.logger.info(f"Paused reading from device {self.connected_device_name}.")
        self.gui.set_pause_state() # Change some widgets
        return

    def stop_reading(self):
        #Sets self.continuous_read to False (this will force the function update() to stop calling itself) and delete all accumulated data
        self.continuous_read = False
        self.stored_data = []
        self.update() #We call one more time the self.update() function to make sure plots is cleared. Since self.continuous_read is already set to False, update() will not acquire data anymore
        self.logger.info(f"Stopped reading from device {self.connected_device_name}. All stored data have been deleted.")
        self.gui.set_stopped_state() # Change some widgets
        # ...
        return
        
    def update(self):
        '''
        This routine reads continuosly the power from the powermeter and stores its value
        If we are continuosly acquiring the power (i.e. if self.ContinuousRead = 1) then:
            1) Reads the power from the powermeter object and stores it in the self.output dictionary
            2) Update the value of the variable self.current_power_string by generating a string containing the power and its units
            3) Update the textbox in the GUI
            3) Call itself after a time given by self.refresh_time
        '''
        if self.gui.plot_object:
            self.gui.plot_object.data.setData(list(range(1, len(self.stored_data)+1)), self.stored_data) #This line is executed even when self.continuous_read == False, to make sure that plot gets cleared when user press the stop button
        if(self.continuous_read == True):
            (currentPower,power_units) = self.instrument.power
            self.output['Power'] = currentPower
            self.stored_data.append(currentPower)
            #self.output['PowerUnits'] = power_units

            super().update()    

            self.current_power_string = f"{currentPower:.2e}" + ' ' +  power_units
            self.gui.edit_Power.setText(self.current_power_string)
            QtCore.QTimer.singleShot(int(self.settings['refresh_time']*1e3), self.update)
           
        return

############################################################
### END Functions to interface the GUI and low-level driver
############################################################
    
    
class gui(abstract_instrument_interface.abstract_gui):
     
    def __init__(self,interface,parent,plot=False):
        """
        Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_gui for general attributes)
        ----------
        plot, bool
            If set true, the GUI also generates a plot object (and a button to show/hide the plot) to plot the content of the self.stored_data object
        """
        super().__init__(interface,parent)

        self.widgets_enabled_when_connected = []     #The widgets in this list will only be enabled when the interface has succesfully connected to a device
        self.widgets_enabled_when_disconnected = []  #The widgets in this list will only be enabled when the interface is not connected to a device
        self.plot_window = None # QWidget object of the widget (i.e. floating window) that will contain the plot
        self.plot_object = None # PlotObject object of the plot where self.store_powers is plotted

        if plot:        # Create a plot object
            self.create_plot() 

    def initialize(self):
        self.create_widgets()

        ### SET INITIAL STATE OF WIDGETS
        self.edit_Power.setText(self.interface.current_power_string)
        self.box_PowerRangeAuto.setChecked(self.interface.settings['auto_power_range'])
        self.edit_RefreshTime.setText(f"{self.interface.settings['refresh_time']:.3f}")
        self.interface.refresh_list_devices()    #By calling this method, as soon as the gui is created we also look for devices
        self.set_disconnected_state()               #When GUI is created, all widgets are set to the "Disconnected" state
        ###

        self.connect_widgets_events_to_functions()

        ### Call the initialize method of the parent class
        super().initialize()

    def create_widgets(self):
        hbox1 = Qt.QHBoxLayout()
        self.label_DeviceList = Qt.QLabel("Devices: ")
        self.combo_Devices = Qt.QComboBox()
        self.button_RefreshDeviceList = Qt.QPushButton("")
        self.button_RefreshDeviceList.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'refresh.png')))     
        hbox1.addWidget(self.label_DeviceList)
        hbox1.addWidget(self.combo_Devices,stretch=1)
        hbox1.addWidget(self.button_RefreshDeviceList)

        hbox2 = Qt.QHBoxLayout()
        self.button_ConnectDevice = Qt.QPushButton("Connect")
        self.button_SetZeroPowermeter = Qt.QPushButton("Set Zero")    
        self.label_Wavelength = Qt.QLabel("Wavelength: ")
        self.edit_Wavelength = Qt.QLineEdit()
        self.edit_Wavelength.setAlignment(QtCore.Qt.AlignRight)
        self.label_WavelengthUnits = Qt.QLabel("nm")
        self.label_PowerRange = Qt.QLabel("Power range: ")
        self.button_DecreasePowerRange = Qt.QPushButton("<")
        self.button_DecreasePowerRange.setToolTip('Decrease the powermeter power range.')
        self.button_DecreasePowerRange.setMaximumWidth(15)       
        self.edit_PowerRange = Qt.QLineEdit()
        self.edit_PowerRange.setToolTip('Maximum power measurable in the current power range (unless \'Auto\' is checked).')
        self.edit_PowerRange.setReadOnly(True)
        self.button_IncreasePowerRange = Qt.QPushButton(">")
        self.button_IncreasePowerRange.setToolTip('Increase the powermeter power range.')
        self.button_IncreasePowerRange.setMaximumWidth(15)
        self.box_PowerRangeAuto = Qt.QCheckBox("Auto")

        self.box_PowerRangeAuto.setToolTip('Set the power range of the powermeter to Automatic.')
        hbox2.addWidget(self.button_ConnectDevice)
        hbox2.addWidget(self.button_SetZeroPowermeter)
        hbox2.addWidget(self.label_Wavelength)
        hbox2.addWidget(self.edit_Wavelength)
        hbox2.addWidget(self.label_WavelengthUnits)
        hbox2.addWidget(self.label_PowerRange)
        hbox2.addWidget(self.button_DecreasePowerRange)
        hbox2.addWidget(self.edit_PowerRange)
        hbox2.addWidget(self.button_IncreasePowerRange)
        hbox2.addWidget(self.box_PowerRangeAuto)

        hbox3 = Qt.QHBoxLayout()
        self.button_StartPauseReading = Qt.QPushButton("")
        self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))
        self.button_StartPauseReading.setToolTip('Start or pause the reading from the powermeter. The previous data points are not discarded when pausing.') 
        self.button_StopReading = Qt.QPushButton("")
        self.button_StopReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'stop.png')))
        self.button_StopReading.setToolTip('Stop the reading from the powermeter. All previous data points are discarded.') 
        self.label_RefreshTime = Qt.QLabel("Refresh time (s): ")
        self.label_RefreshTime.setToolTip('Specifies how often the power is read from the powermeter (Minimum value = 0.001 s).') 
        self.edit_RefreshTime  = Qt.QLineEdit()
        self.edit_RefreshTime.setToolTip('Specifies how often the power is read from the powermeter (Minimum value = 0.001 s).') 
        self.edit_RefreshTime.setAlignment(QtCore.Qt.AlignRight)
        font = QtGui.QFont("Times", 12,QtGui.QFont.Bold)
        self.label_Power = Qt.QLabel("Power: ")
        self.label_Power.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.label_Power.setFont(font)
        self.edit_Power = Qt.QLineEdit()
        self.edit_Power.setFont(font)
        self.edit_Power.setAlignment(QtCore.Qt.AlignRight)
        self.edit_Power.setReadOnly(True)
        hbox3.addWidget(self.button_StartPauseReading)

        if self.plot_object:
            self.button_ShowHidePlot = Qt.QPushButton("Show/Hide Plot")
            self.button_ShowHidePlot.setToolTip('Show/Hide Plot.')
            hbox3.addWidget(self.button_StopReading)

        hbox3.addWidget(self.label_RefreshTime)
        hbox3.addWidget(self.edit_RefreshTime)
        hbox3.addWidget(self.label_Power)
        hbox3.addWidget(self.edit_Power)

        if self.plot_object:
            hbox3.addWidget(self.button_ShowHidePlot)
                
        self.container = Qt.QVBoxLayout()
        self.container.addLayout(hbox1)  
        self.container.addLayout(hbox2)  
        self.container.addLayout(hbox3)  
        self.container.addStretch(1)

        self.widgets_enabled_when_connected = [self.button_SetZeroPowermeter, 
                                               self.edit_Wavelength, 
                                               self.edit_PowerRange, 
                                               self.box_PowerRangeAuto, 
                                               self.button_IncreasePowerRange, 
                                               self.button_DecreasePowerRange,
                                               self.button_StartPauseReading,
                                               self.button_StopReading]
        self.widgets_enabled_when_disconnected = [self.combo_Devices , 
                                                  self.button_RefreshDeviceList]

    def connect_widgets_events_to_functions(self):
        self.button_RefreshDeviceList.clicked.connect(self.click_button_refresh_list_devices)
        self.button_ConnectDevice.clicked.connect(self.click_button_connect_disconnect)
        self.button_SetZeroPowermeter.clicked.connect(self.click_button_set_zero_powermeter)
        self.edit_Wavelength.returnPressed.connect(self.press_enter_wavelength)
        self.button_DecreasePowerRange.clicked.connect(lambda x:self.click_button_change_power_range(-1))
        self.button_IncreasePowerRange.clicked.connect(lambda x:self.click_button_change_power_range(+1))
        self.box_PowerRangeAuto.stateChanged.connect(self.click_box_PowerRangeAuto)
        self.button_StartPauseReading.clicked.connect(self.click_button_StartPauseReading)
        self.button_StopReading.clicked.connect(self.click_button_StopReading)
        self.edit_RefreshTime.returnPressed.connect(self.press_enter_refresh_time)

        if self.plot_object:
            self.button_ShowHidePlot.clicked.connect(self.click_button_ShowHidePlot)

    def set_disconnected_state(self):
        self.disable_widget(self.widgets_enabled_when_connected)
        self.enable_widget(self.widgets_enabled_when_disconnected)
        self.edit_PowerRange.setText('')
        self.edit_Wavelength.setText('')
        self.button_ConnectDevice.setText("Connect")
        self.edit_Power.setText('')

    def set_connecting_state(self):
        self.disable_widget(self.widgets_enabled_when_connected)
        self.enable_widget(self.widgets_enabled_when_disconnected)
        self.button_ConnectDevice.setText("Connecting...")

    def set_connected_state(self):
        self.enable_widget(self.widgets_enabled_when_connected)
        self.disable_widget(self.widgets_enabled_when_disconnected)
        self.button_ConnectDevice.setText("Disconnect")
        #If a self.plot_object was created, update window title with powermeter name and vertical axis of plot with current Power units
        if self.plot_object: 
            self.plot_object.graphWidget.setLabel("left", f"Power [{self.interface.instrument._power_units}]")
            self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")

    def set_pause_state(self):
        self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))
    def set_reading_state(self):
        self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'pause.png')))
    def set_stopped_state(self):    
        self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))

    def set_auto_power_range_state(self,auto_power_range):
        if auto_power_range:
            self.disable_widget([self.edit_PowerRange,self.button_IncreasePowerRange, self.button_DecreasePowerRange])
        else:
            self.enable_widget([self.edit_PowerRange,self.button_IncreasePowerRange, self.button_DecreasePowerRange])
            
############################################################
### GUI Events Functions
############################################################

    def click_button_refresh_list_devices(self):
        self.interface.refresh_list_devices()

    def click_button_connect_disconnect(self):
        if(self.interface.instrument.connected == False): # We attempt connection   
            device_full_name = self.combo_Devices.currentText() # Get the device name from the combobox
            self.interface.connect_device(device_full_name)
        elif(self.interface.instrument.connected == True): # We attempt disconnection
            self.interface.disconnect_device()

    def click_box_PowerRangeAuto(self, state):
        if state == QtCore.Qt.Checked:
            status_bool = True
        else:
            status_bool = False
        self.interface.set_auto_power_range(status_bool)

    def click_button_set_zero_powermeter(self):
        self.interface.set_zero_powermeter()

    def press_enter_wavelength(self):
        return self.interface.set_wavelength(self.edit_Wavelength.text())
        
    def click_button_change_power_range(self,direction):
        self.interface.change_power_range(direction)
       
    def click_button_StartPauseReading(self): 
        if(self.interface.continuous_read == False):
            self.interface.start_reading()
        elif (self.interface.continuous_read == True):
            self.interface.pause_reading()
        return

    def click_button_StopReading(self):
        self.interface.stop_reading()

    def press_enter_refresh_time(self):
        return self.interface.set_refresh_time(self.edit_RefreshTime.text())

    def click_button_ShowHidePlot(self):
        self.plot_window.setHidden(not self.plot_window.isHidden())

############################################################
### END GUI Events Functions
############################################################

    def create_plot(self):
        '''
        This function creates an additional (separated) window with a pyqtgraph object, which plots the contents of self.stored_data
        '''
        self.plot_window = Qt.QWidget() #This is the widget that will contain the plot. Since it does not have a parent, the plot will be in a floating (separated) window
        self.plot_object = PlotObject(self.interface.app, self.interface.mainwindow, self.plot_window)
        styles = {"color": "#fff", "font-size": "20px"}
        self.plot_object.graphWidget.setLabel("left", "Power", **styles)
        self.plot_object.graphWidget.setLabel("bottom", "Acqusition #", **styles)
        self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")
        self.plot_window.show()
        self.plot_window.setHidden(True)
            


class MainWindow(Qt.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(__package__)

    def closeEvent(self, event):
        if self.child:
            pass#self.child.close()

#################################################################################################

def main():
    parser = argparse.ArgumentParser(description = "",epilog = "")
    parser.add_argument("-s", "--decrease_verbose", help="Decrease verbosity.", action="store_true")
    args = parser.parse_args()
    
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    Interface = interface(app=app,mainwindow=window) #In this case window is both the MainWindow and the parent of the gui
    Interface.verbose = not(args.decrease_verbose)
    app.aboutToQuit.connect(Interface.close) 
    Interface.create_gui(window,plot=True)
    window.show()
    app.exec()# Start the event loop.

if __name__ == '__main__':
    main()

#################################################################################################
