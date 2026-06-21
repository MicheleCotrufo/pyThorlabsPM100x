''' Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes'''

import pyvisa as visa

class ThorlabsPM100x:
    """
    Low-level driver to communicate with Thorlabs PM100A and PM100D powermeter consoles via VISA (NI-VISA backend).
 
    The console must be set to "PM100D NI-VISA" mode (and not to "TLPM" mode) in order to be detected
    by this driver. See the project README for details on how to switch mode.
 
    Attributes
    ----------
    model_identifiers : list of [str, str]
        Each element is ``[model_name, idn_substring]``. A device is recognized as ``model_name``
        if ``idn_substring`` is contained in the answer to the ``*IDN?`` query.
    rm : pyvisa.ResourceManager
        The PyVISA resource manager used to discover and open VISA resources.
    connected : bool
        ``True`` if a device is currently connected, ``False`` otherwise.
    model : str or None
        Model of the device currently connected (``'PM100A'`` or ``'PM100D'``), or ``None`` if not connected.
    model_user : str or None
        Model specified by the user when instantiating this driver (if any). When set, only devices
        matching this model are returned by :meth:`list_devices` and accepted by :meth:`connect_device`.
    being_zeroed : int
        Flag (0/1) set to 1 while the powermeter is performing its zeroing routine. While set, reading
        :attr:`power` does not query the instrument and returns ``(None, '')``.
    min_wavelength : int or None
        Minimum operating wavelength (in nm) supported by the connected device. Populated by
        :meth:`read_min_max_wavelength`, which is called automatically upon connection.
    max_wavelength : int or None
        Maximum operating wavelength (in nm) supported by the connected device. Populated by
        :meth:`read_min_max_wavelength`, which is called automatically upon connection.
    """
    #The list model_identifiers is used to identify a device as a Thorlabs console, and to detect its model.
    #Each element of the list is a list of two strings. If the second string is contained in the device identity (i.e. the answer to '*IDN?')
    #then the model device is given by the first string
    model_identifiers = [
                        ['PM100D',  'Thorlabs,PM100D'],
                        ['PM100A',   'Thorlabs,PM100A']
                        ]

    def __init__(self,model=None, virtual=False):
        """
        Parameters
        ----------
        model : str, optional
            If specified, restricts this driver instance to only recognize/connect to devices of this model.
            Must be one of the model names listed in :attr:`model_identifiers` (currently ``'PM100A'`` or ``'PM100D'``).
        virtual : bool, optional
            If ``True``, use the virtual VISA backend (``pyvisa_virtual``) instead of real hardware.
            This allows the driver to run without any physical device or pyvisa installation, using
            three simulated PM100x consoles. Default is ``False``.

        Raises
        ------
        RuntimeError
            If ``model`` is specified but is not one of the supported models.
        """
        if model:
            models_supported = [model[0] for model in self.model_identifiers] 
            if not(model in models_supported):
                   raise RuntimeError("The specified model is not supported. Supported models are " + ", ".join(models_supported))
        if virtual:
            import pyThorlabsPM100x.pyvisa_virtual as _visa
        else:
            import pyvisa as _visa
        self._VisaIOError = _visa.VisaIOError
        self.rm = _visa.ResourceManager()
        self.connected = False
        self.model = None       #model of the device currently connected. 
        self.model_user = model #model specified by user. This variable is only used if the user specified a specific model
        self.being_zeroed = 0   #This flag is set to 1 while the powermeter is being zeroed, in order to temporarily stop any power reading
        self._wavelength = None
        self._auto_power_range = None # boolean variable, True if the powermeter has the auto power range ON, False otherwise
        self._power_range = None
        self._power = None
        self._power_units = None
        self._min_power_range = None
        self._max_power_range = None

        #The properties min_wavelength and max_wavelength are defined as 'standard' variables and not
        # via the @property, because they never change once we are connected to a given powermeter, 
        # so we can query the powermeter only once (at connection) and avoid additional queries later.
        self.min_wavelength = None 
        self.max_wavelength = None
        
    def list_devices(self):
        '''
        Scan all VISA resources currently visible to the system, query their identity (``*IDN?``), and
        check whether any of them is a powermeter console supported by this driver (by comparing the
        identity string with the entries of :attr:`model_identifiers`).
 
        Serial (``ASRL``) resources are skipped, since Thorlabs powermeter consoles are not accessed
        over a plain serial port.
 
        If :attr:`model_user` was set (i.e. the user requested a specific model when instantiating this
        driver), only devices matching that model are included in the returned list.
 
        Returns
        -------
        list_valid_devices : list of [str, str, str]
            A list of all found valid devices. Each element is a list of three strings, in the format
            ``[address, idn, model]``, where ``address`` is the VISA resource address, ``idn`` is the
            raw answer to ``*IDN?``, and ``model`` is either ``'PM100A'`` or ``'PM100D'``.
        '''

                #This makes sure that the Resource Manager of pyvisa (if it was already initialized) is closed and cleared before looking for available devices
                #If a device was previously connected but was unplugged/turned off without doing a proper disconnection, it will not show up in the list  
                #of available devices (or it will generate an error when querying with '*IDN?'), unless we first close and clear the rm object.
                #However, when using this script together with other instruments which depend on pyvisa (e.g. in Ergastirio), this would interfere with other instrument. So for now is commented out
                #if hasattr(self, 'rm'):                 
                #    self.rm.close()                            
                #    #self.rm.visalib._registry.clear()   

        self.list_all_devices = self.rm.list_resources()
        self.list_valid_devices = [] 
        for addr in self.list_all_devices:
            if(not(addr.startswith('ASRL'))):
                try:
                    instrument = self.rm.open_resource(addr)
                    idn = instrument.query('*IDN?').strip()
                    for model in self.model_identifiers: #sweep over all supported models
                        if model[1] in idn:              #check if idn is one of the supported models
                            if self.model_user  and not(self.model_user ==model[0]): #if the user had specified a specific model, we don't consider any other model
                                break
                            self.list_valid_devices.append([addr,idn,model[0]])
                    instrument.before_close()
                    instrument.close()     
                except visa.VisaIOError:
                    pass
        return self.list_valid_devices
    
    def connect_device(self,device_addr):
        '''
        Attempt to connect to the device identified by ``device_addr``.
 
        The device address is first validated against the list of currently available, supported
        devices (obtained via :meth:`list_devices`). Upon successful connection, all relevant
        instrument parameters (wavelength, power range, etc.) are read once via
        :meth:`read_parameters_upon_connection`.
 
        Parameters
        ----------
        device_addr : str
            VISA resource address of the device to connect to (as returned by :meth:`list_devices`).
 
        Returns
        -------
        (Msg, ID) : (str, int)
            ``Msg`` is either the identity string (``*IDN?`` answer) of the connected device, or an
            error message. ``ID`` is 1 if connection was successful, 0 otherwise.
 
        Raises
        ------
        ValueError
            If ``device_addr`` does not correspond to any currently available, supported device.
        '''
        self.list_devices()
        device_addresses = [dev[0] for dev in self.list_valid_devices]
        if (device_addr in device_addresses):
            try:         
                self.instrument = self.rm.open_resource(device_addr)
                Msg = self.instrument.query('*IDN?')
                for model in self.model_identifiers:
                    if model[1] in Msg:
                        self.model = model[0]
                ID = 1
            except visa.VisaIOError:
                Msg = "Error while connecting."
                ID = 0 
        else:
            raise ValueError("The specified address is not a valid device address.")
        if(ID==1):
            self.connected = True
            self.read_parameters_upon_connection()
        return (Msg,ID)

    def read_parameters_upon_connection(self):
        '''
        Query the instrument once for all relevant parameters and cache them in the
        corresponding private instance attributes.

        Called automatically by :meth:`connect_device` immediately after a successful
        connection. Each line accesses a property (or calls a method) whose getter issues
        a VISA query and stores the result in the corresponding ``_``-prefixed attribute
        (e.g. accessing ``self.wavelength`` caches the result in ``self._wavelength``).
        This ensures all cached values are up to date at the moment of connection, so
        that the rest of the program can read them without issuing additional VISA queries.

        Parameters queried: power units, wavelength, wavelength range (min/max), power,
        min/max power range, auto power range status, current power range.
        '''
        self.power_units
        self.wavelength
        self.read_min_max_wavelength()
        self.power
        self.min_power_range
        self.max_power_range
        self.auto_power_range
        self.power_range

    def disconnect_device(self):
        '''
        Disconnect the currently connected device, disabling its remote-control mode and closing the
        underlying VISA resource.
 
        Returns
        -------
        (Msg, ID) : (str, int)
            ``Msg`` is a confirmation message, or the exception raised while disconnecting.
            ``ID`` is 1 if disconnection was successful, 0 otherwise.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if(self.connected == True):
            try:   
                self.instrument.control_ren(False)  # Disable remote mode
                self.instrument.close()
                ID = 1
                Msg = 'Successfully disconnected.'
            except Exception as e:
                ID = 0 
                Msg = e
            self.connected = False
            return (Msg,ID)
        else:
            raise RuntimeError("Device is already disconnected.")

    @property
    def power(self):
        '''
        (float, str): The power currently measured by the console, and its units.
 
        Querying this property issues a VISA query to the instrument (``measure:power?``). While :attr:`being_zeroed` is set (i.e. while the instrument is performing
        its zeroing routine), no query is sent and ``(None, '')`` is returned instead.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if not(self.connected):
            self._power , self._power_units = None , ''
            raise RuntimeError("No powermeter is currently connected.")
        if(self.being_zeroed==0):
            Msg1 = self.instrument.query('measure:power?')
            self._power = float(Msg1)
        else:
            self._power , self._power_units = None , ''
        return (self._power , self._power_units)

    @property
    def power_units(self):
        '''
        str: The units of the power readings, as reported by the instrument (``power:dc:unit?``).

        Typical values are ``'W'`` (watts) or ``'dBm'``. The result is also cached in
        ``self._power_units``, which is used by :attr:`power` to return the units alongside
        the power value without an extra query.

        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if not(self.connected):
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('power:dc:unit?')
        self._power_units = str(Msg).strip('\n') 
        return  self._power_units

    @property
    def wavelength(self):
        '''
        int: The operating (calibration) wavelength of the console, in nanometers.
 
        Reading this property queries the instrument (``SENS:CORR:WAV?``).
        Setting this property writes the new wavelength to the instrument (``SENS:CORR:WAV <value>``).
        The value must be an integer between :attr:`min_wavelength` and :attr:`max_wavelength`
        (inclusive), which depend on the specific powermeter head connected to the console and are
        populated by :meth:`read_min_max_wavelength`.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        TypeError
            (setter only) If the assigned value cannot be converted to ``int``.
        ValueError
            (setter only) If the assigned value is negative or outside the range
            ``[min_wavelength, max_wavelength]``.
        '''
        if not(self.connected):
            self._wavelength = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('SENS:CORR:WAV?')
        self._wavelength = int(float(Msg))
        return self._wavelength

    @wavelength.setter
    def wavelength(self, wl):
        #Input variable wl can be either a string or a float or an int
        if not(self.connected):
            self._wavelength = None
            raise RuntimeError("No powermeter is currently connected.")
        try:
            wl = int(wl)
        except:
            raise TypeError("Wavelength value must be a valid integer number")
        if wl<0:
            raise ValueError("Wavelength must be a positive number.")
        if wl<self.min_wavelength or wl>self.max_wavelength:
            raise ValueError(f"Wavelength must be between {self.min_wavelength} and {self.max_wavelength}.")
        self.instrument.write('SENS:CORR:WAV ' + str(wl))
        self._wavelength = wl

    def read_min_max_wavelength(self):
        '''
        Query the instrument for the minimum and maximum operating wavelengths supported by the
        currently connected powermeter head, and store them in :attr:`min_wavelength` and
        :attr:`max_wavelength`.
 
        This is called automatically by :meth:`read_parameters_upon_connection` upon connection, since
        these bounds depend on the powermeter head and do not change afterwards.
 
        Returns
        -------
        (min_wavelength, max_wavelength) : (int, int)
            The minimum and maximum operating wavelengths, in nanometers.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if not(self.connected):
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('SENS:CORR:WAV? MIN')
        self.min_wavelength = int(float(Msg))
        Msg = self.instrument.query('SENS:CORR:WAV? MAX')
        self.max_wavelength = int(float(Msg))
        return self.min_wavelength, self.max_wavelength

    @property
    def min_power_range(self):
        '''
        float: The minimum power range available for the current wavelength, defined as the maximum
        power measurable within that range. Queries the instrument (``POW:DC:RANG? MIN``).
 
        This value depends on the powermeter head and, for the same head, may also depend on the
        currently set wavelength.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if not(self.connected):
            self._min_power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG? MIN')
        self._min_power_range = float(Msg)
        return self._min_power_range

    @property
    def max_power_range(self):
        '''
        float: The maximum power range available for the current wavelength, defined as the maximum
        power measurable within that range. Queries the instrument (``POW:DC:RANG? MAX``).
 
        This value depends on the powermeter head and, for the same head, may also depend on the
        currently set wavelength.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        '''
        if not(self.connected):
            self._max_power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG? MAX')
        self._max_power_range = float(Msg)
        return self._max_power_range

    @property
    def auto_power_range(self):
        '''
        bool: Whether the console's automatic power-ranging mode is currently enabled.
 
        Reading this property queries the instrument (``POW:DC:RANG:AUTO?``).
        Setting this property enables (``True``) or disables (``False``) automatic power ranging
        (``POW:DC:RANG:AUTO ON``/``OFF``).
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        TypeError
            (setter only) If the assigned value is not a ``bool``.
        '''
        if not(self.connected):
            self._auto_power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG:AUTO?')
        self._auto_power_range = bool(int(Msg))         
        return self._auto_power_range

    @auto_power_range.setter
    def auto_power_range(self, status):
        if not(self.connected):
            raise RuntimeError("No powermeter is currently connected.")
        if not(type(status)==bool):
            raise TypeError("Value of auto_power_range must be either True or False.")
        string = 'ON' if status else 'OFF'
        self.instrument.write('POW:DC:RANG:AUTO ' + string)
        self._auto_power_range = status

    @property
    def power_range(self):
        '''
        float: The current power range, defined as the maximum power measurable within
        this range. Queries the instrument (``POW:DC:RANG?``).
 
        Setting this property requests the instrument to change to the smallest available power
        range that can still measure the requested value; the instrument may therefore end up in a
        power range different from (but containing) the requested value. Read this property again
        after setting it to obtain the actual power range selected by the instrument.
 
        Raises
        ------
        RuntimeError
            If no device is currently connected.
        TypeError
            (setter only) If the assigned value is not an ``int`` or ``float``.
        ValueError
            (setter only) If the assigned value is negative.
        '''
        if not(self.connected):
            self._power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG?')
        self._power_range = float(Msg)
        return self._power_range

    @power_range.setter
    def power_range(self, power):
        if not(self.connected):
            raise RuntimeError("No powermeter is currently connected.")
        if not(type(power)==int or type(power)==float):
            raise TypeError("Value of power_range must be a number.")
        if power<0:
            raise ValueError("Power must be a positive number.")
        self.instrument.write('POW:DC:RANG ' + str(power))
        self._power_range = power


    def set_zero(self):
        '''
        Trigger the zeroing routine of the console (``sense:correction:collect:zero``).
 
        While the zeroing routine is running, :attr:`being_zeroed` is set to 1, and reading
        :attr:`power` will return ``(None, '')`` instead of querying the instrument.
 
        Returns
        -------
        ID : int
            1 if the command was sent successfully, 0 if a VISA error occurred.
        '''
        ID = 0
        if(self.connected):
            self.being_zeroed = 1
            try:
                self.instrument.write('sense:correction:collect:zero')
                self.being_zeroed = 0
                ID = 1
            except visa.VisaIOError:
                ID = 0
                self.being_zeroed = 0
                pass
        return ID

    
    def move_to_next_power_range(self,direction,LastPowerRange = None):
        '''
        Increase or decrease the power range of the console by one step.
 
        The VISA interface of the powermeter does not allow directly "stepping" to the next or
        previous power range: it only allows requesting a target maximum power, and the instrument
        then selects the smallest available range that can still measure that power. Because the
        boundaries of each power range also depend on the current wavelength, simply multiplying or
        dividing the current range by a fixed factor (e.g. 10) can sometimes fail to change the range
        at all, or can skip over a range entirely.
 
        To work around this, this method uses an adaptive algorithm: it repeatedly requests a target
        power range scaled by a factor smaller than 10 (currently 9), checking after each attempt
        whether the instrument's actual power range has changed. As soon as the power range changes,
        the method returns. The method recurses on itself (with an updated target) until the power
        range changes or until the requested target falls outside
        [:attr:`min_power_range`, :attr:`max_power_range`], in which case the method returns without
        changing anything.
 
        Parameters
        ----------
        direction : int
            ``+1`` to increase the power range, ``-1`` to decrease it.
        LastPowerRange : float, optional
            Internal parameter used during recursive calls to track the most recently requested
            target power range. Should not normally be supplied by the caller.
 
        Raises
        ------
        ValueError
            If ``direction`` is not ``+1`` or ``-1``.
        '''

        if not(direction==+1 or direction==-1):
            raise ValueError("The input variable 'direction' must be either +1 (to increase power range) or -1 (to decrease it).") 

        Factor = 10*0.9
        if LastPowerRange is None:
            LastPowerRange = self._power_range
        self.old_powerRange = self._power_range
        self.TargetPowerRange = (LastPowerRange * Factor) if (direction==+1) else (LastPowerRange / Factor)

        if self.TargetPowerRange*Factor < self._min_power_range:
            return
        if self.TargetPowerRange > self._max_power_range:
            return

        self.power_range = self.TargetPowerRange    #Try updating the power range to the new value. The value stored in self.power_range (when retrieving it) will actually be one of the valid power ranges
                                                    #allowed by the specific powermeter.
        if self.power_range == self.old_powerRange: #if after setting the desired power, the power range of the powermeters is unchanged, we call again this function
            self.move_to_next_power_range(direction,self.TargetPowerRange)