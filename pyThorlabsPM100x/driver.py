import pyvisa as visa

class ThorlabsPM100x:

    #The list model_identifiers is used to identify a device as a Thorlabs console, and to detect its model.
    #Each element of the list is a list of two strings. If the second string is contained in the device identity (i.e. the answer to '*IDN?')
    #then the model device is given by the first string
    model_identifiers = [
                        ['PM100D',  'Thorlabs,PM100D'],
                        ['PM100A',   'Thorlabs,PM100A']
                        ]

    def __init__(self,model=None):
        if model:
            models_supported = [model[0] for model in self.model_identifiers] 
            if not(model in models_supported):
                   raise RuntimeError("The specified model is not supported. Supported models are " + ", ".join(models_supported))
        self.rm = visa.ResourceManager()
        self.connected = False
        self.model = None       #model of the device currently connected. 
        self.model_user = model #model specified by user. This variable is only used if the user specified a specific model
        self.being_zeroed = 0   #This flag is set to 1 while the powermeter is being zeroed, in order to temporarly stop any power reading
        self._wavelength = None
        self._auto_power_range = None # boolean variable, True if the powermeter has the auto power range ON, False otherwise
        self._power_range = None
        self._power = None
        self._power_units = None
        self._min_power_range = None
        self._max_power_range = None

        #The properties min_wavelength and max_wavelength are defined as 'standard' variables and not
        # via the the @property, because they never change once we are connected to a given powermeter, 
        # so we can query the powermeter only once (at connection) and avoid additional queries later.
        self.min_wavelength = None 
        self.max_wavelength = None
        
    def list_devices(self):
        '''
        Scans all potential devices, ask for their identity and check if any of them is a valid device supported by this driver (by comparing their identity with the elements of model_identifiers)

        Returns
        -------
        list_valid_devices, list
            A list of all found valid devices. Each element of the list is a list of three strings, in the format [address,identity,model]

        '''

        #This makes sure that the Resource Manager of pyvisa (if it was already initialized) is closed and cleared before looking for available devices
        #If a device was previously connected but was unplugged/turned off without doing a proper disconnection, it will not show up in the list  
        #of available devices (or it will generate an error when querying with '*IDN?'), unless we first close and clear the rm object.
        #However, when using this script together with other instruments which depend on pyvisa (e.g. in Ergastirio), this would interfere with other instrument. So for now is commented out
        #if hasattr(self, 'rm'):                 
        #    self.rm.close()                            
        #    #self.rm.visalib._registry.clear()   

        self.rm = visa.ResourceManager()
        self.list_all_devices = self.rm.list_resources()
        self.list_valid_devices = [] 
        for addr in self.list_all_devices:
            if(not(addr.startswith('ASRL'))):
                try:
                    instrument = self.rm.open_resource(addr)
                    idn = instrument.query('*IDN?').strip()
                    for model in self.model_identifiers: #sweep over all supported models
                        if model[1] in idn:              #check if idn is one of the supported models
                            if self.model_user  and not(self.model_user ==model[0]): #if the user had specified a specific model, we dont consider any other model
                                break
                            self.list_valid_devices.append([addr,idn,model[0]])
                    instrument.before_close()
                    instrument.close()     
                except visa.VisaIOError:
                    pass
        return self.list_valid_devices
    
    def connect_device(self,device_addr):
        self.list_devices()
        device_addresses = [dev[0] for dev in self.list_valid_devices]
        if (device_addr in device_addresses):
            try:         
                self.instrument = self.rm.open_resource(device_addr)
                Msg = self.instrument.query('*IDN?')
                for model in self.model_identifiers:
                    if model[0] in Msg:
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
        self.wavelength
        self.read_min_max_wavelength()
        self.power
        self.min_power_range
        self.max_power_range
        self.auto_power_range
        self.power_range

    def disconnect_device(self):
        if(self.connected == True):
            try:   
                self.instrument.control_ren(False)  # Disable remote mode
                self.instrument.close()
                ID = 1
                Msg = 'Succesfully disconnected.'
            except Exception as e:
                ID = 0 
                Msg = e
            self.connected = False
            return (Msg,ID)
        else:
            raise RuntimeError("Device is already disconnected.")

    @property
    def power(self):
        if not(self.connected):
            self._power , self._power_units = None , ''
            raise RuntimeError("No powermeter is currently connected.")
        if(self.being_zeroed==0):
            Msg1 = self.instrument.query('measure:power?')
            Msg2 = self.instrument.query('power:dc:unit?')
            self._power = float(Msg1)
            self._power_units = str(Msg2).strip('\n') 
        else:
            self._power , self._power_units = None , ''
        return (self._power , self._power_units)

    @property
    def power_units(self):
        return  'W'

    @property
    def wavelength(self):
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
        return self._wavelength

    def read_min_max_wavelength(self):
        if not(self.connected):
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('SENS:CORR:WAV? MIN')
        self.min_wavelength = int(float(Msg))
        Msg = self.instrument.query('SENS:CORR:WAV? MAX')
        self.max_wavelength = int(float(Msg))
        return self.min_wavelength, self.max_wavelength

    @property
    def min_power_range(self):
        if not(self.connected):
            self._min_power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG? MIN')
        self._min_power_range = float(Msg)
        return self._min_power_range

    @property
    def max_power_range(self):
        if not(self.connected):
            self._max_power_range = None
            raise RuntimeError("No powermeter is currently connected.")
        Msg = self.instrument.query('POW:DC:RANG? MAX')
        self._max_power_range = float(Msg)
        return self._max_power_range

    @property
    def auto_power_range(self):
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
        return self._auto_power_range

    @property
    def power_range(self):
        ''' Returns the current power range, defined as the maximum power measureable in the current power range'''
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
        return self._power_range


    def set_zero(self):
        ID = 0
        if(self.connected):
            try:
                self.being_zeroed = 1
                ID = self.instrument.write('sense:correction:collect:zero')
                self.being_zeroed = 0
                ID = 1
            except visa.VisaIOError:
                ID = 0
                pass
        return ID

    
    def move_to_next_power_range(self,direction,LastPowerRange = None):
        '''#Increase or decrease the power range, based on the value of the input variable direction
        Note: the VISA comnmands of the powermeter do not allow to simply "move" to the next power range, but only to specify the maximum power one would like to measure.
        The powermeter then sets the power range to the smallest available range which can still measure the desired power. This can be tricky to handle because, for example
        the bounds of each power range also depend on the wavelength. So, simply increasing the power by, e.g., a factor of 10, might sometimes fail, i.e. it might either not changethe power range,
        or it might skipp one of the ranges.
        To address this, I here use an adaptive alghoritm which progressively increases (or decreases) the power by a factor smaller than 10 and everytime it checks if the powermeter range has actually changed
        As soon as the powermeter range really changes, it stops.'''

        if not(direction==+1 or direction==-1):
            raise ValueError("The input variable 'direction' must be either +1 (to increase power range) or -1 (to decrease it).") 

        Factor = 10*0.9
        if not(LastPowerRange):
            LastPowerRange = self._power_range
        self.old_powerRange = self._power_range
        self.TargetPowerRange = (LastPowerRange * Factor) if (direction==+1) else (LastPowerRange / Factor)

        if self.TargetPowerRange*Factor < self._min_power_range:
            return
        if self.TargetPowerRange > self._max_power_range:
            return

        self.power_range = self.TargetPowerRange    #Try updating the power range to the new value. The value stored in self.power_range (when retrie it) will actually be one of the valid power ranges
                                                    #allowed by the specific powermeter.
        if self.power_range == self.old_powerRange: #if after setting the desired power, the power range of the powermeters is unchanged, we call again this function
            self.move_to_next_power_range(direction,self.TargetPowerRange)

        