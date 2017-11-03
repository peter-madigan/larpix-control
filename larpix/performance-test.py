'''
This module contains methods for setting up and running performance tests of
the larpix ADC and CSA

'''
import logging
import larpix.larpix as larpix
from bitstring import BitArray

def setup_logger(settings):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logfile = settings['logfile']
    handler = logging.FileHandler(logfile)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: '
            '%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def configure_chips(settings):
    '''
    Set up chips for testing.

    '''
    logger = logging.getLogger(__name__)
    logger.info('Configuring chips')
    port = settings['port']
    outfile = settings['outfile']
    controller = larpix.Controller(port)
    for chipargs in chipset:
        chip = larpix.Chip(*chipargs)
        controller.chips.append(chip)
        
    errorcode = 0
    for chip in controller.chips:
        chip.config.csa_testpulse_dac = 0
        chip.config.enable_testpulse()
        read_data = controller.write_configuration(chip)
        read_data = controller.read_configuration(chip)
        if not( chip.config.to_dict() is chip.export_reads() ):
            logger.error(' - Configuration of chip id:%d io:%d failed' %
                         chip.chip_id, chip.io_chain)
            errorcode = 1
        else:
            logger.info('Chip id:%d io:%d configured successfully')
            chip.config.write(outfile, append=True)

    if errorcode == 0:
        logger.info('All chips configured successfully')
    else:
        logger.error(' - Chip configuration failed')
    return errorcode
                            
def csa_noise_test(settings):
    '''
    
    '''
    
def adc_linearity_test(settings):
    '''

    '''

if __name__ == '__main__':
    import argparse
    import sys
    tests = {
            'adc_linearity_test': pcb_io_test,
            'csa_noise_test': io_loopback_test
            }
    parser = argparse.ArgumentParser()
    parser.add_argument('--logfile', default='performance-test.log',
            help='the logfile to save')
    parser.add_argument('-p', '--port', default='/dev/ttyUSB1',
            help='the serial port')
    parser.add_argument('-l', '--list', action='store_true',
            help='list available tests')
    parser.add_argument('-t', '--test', nargs='+', default=tests.keys(),
            help='specify test(s) to run')
    parser.add_argument('--chipid', nargs='*', type=int,
            help='list of chip IDs to test')
    parser.add_argument('--iochain', nargs='*', type=int,
            help='list of IO chain IDs (corresponding to chipids')
    parse.add_argument('-f', '--outfile', default='performance-data.json',
            help='output data file path')
    args = parser.parse_args()
    if args.list:
        print('\n'.join(tests.keys()))
        sys.exit(0)
    if args.chipid and args.iochain:
        chipset = list(zip(args.chipid, args.iochain))
    else:
        chipset = None
    settings = {
            'port': args.port,
            'chipset': chipset,
            'logfile': args.logfile,
            'outfile': args.outfile    
            }
    setup_logger({})
    logger = logging.getLogger(__name__)
    try:
        for test in args.test:
            tests[test](settings)
    except Exception as e:
        logger.error('Error during test', exc_info=True)
