# pyThorlabsPM100x

```pyThorlabsPM100x``` is a Python library/GUI interface to control the Thorlabs consoles PM100A and PM100D. The package is composed of two parts, a
low-level driver to perform basic operations, and high-level GUI, written with PyQt5, which can be easily embedded into other GUIs.

## Installation

Use the package manager pip to install,

```bash
pip install pyThorlabsPM100x
```

This should automatically install all libraries needed by ```pyThorlabsPM100x```. If any error occurs during installation, try installing first
the required dependencies separately (one by one), via
```bash
pip install "PyQt5>=5.15.6"
pip install "pyqtgraph>=0.12.4"
pip install pyvisa
pip install numpy
```
and then run again ```pip install pyThorlabsPM100x```

**Important:** in order to be accessible from this script, the console needs to be set to "NI-VISA driver" modality, and not to
"TLPM modality". Typically, using the console with recent Thorlabs software will automatically set it to "TLPM modality".
You can use the utility [Power Meter Driver Switcher](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM) to switch between modalities.

## Usage as a stand-alone GUI interface
The installation should set up an entry point for the GUI. Just typing
```bash
pyThorlabsPM100x
```
in the command prompt to start the GUI.

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
The method `list_devices()` returns a list, with each element representing one available device in the format `[address,identiy,model]`. The string `address` contains 
the physical address of the device. The line `powermeter.connect_device(device_addr = available_devices[0][0])` establishes a connection to the first device found.
We then print the power currently read by the console, and finally disconnect from it.

**Properties**

| Property | Type | Description | Can be set? | Notes |
| --- | --- | --- |  --- | --- |
| `power` | (float,str) | First element of list is the power currently read by the console, second element is the power units. | No |
| `power_units` | str | Power units | No |
| `wavelength` | int | Operating wavelength of the console. | Yes | Each powermerter head has a different range of acceptable wavelengths. The driver will **not** return an error when trying to set a wavelength outside of this range. |
| `power_range` | float | Current power range, defined as the maximum power measurable in the current range | Yes | When setting this property to a particular value X, the console will change the power range to the smallest power range which allows to measure the desired power X. |
| `min_power_range` | float | Minimum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `max_power_range` | float | Maximum power range available. | No | For the same console/head, this value might vary for different wavelengths. |
| `auto_power_range`| bool | Determines whether the consol is in auto power range or not. | Yes | |




