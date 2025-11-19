"""Simple argparse wrapper for adding standard command-line arguments."""

import argparse


def add_standard_args(parser):
    """
    Add standard command-line arguments to an ArgumentParser.
    
    Parameters:
    -----------
    parser : argparse.ArgumentParser
        The parser to add arguments to
        
    Returns:
    --------
    argparse.ArgumentParser
        The same parser instance (for chaining)
    """
    # Data files to load at startup
    parser.add_argument('--data', type=str, dest='data_files', nargs='+',
                        default=[], action='append', metavar='filename',
                        help='data files to load at startup')
    
    # Python modules to run at startup
    parser.add_argument('-m', '--module', dest='modules', metavar='module',
                        default=[], action='append',
                        help='find a python module or package and run it as a script')
    
    # Python scripts to run at startup
    parser.add_argument('--script', type=str, nargs='+', dest='scripts',
                        default=[], action='append', metavar='filename',
                        help='python scripts to run at startup')
    
    # Testing mode
    parser.add_argument('--testing', action='store_true',
                        help='enable testing mode')
    
    # Testing data directory
    parser.add_argument('--test-data-dir', type=str,
                        help='testing data directory')
    
    # Output directory
    parser.add_argument('--test-output-dir', type=str,
                        help='output directory for writing test output')
    
    # Interactive testing mode
    parser.add_argument('--interactive', action='store_true',
                        help='enable interactive testing mode')
    
    parser.add_argument('--auto-quit', action='store_true',
                        help='automatically quit the application after starting, used for testing')
    return parser
