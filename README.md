# pyThorlabsPM100x

```pyThorlabsPM100x``` is a Python library/GUI interface to control the Thorlabs consoles PM100A and PM100D. The package is composed by two parts, a
low-level driver to perform basic operations, and high-level GUI, written with PyQt5, which can be easily embedded into other GUIs.

## Installation

Use the package manager pip to install pdf2doi.

```bash
pip install pyThorlabsPM100x
```

This should automatically install all the libraries needed by ```pyThorlabsPM100x```. If any error occurs during installation, try to first installing 
required dependencies separately (one by one), via
```bash
pip install "PyQt5>=5.15.6
pip install pyqtgraph>=0.12.4
pip install pyvisa
pip install numpy
```

**Important:** in order to be accessible from this script, the console needs to be set to "NI-VISA driver" modality, and not to
"TLPM modality". Typically, the console will be automatically set to "TLPM modality" after installation of recent Thorlabs software.
You can use the utility [Power Meter Driver Switcher](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM) to switch the modality.

## Usage
TO DO