# pyThorlabsPM100x

```pyThorlabsPM100x``` is a Python library/GUI interface to control the Thorlabs consoles PM100A and PM100D. The package is composed of two parts, a
low-level driver to perform basic operations, and high-level GUI, written with PyQt5, which can be easily embedded into other GUIs.

## Table of Contents
 - [Installation](#installation)
  - [Usage via the low-level driver](#usage-via-the-low-level-driver)
	* [Examples](#examples)
 - [Usage as a stand-alone GUI interface](#usage-as-a-stand-alone-GUI-interface)
 - [Embed the GUI within another GUI](#embed-the-gui-within-another-gui)


## Installation

Use the package manager pip to install,

```bash
pip install pyThorlabsPM100x
```
This will install ```pyThorlabsPM100x``` together with all libraries required to run the low-level driver. In order to use the GUI, it is necessary to install additional libraries,
specified in the ```requirements.txt``` files,
```bash
pip install abstract_instrument_interface>=0.6
pip install "PyQt5>=5.15.6"
pip install "pyqtgraph>=0.12.4"
pip install numpy
```

**Important:** in order to be accessible from this library, the console needs to be set to "PM100D NI-VISA" modality, and not to
"TLPM modality". Typically, if you used recent Thorlabs software to acquire from a console, that will automatically set the console to "TLPM modality".
You can use the utility [Power Meter Driver Switcher](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM) to switch between modalities.

## Usage via the low-level driver

`pyThorlabsPM100x` provides also a low-level driver, based on the library `pyvisa`, to directly interface with the powermeter console.

```python
from pyThorlabsPM100x.driver import ThorlabsPM100x
powermeter = ThorlabsPM100x()
available_devices = powermeter.list_devices()
print(available_devices)
powermeter.connect_device(device_addr = available_devices[0][0])
print(powermeter.power)
powermeter.disconnect_device()
```
The method `list_devices()` returns a list, with each element representing one available device in the format `[address,identity,model]`. The string `address` contains 
the physical address of the device. The line `powermeter.connect_device(device_addr = available_devices[0][0])` establishes a connection to the first device found.
We then print the power currently read by the console, and finally disconnect from it.

The class `ThorlabsPM100x` supports several properties and methods to communicate with the console and to read/change its settings. Some of the properties are read-only, while others can be set. A full list of properties and methods is available here below

**Properties**

| Property | Type | Description | <div style="width:300px"> Can be set?</div> | Notes |
| --- | --- | --- | --- | --- |
| `power` | (float,str) | First element of list is the power currently read by the console, second element is the power units. | No |
| `power_units` | str | Power units | No |
| `wavelength` | int | Operating wavelength (in nanometers) of the console. | Yes | Each powermerter head has a different range of acceptable wavelengths. The driver will **not** return an error when trying to set a wavelength outside of this range. |
| `power_range` | float | Current power range, defined as the maximum power measurable in the current range | Yes | When setting this property to a particular value X, the console will change the power range to the smallest power range which allows to measure the desired power X. |
| `min_power_range` | float | Minimum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `max_power_range` | float | Maximum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `auto_power_range`| bool | Determines whether the consol is in auto power range or not. | Yes | |
| `being_zeroed`| bool | It is True if zero of the device is currently being set. | No | The property `power` will return (None,'') if read while `being_zeroed==True` |

**Methods**
| Method | Returns | Description  |
| --- | --- | --- | 
| `list_devices()` | list |  Returns a list of all available devices. Each element of the list identifies a different device, and it is a three-element list in the form `[address,identity,model]`. The string `address` contains the physical address of the device. The string `idn` contains the 'identity' of the device (which is the answer of the device to the visa query '*IDN?'). The string `model` contains the device model (either 'PM100A' or 'PM100D').| 
| `connect_device(device_addr: str)` | (str,int) |  Attempt to connect to the device identified by the address in the string  `device_addr`. It returns a list of two elements. The first element is a string containing either the ID number of the connected device or an error message. The second element is an integer, equal to 1 if connection was succesful or to 0 otherwise. | 
| `disconnect_device()` | (str,int)  | Attempt to disconnect the currently connected device. If no device is currently connected, it raises a `RuntimeError`. It returns a list of two elements. The first element is a string containing info on succesful disconnection or an error message. The second element is an integer, equal to 1 if disconnection was succesful or to 0 otherwise.  |
| `read_min_max_wavelength()` | (float,float) |  Returns the minimum and maximum operating wavelengths for the connected device. If no device is currently connected, it raises a `RuntimeError`. | 
| `set_zero()` | int | Set the zero to the currently connected (if any) console. The returned value is 1 if the operation was successful, or 0 if any error occurred. | 
| `move_to_next_power_range(direction: int)`| None | It increases or decreases the power range of the console, depending on whether the input parameter is `direction=+1` or `direction=-1`. | 


### Examples
```python
from pyThorlabsPM100x.driver import ThorlabsPM100x
powermeter = ThorlabsPM100x()
available_devices = powermeter.list_devices() #Check which devices are available
print(available_devices)
powermeter.connect_device(device_addr = available_devices[0][0]) #Connect to the first available device
print(powermeter.power) #print the power currently read
print(powermeter.wavelength) #print the operating wavelength
(minWL,maxWL) = powermeter.read_min_max_wavelength() #read max and min available wavelengths
powermeter.wavelength = maxWL #set wavelength to the max
print(powermeter.power_range) #print current power range
powermeter.move_to_next_power_range(direction=+1) #increaase power range
print(powermeter.power_range) #print new power range
powermeter.disconnect_device() #disconnect the device
```

## Usage as a stand-alone GUI interface
The installation should set up an entry point for the GUI. Just typing
```bash
pyThorlabsPM100x
```
in the command prompt will start the GUI.

## Embed the GUI within another GUI
The GUI controller can also be easily integrated within a larger graphical interface, as shown in the example [here](https://github.com/MicheleCotrufo/pyThorlabsPM100x/blob/master/examples/embedding_in_gui.py).

