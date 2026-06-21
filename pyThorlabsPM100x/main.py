''' Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes'''

import os
import PyQt5
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
import PyQt5.QtWidgets as Qt  # QApplication, QWidget, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import logging
import sys
import argparse

import abstract_instrument_interface
import pyThorlabsPM100x.driver
from pyThorlabsPM100x.plots import PlotObject

graphics_dir = os.path.join(os.path.dirname(__file__), 'graphics')

##This application follows the model-view-controller paradigm, but with the view and controller defined inside the same object (the GUI)
##The model is defined by the class 'interface', and the view+controller is defined by the class 'gui'. 

class interface(abstract_instrument_interface.abstract_interface):
    """
    High-level model for the Thorlabs PM100x powermeter, built on top of
    :class:`abstract_instrument_interface.abstract_interface`.

    Wraps a :class:`~pyThorlabsPM100x.driver.ThorlabsPM100x` driver instance,
    validates user input, periodically reads power from the device, and exposes
    its state via Qt signals. Follows the model-view-controller pattern: this class
    is the model, and :class:`gui` is the view/controller.

    Class-level attributes
    ----------------------
    output : dict
        Produced data. Key ``'Power'`` holds the most recently read power value (float).
        Initialized to ``{'Power': 0}``.

    Signals
    -------
    sig_list_devices_updated : pyqtSignal(list)
        Emitted when the list of available devices is refreshed. Carries the list of
        device name strings shown in the GUI combo box.
    sig_reading : pyqtSignal(int)
        Emitted when the reading status changes. Parameter is one of
        ``SIG_READING_START``, ``SIG_READING_PAUSE``, or ``SIG_READING_STOP``.
    sig_updated_data : pyqtSignal(object)
        Emitted each time a new power value is read. Carries ``[power, units]``.
    sig_wavelength : pyqtSignal(int)
        Emitted when the operating wavelength changes. Carries the new wavelength in nm.
    sig_min_max_wavelength : pyqtSignal(int, int)
        Emitted after reading the wavelength range from the device. Carries
        ``(min_wavelength, max_wavelength)`` in nm.
    sig_refreshtime : pyqtSignal(float)
        Emitted when the refresh time setting changes. Carries the new value in seconds.
    sig_power_range : pyqtSignal(float)
        Emitted when the power range changes. Carries the new power range value.
    sig_auto_power_range : pyqtSignal(bool)
        Emitted when the auto power range status changes. Carries the new boolean status.

    Status codes
    ------------
    SIG_READING_START : int (= 1)
        Reading has started (continuous acquisition is active).
    SIG_READING_PAUSE : int (= 2)
        Reading has been paused (accumulated data are preserved).
    SIG_READING_STOP : int (= 3)
        Reading has been stopped and all accumulated data cleared.

    Instance attributes
    -------------------
    instrument : ThorlabsPM100x
        The low-level driver instance used to communicate with the device.
    connected_device_name : str
        VISA address of the currently connected device, or empty string if disconnected.
    continuous_read : bool
        When ``True``, :meth:`update` reads power continuously at the rate set by
        ``settings['refresh_time']``.
    stored_data : list of float
        Power values accumulated since the last :meth:`start_reading` or
        :meth:`stop_reading`.
    power_units : str
        Power units reported by the device (e.g. ``'W'``). Set upon connection.
    wavelength : int
        Most recently read operating wavelength, in nm.
    power_range : float
        Most recently read power range value.
    min_max_wls : (int, int)
        Cached ``(min_wavelength, max_wavelength)`` tuple, in nm.
    settings : dict
        ``'refresh_time'`` (float, seconds) and ``'auto_power_range'`` (bool).
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
        '''
        Parameters
        ----------
        **kwargs
            Forwarded to :class:`~abstract_instrument_interface.abstract_interface`.
            Required key: ``app`` (``Qt.QApplication``). Optional keys include
            ``name_logger`` (str), ``config_dict`` (dict), and ``virtual`` (bool).
            Pass ``virtual=True`` to use the simulated driver instead of real hardware.
        '''
        self.output = {'Power':0} 
        ### Default values of settings (might be overwritten by settings saved in .json files later)
        self.settings = {   'refresh_time': 0.2,
                            'auto_power_range': True
                            }
        
        self.list_devices = []          #list of devices found 
        self.connected_device_name = ''
        self.continuous_read = False    # When this is set to True, the data from device are acquired continuously at the rate set by self.refresh_time
        self.stored_data = []           # List used to store data acquired by device
        ###
        virtual = kwargs.get('virtual', False)
        self.instrument = pyThorlabsPM100x.driver.ThorlabsPM100x(virtual=virtual)
        ###
        super().__init__(**kwargs)
        self.refresh_list_devices()   
        
    def refresh_list_devices(self):
        '''
        Scan for available devices using the driver, update :attr:`list_devices`, and
        emit :attr:`sig_list_devices_updated` to refresh the GUI combo box.
        '''     
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices() #Then we read the list of devices
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 
        self.list_devices = list_valid_devices
        self.send_list_devices()

    def send_list_devices(self):
        '''
        Emit :attr:`sig_list_devices_updated` with the current device list formatted
        as ``"<idn> --> <address>"`` strings, ready to populate the GUI combo box.
        If no devices are found, an empty list is emitted.
        '''
        if(len(self.list_devices)>0):
            list_IDNs_and_devices = [dev[1] + " --> " + dev[0] for dev in self.list_devices] 
        else:
            list_IDNs_and_devices = []
        self.sig_list_devices_updated.emit(list_IDNs_and_devices)

    def connect_device(self,device_full_name):
        '''
        Connect to the device identified by ``device_full_name``.

        Parameters
        ----------
        device_full_name : str
            A string of the form ``"<idn> --> <address>"``, as produced by
            :meth:`send_list_devices` and displayed in the GUI combo box. The VISA
            address is extracted from the part after ``" --> "``. If empty, or if it
            does not contain the ``" --> "`` separator, an error is logged and the
            method returns immediately.

        Notes
        -----
        On success, calls :meth:`set_connected_state`, which reads the current
        wavelength, power range, and auto-ranging status, and starts continuous reading.
        On failure, calls :meth:`set_disconnected_state` and logs an error.
        '''
        if(device_full_name==''):
            self.logger.error("No valid device has been selected.")
            return
        self.set_connecting_state()
        try:
            device_name = device_full_name.split(' --> ')[1].lstrip()   # We extract the device address from the device name
        except IndexError:
            self.logger.error(f"Invalid device identifier: {device_full_name!r}")
            self.set_disconnected_state()
            return
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
        '''
        Disconnect the currently connected device.

        Calls the driver's :meth:`~pyThorlabsPM100x.driver.ThorlabsPM100x.disconnect_device`,
        stops continuous reading, and emits :attr:`sig_connected` with
        :attr:`~abstract_instrument_interface.abstract_interface.SIG_DISCONNECTED`.
        If disconnection fails (e.g. the device was already physically unplugged), the
        disconnected state is still set so the GUI resets correctly.
        '''
        self.logger.info(f"Disconnecting from device {self.connected_device_name}...")
        (Msg,ID) = self.instrument.disconnect_device()
        if(ID==1): # If disconnection was successful
            self.logger.info(f"Disconnected from device {self.connected_device_name}.")
            self.continuous_read = False # We set this variable to False so that the continuous reading from the powermeter will stop
            self.set_disconnected_state()
        else: #If disconnection was not successful
            self.logger.error(f"Error: {Msg}")
            self.set_disconnected_state() #When disconnection is not successful, it is typically because the device already lost connection
                                          #for some reason. In this case, it is still useful to have all widgets reset to disconnected state      
    def close(self,**kwargs):
        '''
        Close this interface. Delegates entirely to the parent class
        :meth:`~abstract_instrument_interface.abstract_interface.close`, which emits
        :attr:`~abstract_instrument_interface.abstract_interface.sig_close`, saves
        settings, and disconnects the device if connected.
        '''
        super().close(**kwargs)           

    def set_connected_state(self):
        '''
        Extend the parent
        :meth:`~abstract_instrument_interface.abstract_interface.set_connected_state`
        to perform PM100x-specific initialization after a successful connection.

        In addition to emitting :attr:`sig_connected` with ``SIG_CONNECTED``, this
        method caches the power units, reads and emits the wavelength range and current
        wavelength, applies the auto power range setting from :attr:`settings`, and
        starts continuous reading via :meth:`start_reading`.
        '''
        super().set_connected_state()
        self.power_units = self.instrument.power_units
        self.read_min_max_wavelength()
        self.read_wavelength()
        #self.read_status_power_autorange()
        self.set_auto_power_range(self.settings['auto_power_range'])
        #self.read_power_range()
        self.start_reading()

    def set_refresh_time(self, refresh_time):
        '''
        Validate and apply a new refresh time.

        Parameters
        ----------
        refresh_time : str or float
            Desired refresh time in seconds. Must be convertible to ``float`` and
            be >= 0.001 s.

        Returns
        -------
        bool
            ``True`` if the value was accepted (or was already set to this value),
            ``False`` if it was invalid. On failure, :attr:`sig_refreshtime` is emitted
            with the current (unchanged) value so the GUI can revert.
        '''
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
        '''
        Validate and set the operating wavelength of the connected device.

        Parameters
        ----------
        wl : str, int, or float
            Desired wavelength in nm. Must be convertible to ``int`` and within the
            ``[min_wavelength, max_wavelength]`` range supported by the connected head.

        Returns
        -------
        bool
            ``True`` if the wavelength was accepted, ``False`` otherwise. On failure,
            :attr:`sig_wavelength` is emitted with the current instrument wavelength
            so the GUI can revert the text box.

        Notes
        -----
        After a successful wavelength change, :meth:`read_power_range` is called
        because the available power ranges may change with wavelength.
        '''
        try:
            if int(self.instrument.wavelength) == int(float(wl)): #in this case the number in the refresh time edit box is the same as the wavelength currently set
                    return True
            self.logger.info(f"Setting the wavelength to {wl} for the device {self.connected_device_name}...")
        except (ValueError,TypeError) as e:
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
        '''
        Read the current operating wavelength from the device, cache it in
        :attr:`wavelength`, and emit :attr:`sig_wavelength`.

        If reading the wavelength fails (e.g. the device got disconnected), an
        error is logged and the method returns without emitting.
        '''
        self.logger.info(f"Reading current wavelength from device {self.connected_device_name}...")
        try:
            wl = self.instrument.wavelength
        except RuntimeError as e:
            self.logger.error(f"An error occurred while reading the wavelength from this device: {e}")
            return
        self.wavelength = int(wl)
        self.sig_wavelength.emit(self.instrument.wavelength)
        self.logger.info(f"Current wavelength is {self.wavelength}.") 
        return
      
    def read_min_max_wavelength(self):
        '''
        Read the wavelength range supported by the connected powermeter head from
        the driver's cached attributes and emit :attr:`sig_min_max_wavelength`.

        The result is cached in :attr:`min_max_wls` as ``(min_wavelength, max_wavelength)``.
        Note: this reads from the driver's already-cached values (set at connection by
        :meth:`~pyThorlabsPM100x.driver.ThorlabsPM100x.read_min_max_wavelength`); it
        does not re-query the instrument.
        '''
        self.logger.info(f"Reading min and max wavelength supported by device {self.connected_device_name}...") 
        self.min_max_wls =  (self.instrument.min_wavelength,self.instrument.max_wavelength)
        self.sig_min_max_wavelength.emit(self.min_max_wls[0],self.min_max_wls[1])
        self.logger.info(f"Wavelength range: {self.min_max_wls[0]}-{self.min_max_wls[1]} nm") 

    def change_power_range(self,direction):
        '''
        Increase or decrease the power range by one step, then read and emit the new range.

        Parameters
        ----------
        direction : int
            ``+1`` to increase the power range, ``-1`` to decrease it. Forwarded
            directly to
            :meth:`~pyThorlabsPM100x.driver.ThorlabsPM100x.move_to_next_power_range`.
        '''
        if direction == +1:
            string = 'increase'
        else: 
            string = 'decrease'
        self.logger.info(f"Trying to {string} the power range...")
        self.instrument.move_to_next_power_range(direction)
        self.read_power_range()
        return

    def read_power_range(self):
        '''
        Read the current power range from the device, cache it in :attr:`power_range`,
        and emit :attr:`sig_power_range`.

        If reading the power range fails (e.g. the device got disconnected), an
        error is logged and the method returns without emitting.
        '''
        self.logger.info(f"Reading current power range from device {self.connected_device_name}...")
        try:
            pow_range = self.instrument.power_range
        except RuntimeError as e:
            self.logger.error(f"An error occurred while reading the power range from this device: {e}")
            return
        self.power_range = pow_range
        self.sig_power_range.emit(self.power_range)
        self.logger.info(f"Current power range is {self.power_range}.") 

    def set_auto_power_range(self,auto_power_range):
        '''
        Enable or disable the automatic power-ranging mode of the connected device.

        Parameters
        ----------
        auto_power_range : bool
            ``True`` to enable auto-ranging, ``False`` to disable it.

        Notes
        -----
        On success, updates ``settings['auto_power_range']`` and emits
        :attr:`sig_auto_power_range`. Regardless of success, :meth:`read_power_range`
        is called afterwards to update the displayed power range value.
        '''
        auto_power_range = bool(auto_power_range)
        status_string = 'ON' if auto_power_range else 'OFF'
        self.logger.info(f"Setting the auto-ranging function to {status_string} for the device {self.connected_device_name}...")    
        try:
            self.instrument.auto_power_range  = auto_power_range
            self.sig_auto_power_range.emit(auto_power_range)
            self.logger.info(f"Setting changed successfully.")
            self.settings['auto_power_range'] = auto_power_range
        except Exception as e:
            self.logger.error(f"An error occurred while setting the auto-ranging status: {e}")
        #self.read_auto_power_range()
        self.read_power_range()

    def read_auto_power_range(self):
        '''
        Read the current auto power range status from the device, update
        ``settings['auto_power_range']``, and emit :attr:`sig_auto_power_range`.

        Returns
        -------
        bool or None
            The current auto power range status, or ``None`` if an error occurred.
        '''
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
        '''
        Trigger the zeroing routine of the connected device via the driver's
        :meth:`~pyThorlabsPM100x.driver.ThorlabsPM100x.set_zero`. Logs success or
        failure. During zeroing,
        :attr:`~pyThorlabsPM100x.driver.ThorlabsPM100x.being_zeroed` is set, which
        causes :attr:`~pyThorlabsPM100x.driver.ThorlabsPM100x.power` to return
        ``(None, '')`` rather than querying the instrument.
        '''
        try: 
            ID = self.instrument.set_zero()
            self.logger.info(f"Zero-ing the device {self.connected_device_name}...")
            if ID == 1:
                self.logger.info(f"Device was successfully zeroed.")
            else:
                self.logger.error(f"An error occurred while zero-ing this device.")
        except Exception as e:
            self.logger.error(f"An error occurred while zero-ing this device: {e}")
        return

    def start_reading(self):
        '''
        Begin continuous power acquisition from the connected device.

        Sets :attr:`continuous_read` to ``True`` and emits :attr:`sig_reading` with
        :attr:`SIG_READING_START`, then calls :meth:`update` which reschedules itself
        via ``QTimer.singleShot`` at the interval set by ``settings['refresh_time']``
        until :attr:`continuous_read` becomes ``False``. Has no effect if no device
        is connected.
        '''
        if(self.instrument.connected == False):
            self.logger.error(f"No device is connected.")
            return
        #self.logger.info(f"Updating wavelength and refresh time before starting reading...")       
        self.sig_reading.emit(self.SIG_READING_START) # This signal will be caught by the GUI
        self.continuous_read = True #Until this variable is set to True, the function UpdatePower will be repeated continuously 
        self.logger.info(f"Starting reading from device {self.connected_device_name}...")
        # Call the function self.update(), which will read the power, store it in a global variable, and then call itself continuously until the variable self.continuous_read is set to False
        self.update()
        return
 
    def pause_reading(self):
        '''
        Pause continuous power acquisition without discarding accumulated data.

        Sets :attr:`continuous_read` to ``False`` (stopping the :meth:`update` loop)
        and emits :attr:`sig_reading` with :attr:`SIG_READING_PAUSE`. The contents
        of :attr:`stored_data` are preserved and the plot is not cleared.
        '''
        #Sets self.continuous_read to False (this will force the function update() to stop calling itself)
        self.continuous_read = False
        self.logger.info(f"Paused reading from device {self.connected_device_name}.")
        self.sig_reading.emit(self.SIG_READING_PAUSE) # This signal will be caught by the GUI
        return

    def stop_reading(self):
        '''
        Stop continuous power acquisition and clear all accumulated data.

        Sets :attr:`continuous_read` to ``False``, clears :attr:`stored_data`, calls
        :meth:`update` once more to push an empty dataset to the plot (so the plot is
        visually cleared), then emits :attr:`sig_reading` with :attr:`SIG_READING_PAUSE`.
        '''
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
        Read power from the device and reschedule itself.

        If :attr:`continuous_read` is ``True``, this method:

        1. Reads ``(power, units)`` from the instrument and stores the power value in
           ``self.output['Power']`` and appends it to :attr:`stored_data`.
        2. Calls ``super().update()`` (defined in
           :class:`~abstract_instrument_interface.abstract_interface`), which fires any
           configured trigger via :meth:`~abstract_instrument_interface.abstract_interface.send_trigger`.
        3. Emits :attr:`sig_updated_data` with ``[power, units]`` (intercepted by the
           GUI to update the power display and live plot).
        4. Schedules another call to :meth:`update` after ``settings['refresh_time']``
           seconds via ``QTimer.singleShot``.

        If :attr:`continuous_read` is ``False``, the method returns immediately without
        querying the instrument or rescheduling itself. It is still safe to call in this
        state (e.g. :meth:`stop_reading` calls it once to trigger a final plot refresh).
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
    """
    PyQt5 view/controller for the Thorlabs PM100x interface.

    Inherits from :class:`~abstract_instrument_interface.abstract_gui`. Builds the
    instrument panel (connection row, reading controls, wavelength and power-range row)
    and optionally a separate floating plot window. Wires widget events to
    :class:`interface` methods and connects :class:`interface` signals to event slots
    that update the widgets.

    Instance attributes
    -------------------
    plot_window : Qt.QWidget or None
        Floating widget that contains the live power plot, or ``None`` if
        ``plot=False`` was passed to the constructor.
    plot_object : PlotObject or None
        The :class:`~pyThorlabsPM100x.plots.PlotObject` instance used for live
        plotting, or ``None`` if ``plot=False``.
    widgets_enabled_when_connected : list of Qt.QWidget
        Widgets enabled only while a device is connected (zero button, wavelength
        edit, power range controls, start/stop buttons).
    widgets_enabled_when_disconnected : list of Qt.QWidget
        Widgets enabled only while no device is connected (device combo box and
        refresh button).
    """

    def __init__(self,interface,parent,plot=False):
        """
        Parameters
        ----------
        interface : interface
            The :class:`interface` (model) object this GUI controls.
        parent : Qt.QWidget
            The Qt widget that will host this GUI panel.
        plot : bool, optional
            If ``True`` (default ``False``), create a floating plot window with a
            live power-vs-acquisition-number chart and show the "Show/Hide Plot"
            and "Stop" buttons. If ``False``, those buttons are hidden.
        """
        super().__init__(interface,parent)
        self.plot_window = None # QWidget object of the widget (i.e. floating window) that will contain the plot
        self.plot_object = None # PlotObject object of the plot where self.store_powers is plotted

        if plot:        # Create a plot object
            self.create_plot() 
        self.initialize()

    def initialize(self):
        '''
        Build the full GUI: create widgets, wire events, attach to parent, and connect
        all model signals to their event slots.

        Called automatically by :meth:`__init__`. Specifically:

        1. Calls :meth:`create_widgets` to instantiate and lay out all Qt widgets.
        2. Calls :meth:`connect_widgets_events_to_functions` to wire button clicks,
           text edits, and checkbox toggles to the corresponding handler methods.
        3. Calls ``super().initialize()`` to set the parent widget's layout and resize it.
        4. Connects all signals emitted by :attr:`interface` to the event slot methods
           of this GUI.
        5. Sets the initial widget state to "disconnected".
        '''
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
        Creates all widgets and layout for the GUI. Every widget and layout must be assigned to self.container, which is a PyQt5 layout object.
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
        '''
        Wire all widget signals (button clicks, text edits, checkbox state changes) to
        their corresponding GUI event handler methods. Called once by :meth:`initialize`.
        '''
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
        '''
        Event slot connected to :attr:`interface.sig_connected`.

        Updates button labels, clears text boxes, and enables/disables widget groups
        to reflect the current connection state (disconnected, connecting, connected,
        or disconnecting).

        Parameters
        ----------
        status : int
            One of ``SIG_CONNECTED``, ``SIG_DISCONNECTED``, ``SIG_CONNECTING``, or
            ``SIG_DISCONNECTING``.
        '''
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
                self.plot_object.graphWidget.setLabel("left", f"Power [{self.interface.power_units}]")
                self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")

    def on_reading_status_change(self,status):
        '''
        Event slot connected to :attr:`interface.sig_reading`.

        Updates the start/pause button icon to reflect the current reading state:
        a "pause" icon while reading is active, a "play" icon when paused or stopped.

        Parameters
        ----------
        status : int
            One of ``SIG_READING_START``, ``SIG_READING_PAUSE``, or ``SIG_READING_STOP``.
        '''
        if status == self.interface.SIG_READING_PAUSE:
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))
        if status == self.interface.SIG_READING_START:
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'pause.png')))
        if status == self.interface.SIG_READING_STOP: 
            self.button_StartPauseReading.setIcon(QtGui.QIcon(os.path.join(graphics_dir,'play.png')))

    def on_list_devices_updated(self,list_devices):
        '''
        Event slot connected to :attr:`interface.sig_list_devices_updated`.

        Clears and repopulates the device combo box with the new list of device strings.

        Parameters
        ----------
        list_devices : list of str
            Device name strings in the format ``"<idn> --> <address>"``.
        '''
        self.combo_Devices.clear()  #First we empty the combobox  
        self.combo_Devices.addItems(list_devices) 

    def on_data_change(self,data):
        '''
        Event slot connected to :attr:`interface.sig_updated_data`.

        Updates the power display text box and, if a plot exists, updates the live
        plot with the full contents of :attr:`interface.stored_data`.

        Parameters
        ----------
        data : list
            ``[power, units]`` as emitted by :attr:`interface.sig_updated_data`.
        '''
        #Data is (in this case) a list [power, units]
        current_power_string = f"{data[0]:.2e}" + ' ' +  data[1]
        self.edit_Power.setText(current_power_string)
        if self.plot_object:
            self.plot_object.data.setData(list(range(1, len(self.interface.stored_data)+1)), self.interface.stored_data) #This line is executed even when self.continuous_read == False, to make sure that plot gets cleared when user press the stop button
        
    def on_refreshtime_change(self,value):
        '''
        Event slot connected to :attr:`interface.sig_refreshtime`.

        Updates the refresh time text box to reflect the validated value stored
        in the model.

        Parameters
        ----------
        value : float
            New refresh time in seconds.
        '''
        self.edit_RefreshTime.setText(f"{value:.3f}")

    def on_wavelength_change(self,value):
        '''
        Event slot connected to :attr:`interface.sig_wavelength`.

        Updates the wavelength text box to reflect the current instrument wavelength.

        Parameters
        ----------
        value : int
            Current operating wavelength in nm.
        '''
        self.edit_Wavelength.setText(str(int(value)))

    def on_min_max_wavelength_update(self,min,max):
        '''
        Event slot connected to :attr:`interface.sig_min_max_wavelength`.

        Updates the wavelength label to display the supported wavelength range in bold.

        Parameters
        ----------
        min : int
            Minimum supported wavelength in nm.
        max : int
            Maximum supported wavelength in nm.
        '''
        self.label_Wavelength.setText(f"Wavelength<br>(<b>{min}-{max}</b>): ")
    
    def on_power_range_change(self,value):
        '''
        Event slot connected to :attr:`interface.sig_power_range`.

        Updates the power range text box with the new value formatted in scientific
        notation, and resets the cursor to position 1.

        Parameters
        ----------
        value : float
            New power range value (maximum measurable power in the current range).
        '''
        self.edit_PowerRange.setText(f"{value:.2e}")
        self.edit_PowerRange.setCursorPosition(1)

    def on_auto_power_range_change(self,value):
        '''
        Event slot connected to :attr:`interface.sig_auto_power_range`.

        Updates the auto-range checkbox state and enables/disables the manual power
        range controls accordingly via :meth:`set_auto_power_range_state`.

        Parameters
        ----------
        value : bool
            ``True`` if auto power ranging is now enabled, ``False`` otherwise.
        '''
        self.set_auto_power_range_state(value)
        self.box_PowerRangeAuto.setChecked(value)

    def on_close(self):
        '''
        Event slot connected to :attr:`interface.sig_close`.

        Closes the floating plot window (if one exists) when the interface is closed.
        '''
        if hasattr(self,'plot_window'):
            if self.plot_window:
                self.plot_window.close()

    def set_auto_power_range_state(self,auto_power_range):
        '''
        Enable or disable the manual power range widgets based on the auto-ranging state.

        When ``auto_power_range`` is ``True``, the power range text box and the
        increase/decrease buttons are disabled (since the instrument controls the range
        automatically). When ``False``, they are re-enabled.

        Parameters
        ----------
        auto_power_range : bool
            ``True`` if auto power ranging is active, ``False`` otherwise.
        '''
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
        '''Refresh the device list by calling :meth:`interface.refresh_list_devices`.'''
        self.interface.refresh_list_devices()

    def click_button_connect_disconnect(self):
        '''
        Toggle the connection state of the instrument.

        If the instrument is currently disconnected, reads the selected device name
        from the combo box and calls :meth:`interface.connect_device`. If currently
        connected, calls :meth:`interface.disconnect_device`.
        '''
        if(self.interface.instrument.connected == False): # We attempt connection   
            device_full_name = self.combo_Devices.currentText() # Get the device name from the combobox
            self.interface.connect_device(device_full_name)
        elif(self.interface.instrument.connected == True): # We attempt disconnection
            self.interface.disconnect_device()

    def click_box_PowerRangeAuto(self, state):
        '''
        Handler for the "Auto" power range checkbox state change.

        Converts the Qt check state to a boolean and calls
        :meth:`interface.set_auto_power_range`.

        Parameters
        ----------
        state : Qt.CheckState
            The new state of the checkbox (``Qt.Checked`` or ``Qt.Unchecked``).
        '''
        if state == QtCore.Qt.Checked:
            status_bool = True
        else:
            status_bool = False
        self.interface.set_auto_power_range(status_bool)

    def click_button_set_zero_powermeter(self):
        '''Handler for the "Set Zero" button. Calls :meth:`interface.set_zero_powermeter`.'''
        self.interface.set_zero_powermeter()

    def press_enter_wavelength(self):
        '''
        Handler for the wavelength text box (Return pressed).

        Reads the current text and calls :meth:`interface.set_wavelength`.

        Returns
        -------
        bool
            ``True`` if the wavelength was accepted, ``False`` otherwise.
        '''
        return self.interface.set_wavelength(self.edit_Wavelength.text())
        
    def click_button_change_power_range(self,direction):
        '''
        Handler for the "<" and ">" power range buttons.

        Parameters
        ----------
        direction : int
            ``-1`` to decrease the power range, ``+1`` to increase it.
        '''
        self.interface.change_power_range(direction)
       
    def click_button_StartPauseReading(self): 
        '''
        Handler for the start/pause reading button.

        If reading is not active, validates the refresh time and wavelength text
        boxes first, then calls :meth:`interface.start_reading`. If reading is
        already active, calls :meth:`interface.pause_reading`.
        '''
        if(self.interface.continuous_read == False):
            if not(self.press_enter_refresh_time()): #read the current value in the refresh_time textbox, and validates it. The function returns True/False if refresh_time was valid
                return
            if not(self.press_enter_wavelength()): #read the current value in the wavelength textbox, and validates it. The function returns True/False if wavelength was valid
                return
            self.interface.start_reading()
        elif (self.interface.continuous_read == True):
            self.interface.pause_reading()
        return

    def click_button_StopReading(self):
        '''Handler for the stop reading button. Calls :meth:`interface.stop_reading`.'''
        self.interface.stop_reading()

    def press_enter_refresh_time(self):
        '''
        Handler for the refresh time text box (Return pressed).

        Reads the current text and calls :meth:`interface.set_refresh_time`.

        Returns
        -------
        bool
            ``True`` if the refresh time was accepted, ``False`` otherwise.
        '''
        return self.interface.set_refresh_time(self.edit_RefreshTime.text())

    def click_button_ShowHidePlot(self):
        '''Handler for the "Show/Hide Plot" button. Toggles the visibility of the plot window.'''
        self.plot_window.setHidden(not self.plot_window.isHidden())

#################################
### END GUI Events Functions ####
#################################

    def create_plot(self):
        '''
        Create a separate floating window containing a live pyqtgraph plot of
        :attr:`interface.stored_data` (power vs. acquisition number).

        The window is created hidden; call ``plot_window.setHidden(False)`` or use
        :meth:`click_button_ShowHidePlot` to show it. The plot axis label and window
        title are updated after connection via :meth:`on_connection_status_change`.
        '''
        self.plot_window = Qt.QWidget() #This is the widget that will contain the plot. Since it does not have a parent, the plot will be in a floating (separated) window
        self.plot_object = PlotObject(self.interface.app, self.plot_window)
        styles = {"color": "#fff", "font-size": "20px"}
        self.plot_object.graphWidget.setLabel("left", "Power", **styles)
        self.plot_object.graphWidget.setLabel("bottom", "Acquisition #", **styles)
        self.plot_window.setWindowTitle(f"Powermeter: {self.interface.connected_device_name}")
        self.plot_window.show()
        self.plot_window.setHidden(True)
            
#################################################################################################

class MainWindow(Qt.QWidget):
    '''
    Top-level window used when running pyThorlabsPM100x as a standalone application.

    A plain ``QWidget`` whose title is set to the package name. The :class:`gui`
    panel is embedded inside it as a child widget. The window's ``closeEvent``
    triggers ``app.aboutToQuit``, which in turn calls :meth:`interface.close` to
    save settings and disconnect the device cleanly.
    '''
    def __init__(self):
        super().__init__()
        self.setWindowTitle(__package__)

 #   def closeEvent(self, event):
 #       #if self.child:
 #       pass#self.child.close()

#################################################################################################

def main():
    '''
    Entry point for the standalone pyThorlabsPM100x application.

    Parses command-line arguments, creates the Qt application, instantiates the
    :class:`interface` (model) and :class:`gui` (view/controller), shows the main
    window, and starts the Qt event loop.

    Command-line arguments
    ----------------------
    ``-s`` / ``--decrease_verbose``
        Suppress informational log output (sets ``Interface.verbose = False``).
    ``-virtual``
        Use the virtual driver (simulated devices) instead of real hardware.
    '''
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