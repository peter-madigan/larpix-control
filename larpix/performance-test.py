import sys
import logging
import larpix

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

def progress_bar(i, n):
    if ( i < n ):
        progress_str = '[' + '|' * int(i/10.) + ' ' * int((n-i)/10.) + ']'
        print '\rProgress: %s' % progress_str,
        sys.stdout.flush()
    else:
        print 'Done!'

def configure_chips(settings):
    '''
    Set up chips for performance testing.

    '''
    logger = logging.getLogger(__name__)
    logger.info('Configuring chips')
    port = settings['port']
    chipset = settings['chipset']
    outfile = settings['outfile'].replace('.json','_config.json')
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
        #if not chip.config is read_data:
        #    logger.error(' - Configuration of chip id:%d io:%d failed' %
        #            chip.chip_id, chip.io_chain)
        #    errorcode = 1
        #else:
        logger.info('Chip id:%d io:%d configured successfully')

    if errorcode == 0:
        logger.info('All chips configured successfully, configuration saved to %s' % outfile)

    else:
        logger.error(' - Chip configuration failed')
    return errorcode

def csa_noise_test(settings):
    '''
    Scans through chipset letting each run for 1sec each.
    Saves recorded data to <outfile>_csa-noise.json

    '''
    logger = logging.getLogger(__name__)
    logger.info('Performing noise test')
    errorcode = 0

    errorcode = configure_chips(settings)
    if efforcode != 0:
        logger.warning(' - Chip configuration failed, aborting')
        return errorcode

    port = settings['port']
    chipset = settings['chipset']
    outfile = settings['outfile'].replace('.json','_csa-noise.json')
    controller = larpix.Controller(port)
    for chipargs in chipset:
        chip = larpix.Chip(*chipargs)
        controller.chips.append(chip)

    testpulse_value = settings['testpulse_max'] / 2
    for i,chip in enumerate(controller.chips):
        # Set testpulse amplitude
        chip.config.csa_testpulse_dac = testpulse_value
        testpulse_register = larpix.Configuration.csa_testpulse_amplitude_address
        controller.write_configuration(chip, registers=testpulse_register)
        controller.read_configuration(chip, registers=testpulse-register)
        controller.parse_input(read_data)

        controller.run(1)

        chip.config.csa_testpulse_dac = 0
        controller.write_configuration(chip, registers=testpulse_register)

        progress_bar(i, len(controller.chips))

    controller.save_output(outfile)
    logger.info('Test complete, saved to %s' % outfile)

def adc_linearity_test(settings):
    '''
    Scans through chipset and pulse sizes one by one (1sec each).
    Saves recorded data to <outfile>_adc-lin.json

    '''
    logger = logging.getLogger(__name__)
    logger.info('Performing linearity scan')
    errorcode = 0

    errorcode = configure_chips(settings)
    if efforcode != 0:
        logger.warning(' - Chip configuration failed, aborting')
        return errorcode

    port = settings['port']
    chipset = settings['chipset']
    outfile = settings['outfile'].replace('.json','_adc-lin.json')
    controller = larpix.Controller(port)
    for chipargs in chipset:
        chip = larpix.Chip(*chipargs)
        controller.chips.append(chip)

    testpulse_values = range(settings['testpulse_step'],
            settings['testpulse_max'], settings['testpulse_step'])
    for i,testpulse_value in enumerate(testpulse_values):
        for chip in controller.chips:
            # Set testpulse amplitude
            chip.config.csa_testpulse_dac = testpulse_value
            testpulse_register = larpix.Configuration.csa_testpulse_amplitude_address
            controller.write_configuration(chip, registers=testpulse_register)
            read_data = controller.read_configuration(chip, registers=testpulse-register)
            controller.parse_input(read_data)

            controller.run(1)

            chip.config.csa_testpulse_dac = 0
            controller.write_configuration(chip, registers=testpulse_register)

        progress_bar(i, len(testpulse_values))

    controller.save_output(outfile)
    logger.info('Scan complete, saved to %s' % outfile)

if __name__ == '__main__':
    import argparse
    import sys
    tests = {
            'adc_linearity_test': adc_linearity_test,
            'csa_noise_test': csa_noise_test
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
    parser.add_argument('-f', '--outfile', default='performance-data.json',
            help='output data file path')
    parser.add_argument('--step', default=5,
            help='testpulse step size in ADC counts')
    parser.add_argument('--max', default=254,
            help='testpulse max size in ADC counts')
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
            'outfile': args.outfile,
            'testpulse_step': args.step,
            'testpulse_max': args.max
            }
    setup_logger(settings)
    logger = logging.getLogger(__name__)
    try:
        for test in args.test:
            tests[test](settings)
    except Exception as e:
        logger.error('Error during test', exc_info=True)
