# pyThorlabsPM100x

```pyThorlabsPM100x``` is a Python library/GUI interface to control the Thorlabs consoles PM100A and PM100D. The package is composed of two parts, a
low-level driver to perform basic operations, and high-level GUI, written with PyQt5, which can be easily embedded into other GUIs.

The interface can work either as a stand-alone application, or as a module of [ergastirio](https://github.com/MicheleCotrufo/ergastirio).

## Table of Contents
 - [Installation](#installation)
 - [Usage via the low-level driver](#usage-via-the-low-level-driver)
   * [Creating a driver instance](#creating-a-driver-instance)
   * [Virtual mode (no hardware needed)](#virtual-mode-no-hardware-needed)
   * [Properties](#properties)
   * [Other attributes](#other-attributes)
   * [Methods](#methods)
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
pip install abstract_instrument_interface>=0.10
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

The class `ThorlabsPM100x` supports several properties and methods to communicate with the console and to read/change its settings. Some of the properties are read-only, while others can be set. A full list of properties, attributes, and methods is available here below. **Note**: the documentation below was partially compiled with the help of Claude - mistakes are possible.

### Creating a driver instance

```python
ThorlabsPM100x(model=None, virtual=False)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `model` | str, optional | If specified, restricts this driver instance to only recognize/connect to devices of this model (`'PM100A'` or `'PM100D'`). `list_devices()` and `connect_device()` will ignore any device of a different model. Raises `RuntimeError` if an unsupported model name is passed. |
| `virtual` | bool, optional | If `True`, use a simulated VISA backend instead of real hardware (see [Virtual mode](#virtual-mode-no-hardware-needed) below). Default is `False`. |

### Virtual mode (no hardware needed)

Passing `virtual=True` makes the driver simulate three PM100x consoles (one PM100A and two PM100D, with different wavelength ranges) instead of talking to real hardware over `pyvisa`. This is useful for testing or demoing the package without a physical instrument, and works even if `pyvisa`/NI-VISA is not installed.

```python
from pyThorlabsPM100x.driver import ThorlabsPM100x
powermeter = ThorlabsPM100x(virtual=True)
available_devices = powermeter.list_devices()
print(available_devices)
powermeter.connect_device(device_addr = available_devices[0][0])
print(powermeter.power)   # returns a simulated, time-varying power reading
powermeter.disconnect_device()
```

### Properties

The following are implemented as Python `@property`, i.e. they are accessed without parentheses (e.g. `powermeter.power`) and, when settable, assigned with `=` (e.g. `powermeter.wavelength = 800`). Reading or setting any of these (except where noted) requires a device to be connected, otherwise a `RuntimeError` is raised.

| Property | Type | Description | <div style="width:300px"> Can be set?</div> | Notes |
| --- | --- | --- | --- | --- |
| `power` | (float,str) | First element of list is the power currently read by the console, second element is the power units. | No | Returns `(None, '')` while `being_zeroed==1`, instead of querying the instrument. |
| `power_units` | str | Power units, as reported by the instrument (typically `'W'` or `'dBm'`). | No |  |
| `wavelength` | int | Operating wavelength (in nanometers) of the console. | Yes | Each powermeter head has a different range of acceptable wavelengths, given by `min_wavelength`/`max_wavelength`. Setting a value outside that range raises a `ValueError`; a non-integer value raises a `TypeError`. |
| `power_range` | float | Current power range, defined as the maximum power measurable in the current range | Yes | When setting this property to a particular value X, the console will change the power range to the smallest power range which allows to measure the desired power X. Setting a negative or non-numeric value raises a `ValueError`/`TypeError`. Read the property again after setting it to obtain the actual range selected by the instrument. |
| `min_power_range` | float | Minimum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `max_power_range` | float | Maximum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `auto_power_range`| bool | Determines whether the console is in auto power range or not. | Yes | Setting a non-boolean value raises a `TypeError`. |

### Other attributes

These are plain instance attributes (not `@property`) that are also useful to read directly.

| Attribute | Type | Description |
| --- | --- | --- |
| `connected` | bool | `True` if a device is currently connected, `False` otherwise. |
| `model` | str or None | Model of the device currently connected (`'PM100A'` or `'PM100D'`), or `None` if not connected. |
| `model_user` | str or None | Model passed to the constructor (if any). When set, restricts `list_devices()`/`connect_device()` to that model only. |
| `min_wavelength` | int or None | Minimum operating wavelength (nm) supported by the connected device. Populated by `read_min_max_wavelength()`, which runs automatically on connection. |
| `max_wavelength` | int or None | Maximum operating wavelength (nm) supported by the connected device. Populated by `read_min_max_wavelength()`, which runs automatically on connection. |
| `being_zeroed` | int (0 or 1) | Set to `1` while the console is performing its zeroing routine (see `set_zero()`), `0` otherwise. While set to `1`, reading `power` returns `(None, '')` instead of querying the instrument. |
| `model_identifiers` | list | Class attribute. List of `[model_name, idn_substring]` pairs used to recognize a connected device's model from its `*IDN?` response. Supported models are currently `'PM100A'` and `'PM100D'`. |

### Methods
| Method | Returns | Description  |
| --- | --- | --- | 
| `list_devices()` | list |  Returns a list of all available devices. Each element of the list identifies a different device, and it is a three-element list in the form `[address,identity,model]`. The string `address` contains the physical address of the device. The string `idn` contains the 'identity' of the device (which is the answer of the device to the visa query '*IDN?'). The string `model` contains the device model (either 'PM100A' or 'PM100D'). If `model_user` was set when instantiating the driver, only devices of that model are returned. | 
| `connect_device(device_addr: str)` | (str,int) |  Attempt to connect to the device identified by the address in the string  `device_addr`. It returns a list of two elements. The first element is a string containing either the ID number of the connected device or an error message. The second element is an integer, equal to 1 if connection was succesful or to 0 otherwise. Raises `ValueError` if `device_addr` is not a currently available, supported device. On success, automatically calls `read_parameters_upon_connection()`. | 
| `read_parameters_upon_connection()` | None | Queries the instrument once for all relevant parameters (power units, wavelength, min/max wavelength, power, min/max power range, auto power range, power range) and caches them in the corresponding attributes. Called automatically by `connect_device()` right after a successful connection; you normally don't need to call it yourself. |
| `disconnect_device()` | (str,int)  | Attempt to disconnect the currently connected device. If no device is currently connected, it raises a `RuntimeError`. It returns a list of two elements. The first element is a string containing info on succesful disconnection or an error message. The second element is an integer, equal to 1 if disconnection was succesful or to 0 otherwise.  |
| `read_min_max_wavelength()` | (float,float) |  Returns the minimum and maximum operating wavelengths for the connected device, and stores them in `min_wavelength`/`max_wavelength`. If no device is currently connected, it raises a `RuntimeError`. | 
| `set_zero()` | int | Set the zero to the currently connected (if any) console. The returned value is 1 if the operation was successful, or 0 if any error occurred. | 
| `move_to_next_power_range(direction: int)`| None | It increases or decreases the power range of the console, depending on whether the input parameter is `direction=+1` or `direction=-1`. Raises `ValueError` if `direction` is not `+1` or `-1`. | 


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

```python
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
Interface = pyThorlabsPM100x.interface(app=app)
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

layout = Qt.QVBoxLayout()
layout.addWidget(widget_containing_interface_GUI)
layout.addWidget(gridlayoutwidget)
layout.addStretch(1)
window.setLayout(layout)


window.show()
app.exec()# Start the event loop.
```
