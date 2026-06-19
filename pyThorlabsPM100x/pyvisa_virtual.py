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
    pass


class _VirtualInstrument:
    """Mimics a pyvisa Resource, responding to PM100x SCPI commands."""

    def __init__(self, state: dict):
        self._s = state  # mutable; shared with ResourceManager so state persists

    def query(self, cmd: str) -> str:
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
        pass

    def close(self) -> None:
        pass

    def control_ren(self, enable: bool) -> None:
        pass


class ResourceManager:
    """Mimics pyvisa.ResourceManager, advertising three virtual PM100x devices."""

    def __init__(self):
        # Deep-copy configs so each ResourceManager instance has independent state.
        self._states = [dict(cfg) for cfg in _DEVICE_CONFIGS]

    def list_resources(self) -> tuple:
        return tuple(s['addr'] for s in self._states)

    def open_resource(self, addr: str) -> _VirtualInstrument:
        for s in self._states:
            if s['addr'] == addr:
                return _VirtualInstrument(s)
        raise VisaIOError(f"No virtual resource at address {addr!r}")
