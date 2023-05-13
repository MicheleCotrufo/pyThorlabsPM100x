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
import pyThorlabsPM100x.driver_virtual
import pyThorlabsPM100x.driver
from pyThorlabsPM100x.plots import PlotObject

graphics_dir = os.path.join(os.path.dirname(__file__), 'graphics')

##This application follows the model-view-controller paradigm, but with the view and controller defined inside the same object (the GUI)
##The model is defined by the class 'interface', and the view+controller is defined by the class 'gui'. 

class interface(abstract_instrument_interface.abstract_interface):
    """
    Create a high-level interface with the device, validates input data and perform high-level tasks such as periodically reading data from the instrument.
    It uses signals (i.e. QtCore.pyqtSignal objects) to notify whenever relevant data has changes. These signals are typically received by the GUI
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
    stored_data : list
        List used to store data acquired by this interface
    power_units : str
        The power units of this device
    settings = {
                'refresh_time': float,      The time interval (in seconds) between consecutive reeading from the device driver (default = 0.2)
                'auto_power_range': bool    Keep track of whether the device is in auto power range modality
                }


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
   
    set_connected_state()
        This method also calls the set_connected_state() method defined in abstract_instrument_interface.abstract_interface
    
    set_refresh_time(refresh_time)
    
    set_wavelength(wl)
    
    read_wavelength()

    read_min_max_wavelength()
    
    change_power_range(direction)
    
    set_auto_power_range(status)
    
    read_auto_power_range()
    
    set_zero_powermeter()
    
    start_reading()
    
    pause_reading()
    
    stop_reading()
    
    update()
        This method also calls the update() method defined in abstract_instrument_interface.abstract_interface

    """

    output = {'Power':0}  #We define this also as class variable. This makes it possible to see which data is produced by this interface without having to create an object

    ## SIGNALS THAT WILL BE USED TO COMMUNICATE WITH THE GUI
    #                                                           | Triggered when ...                                        | Parameter(s) Sent     
    #                                                       #   -----------------------------------------------------------------------------------------------------------------------         
    sig_list_devices_updated = QtCore.pyqtSignal(list)      #   | List of devices is updated                                | List of devices   
    sig_reading = QtCore.pyqtSignal(int)                    #   | Reading status changes                                    | 1 = Started Reading, 2 = Paused Reading, 3 Stopped Reading
    sig_updated_data = QtCore.pyqtSignal(object)            #   | Data is read from instrument                              | Acquired data 
    sig_wavelength = QtCore.pyqtSignal(int)                 #   | Wavelength is changed                                     | Current Wavelength
    sig_min_max_wavelength = QtCore.pyqtSignal(int,int)     #   | Min and max wavelengths supported by this device are read | Current Min and max wavelengths
    sig_refreshtime = QtCore.pyqtSignal(float)              #   | Refresh time is changed                                   | Current Refresh time 
    sig_power_range = QtCore.pyqtSignal(float)              #   | Power range is changed                                    | Current Power range
    sig_auto_power_range = QtCore.pyqtSignal(bool)          #   | Auto power range setting is changed                       | Current Status of auto power range (true/false)
    ##
    # Identifier codes used for view-model communication. Other general-purpose codes are specified in abstract_instrument_interface
    SIG_READING_START = 1
    SIG_READING_PAUSE = 2
    SIG_READING_STOP = 3

    def __init__(self, **kwargs):
        self.output = {'Power':0} 
        ### Default values of settings (might be overwritten by settings saved in .json files later)
        self.settings = {   'refresh_time': 0.2,
                            'auto_power_range': True
                            }
        
        self.list_devices = []          #list of devices found 
        self.connected_device_name = ''
        self.continuous_read = False    # When this is set to True, the data from device are acquired continuosly at the rate set by self.refresh_time
        self.stored_data = []           # List used to store data acquired by device
        ###
        if ('virtual' in kwargs.keys()) and (kwargs['virtual'] == True):
            self.instrument = pyThorlabsPM100x.driver_virtual.ThorlabsPM100x() 
        else:    
            self.instrument = pyThorlabsPM100x.driver.ThorlabsPM100x() 
        ###
        super().__init__(**kwargs)
        self.refresh_list_devices()   
        
    def refresh_list_devices(self):
        '''
        Get a list of all devices connected, by using the method list_devices() of the driver. For each device obtain its identity and its address.
        '''     
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices() #Then we read the list of devices
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 
        self.list_devices = list_valid_devices
        self.send_list_devices()

    def send_list_devices(self):
        if(len(self.list_devices)>0):
            list_IDNs_and_devices = [dev[1] + " --> " + dev[0] for dev in self.list_devices] 
        else:
            list_IDNs_and_devices = []
        self.sig_list_devices_updated.emit(list_IDNs_and_devices)

    def connect_device(self,device_full_name):
        if(device_full_name==''): 
            self.logger.error("No valid device has been selected.")
            return
        self.set_connecting_state()
        device_name = device_full_name.split(' --> ')[1].lstrip()   # We extract the device address from the device name
        self.logger.info(f"Connecting to device {device_name}...")
        try:
            (Msg,ID) = self.instrument.connect_device(device_name)      # Try to connect by using the method connect_device of the device driver
            if(ID==1):  #If connection was successful
                self.logger.info(f"Connected to device {device_name}.")
                self.connected_device_name = device_name
                self.set_connected_state()
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
        super().close(**kwargs)           

    def set_connected_state(self):
        super().set_connected_state()
        self.power_units = self.instrument.power_units
        self.read_min_max_wavelength()
        self.read_wavelength()
        #self.read_status_power_autorange()
        self.set_auto_power_range(self.settings['auto_power_range'])
        #self.read_power_range()
        self.start_reading()

    def set_refresh_time(self, refresh_time):
        try: 
            refresh_time = float(refresh_time)
            if self.settings['refresh_time'] == refresh_time: #in this case the number in the refresh time edit box is the same as the refresh time currently stored
                return True
        except ValueError:
            self.logger.error(f"The refresh time must be a valid number.")
            self.sig_refreshtime.emit(self.settings['refresh_time'])
            return False
        if refresh_time < 0.001:
            self.logger.error(f"The refresh time must be positive and >= 1ms.")
            self.sig_refreshtime.emit(self.settings['refresh_time'])
            return False
        self.logger.info(f"The refresh time is now {refresh_time} s.")
        self.settings['refresh_time'] = refresh_time
        self.sig_refreshtime.emit(self.settings['refresh_time'])
        return True

    def set_wavelength(self, wl):
        try:
            if int(self.instrument.wavelength) == int(float(wl)): #in this case the number in the refresh time edit box is the same as the wavelength currently set
                    return True
            self.logger.info(f"Setting the wavelength to {wl} for the device {self.connected_device_name}...")
        except ValueError as e:
            self.logger.error(f"The wavelength must be a valid number.")
            self.sig_wavelength.emit(self.instrument.wavelength)
            return False
        try: 
            self.instrument.wavelength = int(float(wl))
            self.logger.info(f"Wavelength set correctly.")
        except Exception as e:
            self.logger.error(f"An error occurred while setting the wavelength: {e}")
            self.sig_wavelength.emit(self.instrument.wavelength)
            return False
        self.read_power_range() #The boundaries of the power ranges might change when the wavelength is changed, so we need to update it after changing the wavelength
        return True
  
    def read_wavelength(self):
        self.logger.info(f"Reading current wavelength from device {self.connected_device_name}...") 
        self.wavelength = int(self.instrument.wavelength)
        if self.wavelength == None:
            self.logger.error(f"An error occurred while reading the wavelength from this device.")
            return
        self.sig_wavelength.emit(self.instrument.wavelength)
        self.logger.info(f"Current wavelength is {self.wavelength}.") 
        return
      
    def read_min_max_wavelength(self):
        self.logger.info(f"Reading min and max wavelength supported by device {self.connected_device_name}...") 
        self.min_max_wls =  (self.instrument.min_wavelength,self.instrument.max_wavelength)
        self.sig_min_max_wavelength.emit(self.min_max_wls[0],self.min_max_wls[1])
        self.logger.info(f"Wavelength range: {self.min_max_wls[0]}-{self.min_max_wls[1]} nm") 

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
        self.sig_power_range.emit(self.power_range)
        self.logger.info(f"Current power range is {self.power_range}.") 

    def set_auto_power_range(self,auto_power_range):
        auto_power_range = bool(auto_power_range)
        status_string = 'ON' if auto_power_range else 'OFF'
        self.logger.info(f"Setting the auto-ranging function to {status_string} for the device {self.connected_device_name}...")    
        try:
            self.instrument.auto_power_range  = auto_power_range
            self.sig_auto_power_range.emit(auto_power_range)
            self.logger.info(f"Setting changed succesfully.")
            self.settings['auto_power_range'] = auto_power_range
        except Exception as e:
            self.logger.error(f"An error occurred while setting the auto-ranging status: {e}")
        #self.read_auto_power_range()
        self.read_power_range()

    def read_auto_power_range(self):
        self.logger.info(f"Reading the status of the auto-ranging function for the device {self.connected_device_name}...")   
        try:
            auto_power_range = self.instrument.auto_power_range
            status_string = 'ON' if auto_power_range else 'OFF'
            self.sig_auto_power_range.emit(auto_power_range)
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
        self.sig_reading.emit(self.SIG_READING_START) # This signal will be caught by the GUI
        self.continuous_read = True #Until this variable is set to True, the function UpdatePower will be repeated continuosly 
        self.logger.info(f"Starting reading from device {self.connected_device_name}...")
        # Call the function self.update(), which will do stome suff (read power and store it in a global variable) and then call itself continuosly until the variable self.continuous_read is set to False
        self.update()
        return
 
    def pause_reading(self):
        #Sets self.continuous_read to False (this will force the function update() to stop calling itself)
        self.continuous_read = False
        self.logger.info(f"Paused reading from device {self.connected_device_name}.")
        self.sig_reading.emit(self.SIG_READING_PAUSE) # This signal will be caught by the GUI
        return

    def stop_reading(self):
        #Sets self.continuous_read to False (this will force the function update() to stop calling itself) and delete all accumulated data
        self.continuous_read = False
        self.stored_data = []
        self.update() #We call one more time the self.update() function to make sure plots is cleared. Since self.continuous_read is already set to False, update() will not acquire data anymore
        self.logger.info(f"Stopped reading from device {self.connected_device_name}. All stored data have been deleted.")
        self.sig_reading.emit(self.SIG_READING_PAUSE) # This signal will be caught by the GUI
        # ...
        return
        
    def update(self):
        '''
        This routine reads continuosly the power from the powermeter and stores its value
        If we are continuosly acquiring the power (i.e. if self.continuous_read = 1) then:
            1) Reads the power from the powermeter and stores it in the self.output dictionary
            2) Calls the update methods of the parent class abstract_instrument_interface.abstract_interface
            3) Update the value of the variable self.current_power_string by generating a string containing the power and its units
            3) Emits the self.sig_updated_data (which will be intercepted by the GUI)
            3) Call itself after a time given by self.refresh_time
        '''
        if(self.continuous_read == True):
            (currentPower,power_units) = self.instrument.power
            self.output['Power'] = currentPower
            self.power_units = power_units
            self.stored_data.append(currentPower)
            #self.output['PowerUnits'] = power_units

            super().update()    

            self.sig_updated_data.emit([currentPower, power_units])
            QtCore.QTimer.singleShot(int(self.settings['refresh_time']*1e3), self.update)
           
        return
    
    
class gui(abstract_instrument_interface.abstract_gui):
     
    def __init__(self,interface,parent,plot=False):
        """
        Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_gui for general attributes)
        ----------
        plot, bool
            If set true, the GUI also generates a plot object (and a button to show/hide the plot) to plot the content of the self.stored_data object
        """
        super().__init__(interface,parent)
        self.plot_window = None # QWidget object of the widget (i.e. floating window) that will contain the plot
        self.plot_object = None # PlotObject object of the plot where self.store_powers is plotted

        if plot:        # Create a plot object
            self.create_plot() 
        self.initialize()

    def initialize(self):
        self.create_widgets()
        self.connect_widgets_events_to_functions()

        ### Call the initialize method of the super class. 
        super().initialize()

        ### Connect signals from model to event slots of this GUI
        self.interface.sig_list_devices_updated.connect(self.on_list_devices_updated)
        self.interface.sig_connected.connect(self.on_connection_status_change) 
        self.interface.sig_reading.connect(self.on_reading_status_change) 
        self.interface.sig_updated_data.connect(self.on_data_change) 
        self.interface.sig_refreshtime.connect(self.on_refreshtime_change)
        self.interface.sig_wavelength.connect(self.on_wavelength_change)
        self.interface.sig_min_max_wavelength.connect(self.on_min_max_wavelength_update)
        self.interface.sig_auto_power_range.connect(self.on_auto_power_range_change)
        self.interface.sig_power_range.connect(self.on_power_range_change)
        self.interface.sig_close.connect(self.on_close)

        ### SET INITIAL STATE OF WIDGETS
        self.edit_RefreshTime.setText(f"{self.interface.settings['refresh_time']:.3f}")
        self.interface.send_list_devices()  
        self.on_connection_status_change(self.interface.SIG_DISCONNECTED) #When GUI is created, all widgets are set to the "Disconnected" state              
        ###

    def create_widgets(self):
        """
        Creates all widgets and layout for the GUI. Any Widget and Layout must assigned to self.containter, which is a pyqt Layout object
        """ 
        self.container = Qt.QVBoxLayout()

        #Use the custom connection/listdevices panel, defined in abstract_instrument_interface.abstract_gui
        hbox1, widgets_dict = self.create_panel_connection_listdevices()
        for key, val in widgets_dict.items(): 
            setattr(self,key,val) 

        hbox2 = Qt.QHBoxLayout()
        self.button_StartPauseReading = Qt.QPushButton("")
        self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))
        self.button_StartPauseReading.setToolTip('Start or pause the reading from the powermeter. The previous data points are not discarded when pausing.') 
        self.button_StopReading = Qt.QPushButton("")
        self.button_StopReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'stop.png')))
        self.button_StopReading.setToolTip('Stop the reading from the powermeter. All previous data points are discarded.') 
        self.label_RefreshTime = Qt.QLabel("Refresh time (s): ")
        self.label_RefreshTime.setToolTip('Specifies how often the power is read from the powermeter (Minimum value = 0.001 s).') 
        self.label_RefreshTime.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.edit_RefreshTime  = Qt.QLineEdit()
        self.edit_RefreshTime.setToolTip('Specifies how often the power is read from the powermeter (Minimum value = 0.001 s).') 
        self.edit_RefreshTime.setAlignment(QtCore.Qt.AlignRight)
        self.edit_RefreshTime.setMaximumWidth(120)  
        font = QtGui.QFont("Times", 12,QtGui.QFont.Bold)
        self.label_Power = Qt.QLabel("Power: ")
        self.label_Power.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.label_Power.setFont(font)
        self.edit_Power = Qt.QLineEdit()
        self.edit_Power.setFont(font)
        self.edit_Power.setAlignment(QtCore.Qt.AlignRight)
        self.edit_Power.setReadOnly(True)
        #self.edit_Power.setMaximumWidth(150)    
        self.button_SetZeroPowermeter = Qt.QPushButton("Set Zero")  
        self.button_ShowHidePlot = Qt.QPushButton("Show/Hide Plot")
        self.button_ShowHidePlot.setToolTip('Show/Hide Plot.')

        widgets_row2 = [self.button_StartPauseReading,self.button_StopReading,self.button_SetZeroPowermeter,self.label_RefreshTime,self.edit_RefreshTime,self.label_Power,self.edit_Power,self.button_ShowHidePlot]
        widgets_row2_stretches = [0]*len(widgets_row2)
        for w,s in zip(widgets_row2,widgets_row2_stretches):
            hbox2.addWidget(w,stretch=s)
        hbox2.addStretch(1)

        if not self.plot_object:
            self.button_ShowHidePlot.hide()
            self.button_StopReading.hide()

        hbox3 = Qt.QHBoxLayout()
        self.label_Wavelength = Qt.QLabel("Wavelength: ")
        #self.label_Wavelength.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.edit_Wavelength = Qt.QLineEdit()
        self.edit_Wavelength.setAlignment(QtCore.Qt.AlignRight)
        self.edit_Wavelength.setMaximumWidth(150) 
        self.label_WavelengthUnits = Qt.QLabel("nm")
        self.label_PowerRange = Qt.QLabel("Power range: ")
        self.button_DecreasePowerRange = Qt.QPushButton("<")
        self.button_DecreasePowerRange.setToolTip('Decrease the powermeter power range.')
        self.button_DecreasePowerRange.setMaximumWidth(25)       
        self.edit_PowerRange = Qt.QLineEdit()
        self.edit_PowerRange.setToolTip('Maximum power measurable in the current power range (unless \'Auto\' is checked).')
        self.edit_PowerRange.setReadOnly(True)
        self.edit_PowerRange.setMaximumWidth(150) 
        self.button_IncreasePowerRange = Qt.QPushButton(">")
        self.button_IncreasePowerRange.setToolTip('Increase the powermeter power range.')
        self.button_IncreasePowerRange.setMaximumWidth(25)
        self.box_PowerRangeAuto = Qt.QCheckBox("Auto")
        self.box_PowerRangeAuto.setToolTip('Set the power range of the powermeter to Automatic.')
        widgets_row3 = [self.label_Wavelength,self.edit_Wavelength,self.label_WavelengthUnits,self.label_PowerRange,
                        self.button_DecreasePowerRange,self.edit_PowerRange,self.button_IncreasePowerRange,self.box_PowerRangeAuto]
        widgets_row3_stretches = [0]*len(widgets_row3)
        for w,s in zip(widgets_row3,widgets_row3_stretches):
            hbox3.addWidget(w,stretch=s)
        hbox3.addStretch(1)
  
        for box in [hbox1,hbox2,hbox3]:
            self.container.addLayout(box)  
        self.container.addStretch(1)

        # Widgets for which we want to constraint the width by using sizeHint()
        widget_list = [self.button_StopReading,self.label_RefreshTime,self.label_Power,self.button_SetZeroPowermeter,self.label_WavelengthUnits,self.label_PowerRange,self.box_PowerRangeAuto]
        for w in widget_list:
            w.setMaximumSize(w.sizeHint())

        self.widgets_enabled_when_connected = [self.button_SetZeroPowermeter,self.edit_Wavelength,self.edit_PowerRange,self.box_PowerRangeAuto, 
                                               self.button_IncreasePowerRange,self.button_DecreasePowerRange,self.button_StartPauseReading,self.button_StopReading]
        self.widgets_enabled_when_disconnected = [self.combo_Devices,self.button_RefreshDeviceList]

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

###########################################################################################################
### Event Slots. They are normally triggered by signals from the model, and change the GUI accordingly  ###
###########################################################################################################

    def on_connection_status_change(self,status):
        if status == self.interface.SIG_DISCONNECTED:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.edit_PowerRange.setText('')
            self.edit_Wavelength.setText('')
            self.label_Wavelength.setText(f"Wavelength: ")
            self.button_ConnectDevice.setText("Connect")
            self.edit_Power.setText('')
        if status == self.interface.SIG_DISCONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnecting...")
        if status == self.interface.SIG_CONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Connecting...")
        if status == self.interface.SIG_CONNECTED:
            self.enable_widget(self.widgets_enabled_when_connected)
            self.disable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnect")
            #If a self.plot_object was created, update window title with powermeter name and vertical axis of plot with current Power units
            if self.plot_object: 
                self.plot_object.graphWidget.setLabel("left", f"Power [{self.interface.instrument._power_units}]")
                self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")

    def on_reading_status_change(self,status):
        if status == self.interface.SIG_READING_PAUSE:
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))
        if status == self.interface.SIG_READING_START:
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'pause.png')))
        if status == self.interface.SIG_READING_STOP: 
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))

    def on_list_devices_updated(self,list_devices):
        self.combo_Devices.clear()  #First we empty the combobox  
        self.combo_Devices.addItems(list_devices) 

    def on_data_change(self,data):
        #Data is (in this case) a string
        current_power_string = f"{data[0]:.2e}" + ' ' +  data[1]
        self.edit_Power.setText(current_power_string)
        if self.plot_object:
            self.plot_object.data.setData(list(range(1, len(self.interface.stored_data)+1)), self.interface.stored_data) #This line is executed even when self.continuous_read == False, to make sure that plot gets cleared when user press the stop button
        
    def on_refreshtime_change(self,value):
        self.edit_RefreshTime.setText(f"{value:.3f}")

    def on_wavelength_change(self,value):
        self.edit_Wavelength.setText(str(int(value)))

    def on_min_max_wavelength_update(self,min,max):
        self.label_Wavelength.setText(f"Wavelength<br>(<b>{min}-{max}</b>): ")
    
    def on_power_range_change(self,value):
        self.edit_PowerRange.setText(f"{value:.2e}")
        self.edit_PowerRange.setCursorPosition(1)

    def on_auto_power_range_change(self,value):
        self.set_auto_power_range_state(value)
        self.box_PowerRangeAuto.setChecked(value)

    def on_close(self):
        if hasattr(self,'plot_window'):
            if self.plot_window:
                self.plot_window.close()

    def set_auto_power_range_state(self,auto_power_range):
        if auto_power_range:
            self.disable_widget([self.edit_PowerRange,self.button_IncreasePowerRange, self.button_DecreasePowerRange])
        else:
            self.enable_widget([self.edit_PowerRange,self.button_IncreasePowerRange, self.button_DecreasePowerRange])

#######################
### END Event Slots ###
#######################

            
###################################################################################################################################################
### GUI Events Functions. They are triggered by direct interaction with the GUI, and they call methods of the interface (i.e. the model) object.###
###################################################################################################################################################

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
            if not(self.press_enter_refresh_time()): #read the current value in the refresh_time textbox, and validates it. The function returns True/False if refresh_time was valid
                return
            if not(self.press_enter_wavelength()): #read the current value in the wavelength textbox, and validates it. The function returns True/False if refresh_time was valid
                return
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

#################################
### END GUI Events Functions ####
#################################

    def create_plot(self):
        '''
        This function creates an additional (separated) window with a pyqtgraph object, which plots the contents of self.stored_data
        '''
        self.plot_window = Qt.QWidget() #This is the widget that will contain the plot. Since it does not have a parent, the plot will be in a floating (separated) window
        self.plot_object = PlotObject(self.interface.app, self.plot_window)
        styles = {"color": "#fff", "font-size": "20px"}
        self.plot_object.graphWidget.setLabel("left", "Power", **styles)
        self.plot_object.graphWidget.setLabel("bottom", "Acqusition #", **styles)
        self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")
        self.plot_window.show()
        self.plot_window.setHidden(True)
            
#################################################################################################

class MainWindow(Qt.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(__package__)

    def closeEvent(self, event):
        #if self.child:
        pass#self.child.close()

#################################################################################################

def main():
    parser = argparse.ArgumentParser(description = "",epilog = "")
    parser.add_argument("-s", "--decrease_verbose", help="Decrease verbosity.", action="store_true")
    parser.add_argument('-virtual', help=f"Initialize the virtual driver", action="store_true")
    args = parser.parse_args()
    virtual = args.virtual
    
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    Interface = interface(app=app,virtual=virtual) 
    Interface.verbose = not(args.decrease_verbose)
    app.aboutToQuit.connect(Interface.close) 
    view = gui(interface = Interface, parent=window,plot=True) #In this case window is the parent of the gui
    window.show()
    app.exec()# Start the event loop.

if __name__ == '__main__':
    main()

#################################################################################################
