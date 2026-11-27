import struct

import pymem
import pymem.process


def open_read_only_process(name):
    process = pymem.process.process_from_name(name, exact_match=True)
    if process is None:
        raise pymem.exception.ProcessNotFound(name)

    access = pymem.ressources.structure.PROCESS
    handle = pymem.process.open(
        process.th32ProcessID,
        debug=False,
        process_access=access.PROCESS_QUERY_INFORMATION.value
        | access.PROCESS_VM_READ.value,
    )
    if not handle:
        raise pymem.exception.CouldNotOpenProcess(process.th32ProcessID)

    reader = pymem.Pymem()
    reader.process_id = process.th32ProcessID
    reader.process_handle = handle
    return reader


def get_address(pm, chain):
    """
    Resolves a memory address by following a pointer chain.

    Args:
        pm (pymem.Pymem): An instance of Pymem to interact with the process memory.
        chain (tuple): A tuple containing:
            - module_name (str): The name of the module where the base address is located.
            - base_offset (int): The offset from the module base.
            - offsets (list[int]): A list of offsets to traverse.

    Returns:
        int or None: The resolved memory address, or None if an error occurs.
    """
    module_name, base_offset, offsets = chain

    try:
        module_base = pymem.process.module_from_name(
            pm.process_handle, module_name
        ).lpBaseOfDll
        address = module_base + base_offset
        for offset in offsets:
            address = (
                pm.read_longlong(address) + offset
            )  # Read 8-byte pointer at address
        return address

    except Exception as e:
        print(f"Error reading memory: {e}")
        return None


def read_game_memory(pm, address, data_type, *, raise_on_error=False):
    """
    Reads a value from the specified memory address.

    Args:
        pm (pymem.Pymem): An instance of Pymem to interact with the process memory.
        address (int): The memory address to read from.
        data_type (str): The type of data to read. Supported types:
            - 'int' (4-byte integer)
            - 'float' (4-byte float)
            - 'long' (4-byte integer)
            - 'long long' (8-byte integer)
            - 'BE_float' (4-byte big-endian float)
            - 'BE_int' (4-byte big-endian integer)

    Returns:
        int, float, or None: The value read from memory, or None if an error occurs.
    """
    try:
        if data_type == "int":
            return pm.read_int(address)  # 4-byte integer
        elif data_type == "float":
            return pm.read_float(address)  # 4-byte float
        elif data_type == "long":
            return pm.read_long(address)  # 4-byte integer
        elif data_type == "long long":
            return pm.read_longlong(address)  # 8-byte integer
        elif data_type == "BE_float":  # Big-endian float (4 bytes)
            raw_data = pm.read_bytes(address, 4)
            return struct.unpack(">f", raw_data)[0]
        elif data_type == "BE_int":  # Big-endian integer (4 bytes)
            raw_data = pm.read_bytes(address, 4)
            return struct.unpack(">i", raw_data)[0]
        else:
            raise ValueError(
                f"Unsupported data type specified for reading: {data_type}"
            )

    except Exception as e:
        if raise_on_error:
            raise
        print(f"Error reading memory: {e}")
        return None


def find_memory_address(pm, address):
    """
    Searches memory for occurrences of a specific 8-byte memory address,
    formatted as raw bytes (in \\x{byte:02x} format).

    Args:
        pm (pymem.Pymem): An instance of Pymem to interact with the process memory.
        address (int): The memory address to search for.

    Returns:
        list[int]: A list of memory addresses where the given address pattern was found.
    """
    # Convert the address to little-endian 8-byte format
    address_bytes = address.to_bytes(8, byteorder="little")
    pattern_bytes = rb"".join(f"\\x{byte:02x}".encode() for byte in address_bytes)

    # Search the memory for the formatted byte pattern
    return pm.pattern_scan_all(pattern_bytes, return_multiple=True)
