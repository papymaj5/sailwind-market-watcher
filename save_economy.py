"""Read balances and exchange rates from a Sailwind 0.41 save."""

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

SAVE_DIRECTORY = Path.home() / "AppData" / "LocalLow" / "Raw Lion Workshop" / "Sailwind"
REGIONAL_CURRENCIES = ("Al'Ankh Lions", "Emerald Dragons", "Aestrin Crowns")
CURRENCY_ORDER = (*REGIONAL_CURRENCIES, "Gold Lions")
EXCHANGE_MULTIPLIER = 0.99
MAX_SAVE_BYTES = 64 * 1024 * 1024


class SaveReader:
    def __init__(self, data):
        self.data = data
        self.position = 0

    def read(self, size):
        end = self.position + size
        if end > len(self.data):
            raise ValueError("Incomplete save.")
        result = self.data[self.position : end]
        self.position = end
        return result

    def byte(self):
        return self.read(1)[0]

    def integer(self):
        return struct.unpack("<i", self.read(4))[0]

    def string(self):
        length = 0
        for shift in range(0, 35, 7):
            part = self.byte()
            length |= (part & 127) << shift
            if part < 128:
                return self.read(length).decode("utf-8")
        raise ValueError("Invalid save string length.")

    def expect(self, value):
        if self.byte() != value:
            raise ValueError("Unrecognized Sailwind save format.")


@dataclass
class SaveEconomy:
    rates: dict[str, float] = field(default_factory=dict)
    balances: dict[str, int] = field(default_factory=dict)


def read_primitive_array(data, offset, array_id, kind, fmt):
    # ArraySinglePrimitive: object ID, length, and primitive element type.
    header = struct.pack("<BiiB", 15, array_id, 4, kind)
    start = data.find(header, offset)
    if start < 0 or data.find(header, start + 1) >= 0:
        raise ValueError("Could not identify a currency array.")
    start += len(header)
    if start + struct.calcsize(fmt) > len(data):
        raise ValueError("Incomplete currency array.")
    return struct.unpack_from(fmt, data, start)


def read_save_economy(data):
    reader = SaveReader(data)
    reader.expect(0)  # SerializedStreamHeader
    root_id = reader.integer()
    reader.read(12)
    reader.expect(12)  # BinaryLibrary
    reader.integer()
    reader.string()
    reader.expect(5)  # ClassWithMembersAndTypes
    if reader.integer() != root_id or reader.string() != "SaveContainer":
        raise ValueError("Missing Sailwind save root.")
    count = reader.integer()
    if not 1 <= count <= 256:
        raise ValueError("Invalid save field count.")
    names = [reader.string() for _ in range(count)]
    types = reader.read(count)
    primitive_types = {}
    for index, kind in enumerate(types):
        if kind in (0, 7):
            primitive_types[index] = reader.byte()
        elif kind in (3, 4):
            reader.string()
            if kind == 4:
                reader.integer()
        elif kind not in (1, 2, 5, 6):
            raise ValueError("Invalid save field type.")
    reader.integer()  # Library ID

    array_types = {"currencyRates": 11, "playerCurrency": 8}
    references = {}
    for index, (name, kind) in enumerate(zip(names, types)):
        if name in array_types:
            if kind != 7 or primitive_types[index] != array_types[name]:
                raise ValueError("Unexpected currency field type.")
            reader.expect(9)  # MemberReference
            references[name] = reader.integer()
            if len(references) == len(array_types):
                break
            continue
        if kind == 0 and primitive_types[index] in (8, 11):
            reader.read(4)
        elif kind != 0:
            record = reader.byte()
            if record == 9:
                reader.integer()
            elif record != 10:  # ObjectNull
                raise ValueError("Unsupported field before currency rates.")
        else:
            raise ValueError("Unsupported primitive before currency rates.")
    else:
        raise ValueError("Missing currency fields in this save.")

    *regional, gold = read_primitive_array(
        data, reader.position, references["currencyRates"], 11, "<4f"
    )
    balances = read_primitive_array(
        data, reader.position, references["playerCurrency"], 8, "<4i"
    )
    if not all(math.isfinite(value) and value > 0 for value in (*regional, gold)):
        raise ValueError("Invalid currency rates.")
    rates = {
        currency: round(rate / gold * EXCHANGE_MULTIPLIER, 5)
        for currency, rate in zip(REGIONAL_CURRENCIES, regional)
    }
    if any(balance < 0 for balance in balances):
        raise ValueError("Invalid currency balances.")
    return SaveEconomy(rates, dict(zip(CURRENCY_ORDER, balances)))


class SavedGameEconomy:
    def __init__(self, directory=SAVE_DIRECTORY):
        self.directory = directory
        self._source = None
        self._economy = SaveEconomy()

    def read(self):
        try:
            slots = [
                path
                for path in self.directory.glob("slot*.save")
                if path.stem[4:].isdigit() and path.is_file()
            ]
            if len(slots) != 1:
                hint = "Multiple saves found." if slots else "No Sailwind save found."
                return SaveEconomy(), hint
            path = slots[0]
            before = path.stat()
            source = (path, before.st_mtime_ns, before.st_size)
            if source == self._source:
                return self._economy, path.name
            with path.open("rb") as file:
                data = file.read(MAX_SAVE_BYTES + 1)
            after = path.stat()
            if (
                len(data) != before.st_size
                or after.st_size != before.st_size
                or after.st_mtime_ns != before.st_mtime_ns
                or len(data) > MAX_SAVE_BYTES
            ):
                return SaveEconomy(), "Save is changing or too large."
            economy = read_save_economy(data)
        except (OSError, ValueError):
            return SaveEconomy(), "Could not read or parse the Sailwind save."
        self._source, self._economy = source, economy
        return economy, path.name
