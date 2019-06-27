import time
import zmq
import sys
from collections import defaultdict

from larpix.io import IO
from larpix.larpix import Packet
from larpix.configs import load
from larpix.format.message_format import dataserver_message_decode

class MultiZMQ_IO(IO):
    '''
    The MultiZMQ_IO object interfaces with a network of Bern LArPix v2 modules
    using Igor's ZeroMQ communications protocol.

    This object handles the required communications, and also has extra
    methods for additional functionality, including system reset, packet
    count, clock frequency, and more.

    By default, when creating a MultiZMQ_IO object, the ``io/default.json``
    configuration will attempt to be loaded unless otherwise specified. The path relative to the pwd is checked first,
    followed by the path of the larpix-control installation.

    '''
    _valid_config_classes = ['MultiZMQ_IO']

    def __init__(self, addresses, config_filepath=None):
        super(MultiZMQ_IO, self).__init__()
        if not isinstance(addresses, list):
            raise ValueError('MultiZMQ_IO must be instaniated with a list of '
                'board addresses')
        self.load(config_filepath)

        self.context = zmq.Context()
        self.senders = {}
        self.senders_lookup = {}
        self.receivers = {}
        self.receivers_lookup = {}
        for address in addresses:
            self.senders[address] = self.context.socket(zmq.REQ)
            self.receivers[address] = self.context.socket(zmq.SUB)
            self.senders_lookup[self.senders[address]] = address
            self.receivers_lookup[self.receivers[address]] = address
        self.hwm = 20000
        for receiver in self.receivers.values():
            receiver.set_hwm(self.hwm)
        for address in self.senders.keys():
            send_address = 'tcp://' + address + ':5555'
            receive_address = 'tcp://' + address + ':5556'
            self.senders[address].connect(send_address)
            self.receivers[address].connect(receive_address)
        self._sender_replies = defaultdict(list)
        self.poller = zmq.Poller()
        for receiver in self.receivers.values():
            self.poller.register(receiver, zmq.POLLIN)

    @property
    def sender_replies(self):
        return self._sender_replies
    @sender_replies.setter
    def sender_replies(self, val):
        self._sender_replies = val

    def send(self, packets):
        self.sender_replies = defaultdict(list)
        send_time = time.time()
        addresses = [MultiZMQ_IO.parse_chip_key(packet.chip_key)['address'] for packet in packets]
        msg_datas = MultiZMQ_IO.encode(packets)
        for address, msg_data in zip(addresses, msg_datas):
            tosend = b'SNDWORD ' + msg_data
            self.senders[address].send(tosend)
            self.sender_replies[address].append(self.senders[address].recv())

    def start_listening(self):
        if self.is_listening:
            raise RuntimeError('Already listening')
        super(MultiZMQ_IO, self).start_listening()
        for receiver in self.receivers.values():
            receiver.setsockopt(zmq.SUBSCRIBE, b'')

    def stop_listening(self):
        if not self.is_listening:
            raise RuntimeError('Already not listening')
        super(MultiZMQ_IO, self).stop_listening()
        for receiver in self.receivers.values():
            receiver.setsockopt(zmq.UNSUBSCRIBE, b'')

    def parse_chip_key(self, key):
        '''
        Decodes a chip key into ``'chip_id'``, ``'io_chain'``, and ``'address'``

        :returns: ``dict`` with keys ``('chip_id', 'io_chain', 'addresss')``
        '''
        return_dict = {}
        return_dict['chip_id'] = key.chip_id
        return_dict['io_chain'] = key.io_channel - 1
        return_dict['address'] = self._io_group_table[key.io_group]
        return return_dict

    def generate_chip_key(self, **kwargs):
        '''
        Generates a valid ``MultiZMQ_IO`` chip key

        :param chip_id: ``int`` corresponding to internal chip id

        :param io_chain: ``int`` corresponding to daisy chain number

        :param address: ``str`` corresponding to the address of the DAQ board

        '''
        req_fields = ('chip_id', 'io_chain', 'address')
        if not all([key in kwargs for key in req_fields]):
            raise ValueError('Missing fields required to generate chip id'
                ', requires {}, received {}'.format(req_fields, kwargs.keys()))
        if not isinstance(kwargs['chip_id'], int):
            raise ValueError('chip_id must be int')
        if not isinstance(kwargs['io_chain'], int):
            raise ValueError('io_chain must be int')
        if not isinstance(kwargs['address'], str):
            raise ValueError('address must be str')
        return Key.from_dict(dict(
                io_group = kwargs['address'],
                io_channel = kwargs['io_chain'] + 1,
                chip_id = kwargs['chip_id']
            ))

    def decode(self, msgs, address, **kwargs):
        '''
        Convert a list ZMQ messages into packets

        '''
        return dataserver_message_decode(msgs, key_generator=self.generate_chip_key, version=(1,0), address=address, **kwargs)

    def encode(self, packets):
        '''
        Encode a list of packets into ZMQ messages
        '''
        msg_data = []
        if sys.version_info[0] < 3:
            msg_data = [b'0x00%s %d' % (packet.bytes()[::-1].encode('hex'), self.parse_chip_key(packet.chip_key)['io_chain']) for packet in packets]
        else:
            msg_data = [b'0x00%s %d' % (packet.bytes()[::-1].hex().encode(), self.parse_chip_key(packet.chip_key)['io_chain'])for packet in packets]
        return msg_data

    def empty_queue(self):
        '''
        Process any awaiting messages from all ZMQ connections. Will continue
        to read until the `hwm` is reached or there are no more awaiting messages.

        :returns: 2-`tuple` containing a list of received packets and the full bytestream
        '''
        packets = []
        bytestream_list = []
        bytestream = b''
        n_recv = 0
        read_time = time.time()
        while self.poller.poll(0) and n_recv < self.hwm:
            events = dict(self.poller.poll(0))
            for socket, n_events in events.items():
                for _ in range(n_events):
                    message = socket.recv()
                    n_recv += 1
                    bytestream_list.append(message)
                    address = self.receivers_lookup[socket]
                    packets += self.decode([message], address=address)
        #print('len(bytestream_list) = %d' % len(bytestream_list))
        bytestream = b''.join(bytestream_list)
        return packets, bytestream

    def reset(self, addresses=None):
        '''
        Send a reset pulse to the LArPix ASICs.

        :param addresses: ``list`` of daq board addresses to reset, if ``None`` reset all addresses

        '''
        if addresses is None:
            return self.reset(addresses=self.senders.keys())

        for address in addresses:
            self.senders[address].send(b'SYRESET')
        return_dict = {}
        for address in addresses:
            return_dict[address] = self.senders[address].recv()
        return return_dict

    def set_clock(self, freq_khz, addresses=None):
        '''
        Set the LArPix CLK2X freqency (in kHz).

        :param freq_khz: CLK2X freq in khz to set

        :param addresses: ``list`` of daq board addresses to change frequency, if ``None`` modifies all addresses

        '''
        if addresses is None:
            return self.set_clock(freq_khz, addresses=self.senders.keys())

        for address in addresses:
            self.senders[address].send(b'SETFREQ %s' % hex(freq_khz).encode())
        return_dict = {}
        for address in addresses:
            return_dict[address] = self.senders[address].recv()
        return return_dict

    def set_testpulse_freq(self, divisor, address):
        '''
        Set the testpulse frequency, computed by dividing the CLK2X
        frequency by ``divisor``.

        :param divisor: test pulse frequency divisor

        :param address: daq board addresses to change test pulse freq

        '''
        self.senders[address].send(b'SETFTST %s' % hex(divisor).encode())
        return self.senders[address].recv()

    def get_packet_count(self, io_channel, address):
        '''
        Get the number of packets received, as determined by the number
        of UART "start" bits processed.

        :param io_channel: IO channel to check

        :param address: address of daq board

        '''
        self.senders[address].send(b'GETSTAT %d' % io_channel)
        result = self.senders[address].recv()
        space = result.find(b' ')
        number = int(result[:space])
        return number

    def ping(self, addresses=None):
        '''
        Send a ping to the system.

        :param addresses: ``list`` of daq board addresses to ping, if ``None`` ping all addresses

        :returns: ``dict`` with one entry per address. Value is ``True`` if first two bytes of the response are b'OK'.

        '''
        if addresses is None:
            return self.ping(addresses=self.senders.keys())

        for address in addresses:
            self.senders[address].send(b'PING_HB')
        result = {}
        for address in addresses:
            received_msg = self.senders[address].recv()
            result[address] = received_msg[:2] == b'OK'
        return result

    def cleanup(self):
        '''
        Close the ZMQ objects to prevent a memory leak.

        This method is only required if you plan on instantiating a new
        ``MultiZMQ_IO`` object.

        '''
        for address in addresses:
            self.senders[address].close(linger=0)
            self.receivers[address].close(linger=0)
            self.context.term()
