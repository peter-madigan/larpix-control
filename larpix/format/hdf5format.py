'''
This module gives access to the LArPix+HDF5 file format.

File format description
=======================

All LArPix+HDF5 files use the HDF5 format so that they
can be read and written using any language that has an HDF5 binding. The
documentation for the Python h5py binding is at <http://docs.h5py.org>.

The ``to_file`` and ``from_file`` methods translate between a list of
Packet-like objects and an HDF5 data file. ``from_file`` can be used to
load up the full file all at once or just a subset of rows (supposing
the full file was too big to fit in memory). To access the data most
efficiently, do not rely on ``from_file`` and instead perform analysis
directly on the HDF5 data file.

File Header
-----------

The file header can be found in the ``/_header`` HDF5 group. At a
minimum, the header will contain the following HDF5 attributes:

    - ``version``: a string containing the LArPix+HDF5 version
    - ``created``: a Unix timestamp of the file's creation time
    - ``modified``: a Unix timestamp of the file's last-modified time

Versions
--------

The LArPix+HDF5 format is self-describing and versioned. This means as
the format evolves, the files themselves will identify which version
of the format should be used to interpret them. When writing a file
with ``to_file``, the format version can be specified, or by default,
the latest version is used. When reading a file with ``from_file``, by
default, the format version of the actual file is used. If a specific
format version is expected or required, that version can be specified,
and a ``RuntimeError`` will be raised if a different format version is
encountered.

The versions are always in the format ``major.minor`` and are stored as
strings (e.g. ``'1.0'``, ``'1.5'``, ``2.0``).

The minor format will increase if a non-breaking change is made, so that
a script compatible with a lower minor version will also work with files
that have a higher minor version. E.g. a script designed to work with
v1.0 will also work with v1.5. The reverse is not necessarily true: a
script designed to work with v1.5 *may not* work with v1.0 files.

The major format will increase if a breaking change is made. This means
that a script designed to work with v1.5 will *likely not* work with
v2.0 files, and vice versa.

File Data
---------

The file data is saved in HDF5 datasets, and the specific data format
depends on the LArPix+HDF5 version.

Version 2.0 description
^^^^^^^^^^^^^^^^^^^^^^^

For version 2.0, there are two dataset: ``packets`` and ``messages``.

The ``packets`` dataset
contains a list of all of the packets sent and received during a
particular time interval.

    - Shape: ``(N,)``, ``N >= 0``

    - Datatype: a compound datatype (called "structured type" in
      h5py/numpy). Not all fields are relevant for each packet. Unused
      fields are set to a default value of 0 or the empty string.
      Keys/fields:

        - ``io_group`` (``u1``/unsigned byte): an id associated with the
          high-level io group associated with this packet

        - ``io_channel`` (``u1``/unsigned byte): the id associated with the
          mid-level io channel associated with this packet

        - ``packet_type`` (``u1``/unsigned byte): the packet type code, which
          can be interpreted according to the map stored in the
          'packets' attribute 'packet_types'

        - ``chip_id`` (``u1``/unsigned byte): the LArPix chip id

        - ``parity`` (``u1``/unsigned byte): the packet parity bit (0 or
          1)

        - ``valid_parity`` (``u1``/unsigned byte): 1 if the packet
          parity is valid (odd), 0 if it is invalid

        - ``downstream_marker`` (``u1``/unsigned byte): a marker to indicate the
          hydra io network direction for this packet

        - ``channel_id`` (``u1``/unsigned byte): the ASIC channel

        - ``timestamp`` (``u8``/unsigned 8-byte long int): the timestamp
          associated with the packet. **Caution**: this field does
          "triple duty" as both the ASIC timestamp in data packets
          (``type`` == 0), as the global timestamp in timestamp
          packets (``type`` == 4), and as the message timestamp in
          message packets (``type`` == 5).

        - ``dataword`` (``u1``/unsigned byte): the ADC data word

        - ``trigger_type`` (``u1``/unsigned byte): the trigger type assciated
          with this packet

        - ``local_fifo` (``u1``/unsigned byte): 1 if the channel FIFO is >50%
          full, 3 if the channel FIFO is 100% full

        - ``shared_fifo`` (``u1``/unsigned byte): 1 if the chip FIFO is >50%
          full, 3 if the channel FIFO is 100% full

        - ``register_address`` (``u1``/unsigned byte): the configuration
          register index

        - ``register_data`` (``u1``/unsigned byte): the configuration register
          value

        - ``direction`` (``u1``/unsigned byte): 0 if packet was sent to
          ASICs, 1 if packet was received from ASICs.

        - ``local_fifo_events`` (``u1``/unsigned byte): number of packets in the
          channel FIFO (only valid if FIFO diagnostics are enabled)

        - ``shared_fifo_events`` (``u1``/unsigned byte): number of packets in the
          chip FIFO (only valid if FIFO diagnostics are enabled)

        - ``counter`` (``u4``/unsigned 4-byte int): the message index (only
          valid for message type packets)

        - ``fifo_diagnostics_enabled`` (``u1``/unsigned byte): flag for when
          fifo diagnostics are enabled (1 if enabled, 0 if not)

    - Packet types lookup: the ``packets`` dataset has an attribute
      ``'packet_types'`` which contains the following lookup table for
      packets::

        0: 'data',
        1: 'test',
        2: 'config write',
        3: 'config read',
        4: 'timestamp',
        5: 'message',

The ``messages`` dataset has the full messages referred to by message
packets in the ``packets`` dataset.

    - Shape: ``(N,)``, ``N >= 0``

    - Datatype: a compound datatype with fields:

        - ``message`` (``S64``/64-character string): the message

        - ``timestamp`` (``u8``/unsigned 8-byte long int): the timestamp
          associated with the message

        - ``index`` (``u4``/unsigned 4-byte int): the message index,
          which should be equal to the row index in the ``messages``
          dataset


Version 1.0 description
^^^^^^^^^^^^^^^^^^^^^^^

For version 1.0, there are two dataset: ``packets`` and ``messages``.

The ``packets`` dataset
contains a list of all of the packets sent and received during a
particular time interval.

    - Shape: ``(N,)``, ``N >= 0``

    - Datatype: a compound datatype (called "structured type" in
      h5py/numpy). Not all fields are relevant for each packet. Unused
      fields are set to a default value of 0 or the empty string.
      Keys/fields:

        - ``chip_key`` (``S32``/32-character string): the chip key
          identifying the ASIC associated with this packet

        - ``type`` (``u1``/unsigned byte): the packet type code, which
          can be interpreted according to the map stored in the
          raw_packet attribute 'packet_types'

        - ``chipid`` (``u1``/unsigned byte): the LArPix chipid

        - ``parity`` (``u1``/unsigned byte): the packet parity bit (0 or
          1)

        - ``valid_parity`` (``u1``/unsigned byte): 1 if the packet
          parity is valid (odd), 0 if it is invalid

        - ``channel`` (``u1``/unsigned byte): the ASIC channel

        - ``timestamp`` (``u8``/unsigned 8-byte long int): the timestamp
          associated with the packet. **Caution**: this field does
          "triple duty" as both the ASIC timestamp in data packets
          (``type`` == 0), as the global timestamp in timestamp
          packets (``type`` == 4), and as the message timestamp in
          message packets (``type`` == 5).

        - ``adc_counts`` (``u1``/unsigned byte): the ADC data word

        - ``fifo_half`` (``u1``/unsigned byte): 1 if the FIFO half full
          flag is present, 0 otherwise.

        - ``fifo_full`` (``u1``/unsigned byte): 1 if the FIFO full flag
          is present, 0 otherwise.

        - ``register`` (``u1``/unsigned byte): the configuration
          register index

        - ``value`` (``u1``/unsigned byte): the configuration register
          value

        - ``counter`` (``u4``/unsigned 4-byte int): the test counter
          value, or the message index. **Caution**: this field does
          "double duty" as the counter for test packets (``type`` == 1)
          and as the message index for message packets (``type`` == 5).

        - ``direction`` (``u1``/unsigned byte): 0 if packet was sent to
          ASICs, 1 if packet was received from ASICs.

    - Packet types lookup: the ``packets`` dataset has an attribute
      ``'packet_types'`` which contains the following lookup table for
      packets::

        0: 'data',
        1: 'test',
        2: 'config write',
        3: 'config read',
        4: 'timestamp',
        5: 'message',

The ``messages`` dataset has the full messages referred to by message
packets in the ``packets`` dataset.

    - Shape: ``(N,)``, ``N >= 0``

    - Datatype: a compound datatype with fields:

        - ``message`` (``S64``/64-character string): the message

        - ``timestamp`` (``u8``/unsigned 8-byte long int): the timestamp
          associated with the message

        - ``index`` (``u4``/unsigned 4-byte int): the message index,
          which should be equal to the row index in the ``messages``
          dataset

Examples
--------

Plot a histogram of ADC counts (selecting packet type to be data packets
only)

>>> import matplotlib.pyplot as plt
>>> import h5py
>>> f = h5py.File('output.h5', 'r')
>>> packets = f['packets']
>>> plt.hist(packets['adc_counts'][packets['type'] == 0])
>>> plt.show()

Load the first 10 packets in a file into Packet objects and print any
MessagePacket packets to the console

>>> from larpix.format.hdf5format import from_file
>>> from larpix.larpix import MessagePacket
>>> result = from_file('output.h5', end=10)
>>> for packet in result['packets']:
...     if isinstance(packet, MessagePacket):
...         print(packet)



'''
import time

import h5py
import numpy as np

from larpix.larpix import Packet_v1, Packet_v2, TimestampPacket, MessagePacket
from larpix.logger import Logger

#: The most recent / up-to-date LArPix+HDF5 format version
latest_version = '1.0'

#: The dtype specification used in the HDF5 files.
#:
#: Structure: ``{version: {dset_name: [structured dtype fields]}}``
dtypes = {
        '0.0': {
            'raw_packet': [
                ('chip_key','S32'),
                ('type','u1'),
                ('chipid','u1'),
                ('parity','u1'),
                ('valid_parity','u1'),
                ('counter','u4'),
                ('channel','u1'),
                ('timestamp','u8'),
                ('adc_counts','u1'),
                ('fifo_half','u1'),
                ('fifo_full','u1'),
                ('register','u1'),
                ('value','u1'),
                ]
            },
        '1.0': { # compatible with v1 packets only
            'packets': [
                ('chip_key','S32'),
                ('type','u1'),
                ('chipid','u1'),
                ('parity','u1'),
                ('valid_parity','u1'),
                ('channel','u1'),
                ('timestamp','u8'),
                ('adc_counts','u1'),
                ('fifo_half','u1'),
                ('fifo_full','u1'),
                ('register','u1'),
                ('value','u1'),
                ('counter','u4'),
                ('direction', 'u1'),
                ],
            'messages': [
                ('message', 'S64'),
                ('timestamp', 'u8'),
                ('index', 'u4'),
                ]
            },
        '2.0': { # compatible with v2 packets and timestamp packets only
            'packets': [
                ('io_group','u1'),
                ('io_channel','u1'),
                ('chip_id','u1'),
                ('packet_type','u1'),
                ('downstream_marker','u1'),
                ('parity','u1'),
                ('valid_parity','u1'),
                ('channel_id','u1'),
                ('timestamp','u8'),
                ('dataword','u1'),
                ('trigger_type','u1'),
                ('local_fifo','u1'),
                ('shared_fifo','u1'),
                ('register_address','u1'),
                ('register_data','u1'),
                ('direction', 'u1'),
                ('local_fifo_events','u1'),
                ('shared_fifo_events','u1'),
                ('counter','u4'),
                ('fifo_diagnostics_enabled','u1'),
                ],
            'messages': [
                ('message', 'S64'),
                ('timestamp', 'u8'),
                ('index', 'u4'),
                ]
            }
        }

#: A map between attribute name and "column index" in the structured
#: dtypes.
#:
#: Structure: ``{version: {dset_name: {field_name: index}}}``
dtype_property_index_lookup = {
        '0.0': {
            'raw_packet': {
                'chip_key': 0,
                'type': 1,
                'chipid': 2,
                'parity': 3,
                'valid_parity': 4,
                'counter': 5,
                'channel': 6,
                'timestamp': 7,
                'adc_counts': 8,
                'fifo_half': 9,
                'fifo_full': 10,
                'register': 11,
                'value': 12,
                }
            },
        '1.0': {
            'packets': {
                'chip_key': 0,
                'type': 1,
                'chipid': 2,
                'parity': 3,
                'valid_parity': 4,
                'channel': 5,
                'timestamp': 6,
                'adc_counts': 7,
                'fifo_half': 8,
                'fifo_full': 9,
                'register': 10,
                'value': 11,
                'counter': 12,
                'direction': 13,
                },
            'messages': {
                'message': 0,
                'timestamp': 1,
                'index': 2,
                }
            },
        '2.0': {
            'packets': {
                'io_group': 0,
                'io_channel': 1,
                'chip_id': 2,
                'packet_type': 3,
                'downstream_marker': 4,
                'parity': 5,
                'valid_parity': 6,
                'channel_id': 7,
                'timestamp': 8,
                'dataword': 9,
                'trigger_type': 10,
                'local_fifo': 11,
                'shared_fifo': 12,
                'register_address': 13,
                'register_data': 14,
                'direction': 15,
                'local_fifo_events': 16,
                'shared_fifo_events': 17,
                'counter': 18,
                'fifo_diagnostics_enabled': 19,
                },
            'messages': {
                'message': 0,
                'timestamp': 1,
                'index': 2,
                }
            }
        }

def to_file(filename, packet_list, mode='a', version=None):
    '''
    Save the given packets to the given file.

    This method can be used to update an existing file.

    :param filename: the name of the file to save to
    :param packet_list: any iterable of objects of type ``Packet`` or
        ``TimestampPacket``.
    :param mode: optional, the "file mode" to open the data file
        (default: ``'a'``)
    :param version: optional, the LArPix+HDF5 format version to use. If
        writing a new file and version is unspecified or ``None``,
        the latest version will be used. If writing an existing file
        and version is unspecified or ``None``, the existing file's
        version will be used. If writing an existing file and version
        is specified and does not exactly match the existing file's
        version, a ``RuntimeError`` will be raised. (default: ``None``)

    '''
    with h5py.File(filename, mode) as f:
        # Create header
        if '_header' not in f.keys():
            if version is None:
                version = latest_version
            header = f.create_group('_header')
            header.attrs['version'] = version
            header.attrs['created'] = time.time()
        else:
            header = f['_header']
            file_version = header.attrs['version']
            if header.attrs['version'] != version:
                raise RuntimeError('Incompatible versions: existing: %s, '
                    'specified: %s' % (file_version, version))
        header.attrs['modified'] = time.time()

        # Create datasets
        if version == '0.0':
            packet_dset_name = 'raw_packet'
        else:
            packet_dset_name = 'packets'
            direction_index = (
                    dtype_property_index_lookup[version]['packets']
                    ['direction'])
            if version == '2.0':
                packet_type_index = (
                        dtype_property_index_lookup[version]['packets']
                        ['packet_type'])
                fifo_diagnostics_enabled_index = (
                        dtype_property_index_lookup[version]['packets']
                        ['fifo_diagnostics_enabled'])
        packet_dtype = dtypes[version][packet_dset_name]
        if packet_dset_name not in f.keys():
            packet_dset = f.create_dataset(packet_dset_name, shape=(len(packet_list),),
                    maxshape=(None,), dtype=packet_dtype)
            packet_dset.attrs['packet_types'] = '''
0: 'data',
1: 'test',
2: 'config write',
3: 'config read',
4: 'timestamp',
5: 'message',
'''
            start_index = 0
        else:
            packet_dset = f[packet_dset_name]
            start_index = packet_dset.shape[0]
            packet_dset.resize(start_index + len(packet_list), axis=0)
        if version != '0.0':
            message_dset_name = 'messages'
            message_dtype = dtypes[version][message_dset_name]
            if message_dset_name not in f.keys():
                message_dset = f.create_dataset(message_dset_name,
                        shape=(0,), maxshape=(None,),
                        dtype=message_dtype)
                message_start_index = 0
            else:
                message_dset = f[message_dset_name]
                message_start_index = message_dset.shape[0]

        # Fill dataset
        encoded_packets = []
        messages = []
        for i, packet in enumerate(packet_list):
            dict_rep = packet.export()
            encoded_packet = [
                dict_rep.get(key, b'') if val_type[0] == 'S'  # string
                    else dict_rep.get(key, 0) for key, val_type in
                    packet_dtype]
            if 'direction' in dict_rep:
                encoded_packet[direction_index] = {
                        Logger.WRITE: 0,
                        Logger.READ: 1}[encoded_packet[direction_index]]
            if version == '2.0':
                if isinstance(packet, (Packet_v1)):
                    raise ValueError('version 2.0 hdf5format is incompatible with v1 packets')
                if isinstance(packet, (TimestampPacket,MessagePacket)):
                    encoded_packet[packet_type_index] = packet.packet_type
                elif packet.fifo_diagnostics_enabled:
                    encoded_packet[fifo_diagnostics_enabled_index] = 1
                for idx in range(len(encoded_packet)):
                    if encoded_packet[idx] is None:
                        encoded_packet[idx] = 0

            encoded_packets.append(tuple(encoded_packet))
            if isinstance(packet, MessagePacket):
                messages.append((packet.message, packet.timestamp,
                    message_start_index + len(messages)))


        packet_dset[start_index:] = encoded_packets
        if version != '0.0':
            message_dset.resize(message_start_index + len(messages), axis=0)
            message_dset[message_start_index:] = messages

def from_file(filename, version=None, start=None, end=None):
    '''
    Read the data from the given file into LArPix Packet objects.

    :param filename: the name of the file to read
    :param version: the format version. Specify this parameter to
        enforce a version check. When a specific version such as
        ``'1.5'`` is specified, a ``RuntimeError`` will be raised if the
        stored format version number is not an exact match. If a version
        is prefixed with ``'~'`` such as ``'~1.5'``, a ``RuntimeError``
        will be raised if the stored format version is *incompatible*
        with the specified version. Compatible versions are those with
        the same major version and at least the same minor version. E.g.
        for ``'~1.5'``, versions between v1.5 and v2.0 are compatible.
        If unspecified or ``None``, will use the stored format version.
    :param start: the index of the first row to read
    :param end: the index after the last row to read (same semantics as
        Python ``range``)
    :returns packet_dict: a dict with keys ``'packets'`` containing a
        list of packet objects; and ``'created'``, ``'modified'``, and
        ``'version'``, containing the file metadata.

    '''
    with h5py.File(filename, 'r') as f:
        file_version = f['_header'].attrs['version']
        if version is None:
            version = file_version
        elif version[0] == '~':
            file_major, _, file_minor = file_version.split('.')
            version_major, _, version_minor = version.split('.')
            version_major = version_major[1:]
            if (file_major != version_major
                    or file_minor < version_minor):
                raise RuntimeError('Incompatible versions: existing: %s, '
                    'specified: %s' % (file_version, version))
            else:
                version = file_version
        elif version == file_version:
            pass
        else:
            raise RuntimeError('Incompatible versions: existing: %s, '
                'specified: %s' % (file_version, version))

        if version not in dtypes:
            raise RuntimeError('Unknown version: %s' % version)

        if version == '0.0':
            dset_name = 'raw_packet'
        else:
            dset_name = 'packets'
            message_dset_name = 'messages'
            message_props = (
                    dtype_property_index_lookup[version][message_dset_name])
            message_dset = f[message_dset_name]
        props = dtype_property_index_lookup[version][dset_name]
        packets = []
        if start is None and end is None:
            dset_iter = f[dset_name]
        else:
            dset_iter = f[dset_name][start:end]
        for row in dset_iter:
            # TimestampPackets
            if (version in ('0.0','1.0') and row[props['type']] == 4) or \
            (version == '2.0' and row[props['packet_type']] == 4):
                packets.append(TimestampPacket(row[props['timestamp']]))
                continue
            # MessagePackets
            if (version in ('0.0','1.0') and row[props['type']] == 5) or \
            (version == '2.0' and row[props['packet_type']] == 5):
                index = row[props['counter']]
                message_row = message_dset[index]
                message = message_row[message_props['message']].decode()
                timestamp = row[props['timestamp']]
                packets.append(MessagePacket(message, timestamp))
                continue
            # LArPix Packets
            if version in ('0.0', '1.0'):
                p = Packet_v1()
                p.chip_key = row[props['chip_key']]
                p.packet_type = row[props['type']]
                p.chipid = row[props['chipid']]
                p.parity_bit_value = row[props['parity']]
                if p.packet_type == Packet_v1.DATA_PACKET:
                    p.channel = row[props['channel']]
                    p.timestamp = row[props['timestamp']]
                    p.dataword = row[props['adc_counts']]
                    p.fifo_half_flag = row[props['fifo_half']]
                    p.fifo_full_flag = row[props['fifo_full']]
                elif p.packet_type == Packet_v1.TEST_PACKET:
                    p.counter = row[props['counter']]
                elif (p.packet_type == Packet_v1.CONFIG_WRITE_PACKET
                        or p.packet_type == Packet_v1.CONFIG_READ_PACKET):
                    p.register_address = row[props['register']]
                    p.register_data = row[props['value']]
                if version != '0.0':
                    p.direction = row[props['direction']]
                packets.append(p)
            else:
                p = Packet_v2()
                p.io_group = row[props['io_group']]
                p.io_channel = row[props['io_channel']]
                p.chip_id = row[props['chip_id']]
                p.packet_type = row[props['packet_type']]
                p.downstream_marker = row[props['downstream_marker']]
                p.parity = row[props['parity']]
                p.valid_parity = row[props['valid_parity']]
                p.direction = row[props['direction']]
                if p.packet_type == Packet_v2.DATA_PACKET:
                    p.channel_id = row[props['channel_id']]
                    p.timestamp = row[props['timestamp']]
                    p.dataword = row[props['dataword']]
                    p.trigger_type = row[props['trigger_type']]
                    p.local_fifo = row[props['local_fifo']]
                    p.shared_fifo = row[props['shared_fifo']]
                    if row[props['fifo_diagnostics_enabled']] != 0:
                        p.fifo_diagnostics_enabled = True
                        p.local_fifo = row[props['local_fifo_events']]
                        p.shared_fifo = row[props['shared_fifo_events']]
                        p.timestamp = row[props['timestamp']]
                elif p.packet_type in (Packet_v2.CONFIG_READ_PACKET, Packet_v2.CONFIG_WRITE_PACKET):
                    p.register_address = row[props['register_address']]
                    p.register_data = row[props['register_data']]
                packets.append(p)
        return {
                'packets': packets,
                'created': f['_header'].attrs['created'],
                'modified': f['_header'].attrs['modified'],
                'version': f['_header'].attrs['version'],
                }