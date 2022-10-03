#If this package was installed only to use the low-level driver, the PyQt library is not necessarily installed. In this case, importing stuff from main.py would generate an error
import importlib.util
package_name = 'PyQt5'
spec = importlib.util.find_spec(package_name)
if spec:
    from .main import interface, gui




