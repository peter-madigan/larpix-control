'''
Quickstart commands for test boards
'''

from __future__ import absolute_import
from __future__ import print_function
import sys
import warnings
import copy

import larpix.larpix as larpix
from larpix.io.serialport import SerialPort, enable_logger
from larpix.io.zmq_io import ZMQ_IO
from larpix.logger.h5_logger import HDF5Logger

## For interactive mode
VERSION = sys.version_info
if VERSION[0] < 3:
    input = raw_input
##

#List of LArPix test board configurations
board_info_list = [
    {'name':'unknown',
     'file':None,
     'chip_list':[('0-{}'.format(chip_id), chip_id) for chip_id in range(0,256)],},
    {'name':'pcb-1',
     'file':'controller/pcb-1_chip_info.json'},
    {'name':'pcb-2',
     'file':'controller/pcb-2_chip_info.json'},
    {'name':'pcb-3',
     'file':'controller/pcb-3_chip_info.json'},
    {'name':'pcb-4',
     'file':'controller/pcb-4_chip_info.json'},
    {'name':'pcb-5',
     'file':'controller/pcb-5_chip_info.json'},
     {'name':'pcb-6',
     'file':'controller/pcb-6_chip_info.json'},
    {'name':'pcb-10',
     'file':'controller/pcb-10_chip_info.json'}
]
#Create handy map by board name
board_info_map = dict([(elem['name'],elem) for elem in board_info_list])

def create_controller(io=None, logger=None, **kwargs):
    '''
    Create a default controller

    :param io: `larpix.io.IO` object to be added to the controller

    :param logger: `larpix.logger.Logger` object to be added to the controller

    :returns: default `larpix.larpix.Controller`

    '''
    c = larpix.Controller()
    c.io = io
    c.logger = logger
    if c.logger:
        logger.open()
    return c

def init_controller(controller, board='unknown', safe=True):
    '''
    Initialize controller using internal list of named boards

    :param controller: controller to initialize

    :param board: string from `quickstart.board_info_map.keys()`

    :param safe: flag to check chip keys against `controller.io`

    :returns: `controller` with chips initialized

    '''
    if not board in board_info_map.keys():
        board = 'unknown'
    board_info = board_info_map[board]
    if board_info['file']:
        controller.load(board_info['file'], safe=True)
    else:
        warnings.warn('unknown board, initializing with serious assumptions '
            'about your setup!')
        for chip_info in board_info['chip_list']:
            controller.add_chip(*chip_info, safe=safe)
    controller.board_info = board_info
    return controller

def silence_chips(controller, interactive=False):
    '''
    Silence all chips in controller by maximizing the global threshold

    :param controller: controller of chips to silence

    :param interactive: flag to request input between silencing chips

    '''
    for chip_key in controller.chips:
        chip = controller.get_chip(chip_key)
        if interactive:
            print('Silencing chip %d' % chip.chip_id)
        chip.config.global_threshold = 255
        controller.write_configuration(chip_key, chip.config.global_threshold_address)
        if interactive:
            input('Just silenced chip %d. <enter> when ready.\n' % chip.chip_id)

def disable_chips(controller):
    '''
    Disable all chips in controller by masking all channels

    :param controller: controller of chips to disable

    '''
    controller.disable()

def set_config(controller, config='chip/default.json', interactive=False):
    '''
    Set the chips to a specified configuration

    :param controller: controller of chips to configure

    :param config: path to configuration file to use for configuration

    :param interactive: flag to request input between configuring chips

    '''
    for chip_key in controller.chips:
        chip = controller.get_chip(chip_key)
        if interactive:
            x = input('Configuring chip %d. <enter> to continue, q to quit' % chip.chip_id)
            if x == 'q':
                break
        prev_config = copy.deepcopy(chip.config)
        chip.config.load(config)
        addresses = [diff[0] for diff in chip.config.compare(prev_config).values()]
        print('modifying registers: {}'.format(addresses))
        controller.write_configuration(chip_key, addresses)
        print('configured chip {}'.format(str(chip)))

def set_config_physics(controller, interactive=False):
    '''
    Set the chips for the default physics configuration

    :param controller: controller of chips to configure

    :param interactive: flag to request input between configuring chips

    '''
    return set_config(controller, config='chip/physics.json', interactive=interactive)

def flush_stale_data(controller, time=1):
    '''
    Read and discard contents, useful for flushing any data that may exist in
    system buffers

    :param controller: controller to flush

    :param time: open communications `time` seconds

    '''
    controller.run(time,'flush_buffer')
    del controller.reads[-1]

def get_chip_ids(**settings):
    '''
    Return a list of Chip objects representing the chips on the board.

    Checks if a chip is present by adjusting one channel's pixel trim
    threshold and checking to see that the correct configuration is read
    back in.

    '''
    warnings.warn("This method is now deprecated since it relies on Controller.all_chips",
        DeprecationWarning)
    logger = logging.getLogger(__name__)
    logger.info('Executing get_chip_ids')
    if 'controller' in settings:
        controller = settings['controller']
    else:
        controller = larpix.Controller(settings['port'])
    controller.use_all_chips = True
    stored_timeout = controller.timeout
    controller.timeout=0.1
    chips = {}
    chip_regs = [(c.chip_key, 0) for c in controller.all_chips]
    controller.multi_read_configuration(chip_regs, timeout=0.1)
    for chip_key in controller.all_chips:
        chip = controller.get_chip(chip_key)
        if len(chip.reads) == 0:
            print('Chip ID %d: No packet recieved' %
                  chip.chip_id)
            continue
        if len(chip.reads[0]) != 1:
            print('Cannot determine if chip %d exists because more'
                    'than 1 packet was received (expected 1)' %
                    chip.chip_id)
            continue
        if chip.reads[0][0].register_data != 0:
            chips.append(chip)
            logger.info('Found chip %s' % chip)
    controller.timeout = stored_timeout
    controller.use_all_chips = False
    return chips

def quickcontroller(board='pcb-1', interactive=False, io=None, logger=None,
    log_filepath=None):
    '''
    Quick jump through all controller creation and config steps

    :param board: board name from `quickstart.board_info_map.keys()`

    :param interactive: flag to request input between actions

    :param io: `larpix.io.IO` object to use when creating controller. If none, try to resolve a ZMQ_IO address

    :param logger: `larpix.logger.Logger` object to use when creating controller. If none, use a default HDF5Logger

    :param log_filepath: only to be used if no logger is specified, sets the log path to a non-default value

    '''
    if io is None:
        io = ZMQ_IO('tcp://localhost')
        # io = SerialPort(baudrate=1000000,
            # timeout=0.01)
    enable_logger()
    if logger is None:
        cont.logger = HDF5Logger(filename=log_filepath)
    cont = create_controller(io=io, logger=logger)
    init_controller(cont, board)
    silence_chips(cont, interactive)
    if cont.board_info['name'] == 'unknown':
        # Find and load chip info
        settings = {'controller':cont}
        cont.chips = get_chip_ids(**settings)
    set_config_physics(cont, interactive)
    #flush_stale_data(cont)
    return cont

# Short-cut handle
qc = quickcontroller

