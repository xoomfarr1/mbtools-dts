"""MBTools VIN / vehicle identification helpers (stdlib only).

This is a copy of ``mbtools.core.ecu``.  It turns a 17-character VIN into the
fields the rest of the toolset uses: the manufacturer (WMI lookup), the model
year (10th character), and the plant code and serial (kept verbatim).

The sample manufacturer table and model tables are illustrative sample data --
the repository deliberately ships no OEM VIN code tables.
"""

from __future__ import annotations

import re

WMI_MAKER = {
    "437": "Mercedes-Benz", "WBA": "BMW", "WVW": "Volkswagen",
    "1G1": "General Motors", "1G2": "General Motors", "2GC": "General Motors",
    "3GM": "General Motors", "4T1": "Toyota", "4T2": "Toyota",
    "7T1": "Toyota", "7T2": "Toyota", "1HG": "Honda", "1N1": "Nissan",
    "6J1": "Nissan",
}

_MODEL_YEAR_CODES = {
    "A": "1980", "B": "1981", "C": "1982", "D": "1983", "E": "1984",
    "F": "1985", "G": "1986", "H": "1987", "J": "1988", "K": "1989",
    "L": "1990", "M": "1991", "N": "1992", "P": "1993", "R": "1994",
    "S": "1995", "T": "1996", "V": "1997", "W": "1998", "X": "1999", "Y": "2000",
    "1": "2001", "2": "2002", "3": "2003", "4": "2004", "5": "2005",
    "6": "2006", "7": "2007", "8": "2008", "9": "2009",
    "A": "2010", "B": "2011", "C": "2012", "D": "2013", "E": "2014",
    "F": "2015", "G": "2016", "H": "2017", "J": "2018", "K": "2019",
    "L": "2020", "M": "2021", "N": "2022", "P": "2023", "R": "2024",
    "S": "2025", "T": "2026",
}

VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)

_CHAR_VALUES = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5,
    "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}

_MODEL_TABLE = {("1HG", "CM826"): "Accord"}
_PLANT_TABLE = {("1HG", "A"): "Marysville (OH, USA)"}


def identify_maker(vin: str) -> str:
    if not vin or len(vin) < 3:
        return "Unknown OEM"
    wmi = vin[0:3].upper()
    return WMI_MAKER.get(wmi, f"Unknown OEM (WMI {wmi})")


def model_year_from_char(char: str, is_female: bool = False) -> str:
    code = char.upper()
    return _MODEL_YEAR_CODES.get(code, f"Unknown ({code})")


def _calc_check_digit(vin: str) -> str:
    if len(vin) != 17 or any(ch not in _CHAR_VALUES for ch in vin):
        raise ValueError("vin must be 17 uppercase alphanumeric chars")
    total = 0
    for ch, weight in zip(vin, VIN_WEIGHTS):
        total += _CHAR_VALUES[ch] * weight
    rem = total % 11
    return "X" if rem == 10 else str(rem)


def validate_vin(vin: str) -> bool:
    if not VIN_PATTERN.match(vin):
        return False
    return _calc_check_digit(vin) == vin[8]


def parse_vin(vin: str) -> dict:
    if not validate_vin(vin):
        raise ValueError("invalid VIN")
    vin = vin.upper()
    wmi = vin[0:3]
    model_code = vin[3:8]
    model = _MODEL_TABLE.get((wmi, model_code), model_code)
    plant_code = vin[10]
    plant = _PLANT_TABLE.get((wmi, plant_code), plant_code)
    return {
        "wmi": wmi,
        "manufacturer": identify_maker(vin),
        "model_code": model_code,
        "model": model,
        "year": model_year_from_char(vin[9]),
        "plant_code": plant_code,
        "plant": plant,
        "serial": vin[11:17],
        "check_digit_valid": True,
    }
