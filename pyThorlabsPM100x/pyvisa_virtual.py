''' Note: most of docstrings in this file have been generated automatically by Claude. AI can make mistakes'''

"""
Drop-in replacement for pyvisa that simulates three Thorlabs PM100x devices.
Exposes the same ResourceManager / instrument API that driver.py uses so that
ThorlabsPM100x(virtual=True) can run without any real hardware or pyvisa installed.
"""

import math
import time

# Per-device configuration.  Each entry describes one simulated instrument.
_DEVICE_CONFIGS = [
    {
        'addr':            'VIRTUAL0::INSTR',
        'idn':             'Thorlabs,PM100A,SN00001,V1.0',
        'min_wl':          400,
        'max_wl':          1000,
        'wavelength':      600,
        'phase':           math.pi / 6,
        'min_power_range': 1e-4,
        'max_power_range': 10.0,
        'power_range':     1e-3,
        'auto_power_range': False,
        'power_units':     'W',
    },
    {
        'addr':            'VIRTUAL1::INSTR',
        'idn':             'Thorlabs,PM100D,SN00002,V1.0',
        'min_wl':          700,
        'max_wl':          1800,
        'wavelength':      800,
        'phase':           math.pi / 3,
        'min_power_range': 1e-4,
        'max_power_range': 10.0,
        'power_range':     1e-3,
        'auto_power_range': False,
        'power_units':     'W',
    },
    {
        'addr':            'VIRTUAL2::INSTR',
        'idn':             'Thorlabs,PM100D,SN00003,V1.0',
        'min_wl':          400,
        'max_wl':          15000,
        'wavelength':      1500,
        'phase':           math.pi,
        'min_power_range': 1e-4,
        'max_power_range': 10.0,
        'power_range':     1e-3,
        'auto_power_range': False,
        'power_units':     'W',
    },
]


class VisaIOError(Exception):
    '''
    Simulated VISA I/O error, raised by :class:`_VirtualInstrument` and
    :class:`ResourceManager` in the same situations where ``pyvisa.VisaIOError``
    would be raised by the real pyvisa library (unrecognized SCPI commands,
    unknown resource addresses, etc.).
    '''
    pass


class _VirtualInstrument:
    """
    Simulated pyvisa resource that responds to the SCPI commands used by
    :class:`~pyThorlabsPM100x.driver.ThorlabsPM100x`.

    State is stored in a mutable dict (``_s``) shared with the parent
    :class:`ResourceManager`, so changes made via :meth:`write` persist across
    multiple :meth:`query` calls and survive re-opening the same virtual resource.

    Supported SCPI commands
    -----------------------
    Queries (``query``):
        ``*IDN?``, ``measure:power?``, ``power:dc:unit?``, ``SENS:CORR:WAV?``,
        ``SENS:CORR:WAV? MIN``, ``SENS:CORR:WAV? MAX``, ``POW:DC:RANG? MIN``,
        ``POW:DC:RANG? MAX``, ``POW:DC:RANG:AUTO?``, ``POW:DC:RANG?``

    Writes (``write``):
        ``SENS:CORR:WAV <value>``, ``POW:DC:RANG:AUTO ON``,
        ``POW:DC:RANG:AUTO OFF``, ``POW:DC:RANG <value>``,
        ``sense:correction:collect:zero``
    """

    def __init__(self, state: dict):
        '''
        Parameters
        ----------
        state : dict
            Mutable state dictionary for this virtual device, shared with the
            :class:`ResourceManager` that created it. Must contain the keys defined
            in ``_DEVICE_CONFIGS``.
        '''
        self._s = state  # mutable; shared with ResourceManager so state persists

    def query(self, cmd: str) -> str:
        '''
        Send a SCPI query to the simulated instrument and return its response.

        The simulated power (``measure:power?``) is a sinusoid oscillating between
        0 and 2 with a period of 5 seconds, offset by a per-device phase.

        Parameters
        ----------
        cmd : str
            SCPI query string (leading/trailing whitespace is stripped).

        Returns
        -------
        str
            The simulated instrument response.

        Raises
        ------
        VisaIOError
            If ``cmd`` is not one of the supported query strings.
        '''
        cmd = cmd.strip()
        s = self._s
        if cmd == '*IDN?':
            return s['idn']
        if cmd == 'measure:power?':
            value = math.sin(s['phase'] + 2 * math.pi * time.time() / 5) + 1
            return str(value)
        if cmd == 'power:dc:unit?':
            return s['power_units']
        if cmd == 'SENS:CORR:WAV?':
            return str(float(s['wavelength']))
        if cmd == 'SENS:CORR:WAV? MIN':
            return str(float(s['min_wl']))
        if cmd == 'SENS:CORR:WAV? MAX':
            return str(float(s['max_wl']))
        if cmd == 'POW:DC:RANG? MIN':
            return str(s['min_power_range'])
        if cmd == 'POW:DC:RANG? MAX':
            return str(s['max_power_range'])
        if cmd == 'POW:DC:RANG:AUTO?':
            return '1' if s['auto_power_range'] else '0'
        if cmd == 'POW:DC:RANG?':
            return str(s['power_range'])
        raise VisaIOError(f"Unrecognised query: {cmd!r}")

    def write(self, cmd: str) -> None:
        '''
        Send a SCPI write command to the simulated instrument, updating its state.

        Parameters
        ----------
        cmd : str
            SCPI write command string (leading/trailing whitespace is stripped).

        Raises
        ------
        VisaIOError
            If ``cmd`` is not one of the supported write commands.
        '''
        cmd = cmd.strip()
        s = self._s
        if cmd.startswith('SENS:CORR:WAV '):
            s['wavelength'] = int(float(cmd.split(' ', 1)[1]))
        elif cmd == 'POW:DC:RANG:AUTO ON':
            s['auto_power_range'] = True
        elif cmd == 'POW:DC:RANG:AUTO OFF':
            s['auto_power_range'] = False
        elif cmd.startswith('POW:DC:RANG '):
            s['power_range'] = float(cmd.split(' ', 1)[1])
        elif cmd == 'sense:correction:collect:zero':
            pass  # zeroing is a no-op in simulation
        else:
            raise VisaIOError(f"Unrecognised write command: {cmd!r}")

    def before_close(self) -> None:
        '''No-op. Provided for API compatibility with pyvisa resources.'''
        pass

    def close(self) -> None:
        '''No-op. Provided for API compatibility with pyvisa resources.'''
        pass

    def control_ren(self, enable: bool) -> None:
        '''
        No-op. Provided for API compatibility with pyvisa resources.

        Parameters
        ----------
        enable : bool
            Ignored in the virtual driver.
        '''
        pass


class ResourceManager:
    """
    Simulated pyvisa ``ResourceManager``, advertising three virtual PM100x devices.

    Each instance gets its own independent copy of the device state (deep-copied
    from ``_DEVICE_CONFIGS``), so multiple :class:`ResourceManager` instances do
    not share state. Within a single instance, state changes made via
    :meth:`~_VirtualInstrument.write` on an opened resource persist for the
    lifetime of that ``ResourceManager``.

    Simulated devices
    -----------------
    ``VIRTUAL0::INSTR``
        PM100A, wavelength range 400–1000 nm.
    ``VIRTUAL1::INSTR``
        PM100D, wavelength range 700–1800 nm.
    ``VIRTUAL2::INSTR``
        PM100D, wavelength range 400–15000 nm.
    """

    def __init__(self):
        '''
        Initialize the resource manager with independent copies of all device states.
        '''
        # Deep-copy configs so each ResourceManager instance has independent state.
        self._states = [dict(cfg) for cfg in _DEVICE_CONFIGS]

    def list_resources(self) -> tuple:
        '''
        Return the VISA addresses of all simulated devices.

        Returns
        -------
        tuple of str
            VISA address strings for all three virtual devices.
        '''
        return tuple(s['addr'] for s in self._states)

    def open_resource(self, addr: str) -> _VirtualInstrument:
        '''
        Open and return a simulated instrument for the given VISA address.

        Parameters
        ----------
        addr : str
            VISA resource address, as returned by :meth:`list_resources`.

        Returns
        -------
        _VirtualInstrument
            A virtual instrument object whose state is shared with this
            ``ResourceManager`` (changes persist across open/close cycles).

        Raises
        ------
        VisaIOError
            If ``addr`` does not match any of the three simulated device addresses.
        '''
        for s in self._states:
            if s['addr'] == addr:
                return _VirtualInstrument(s)
        raise VisaIOError(f"No virtual resource at address {addr!r}")