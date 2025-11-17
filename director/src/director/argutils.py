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
    parser.add_argument('--data', type=str, nargs='+', dest='data_files',
                        default=[], action='append', metavar='filename',
                        help='data files to load at startup')
    
    # Python modules to run at startup
    parser.add_argument('-m', '--module', dest='modules', metavar='module',
                        default=[], action='append',
                        help='find a python module or package and run it as a script')
    
    # Python scripts to run at startup
    parser.add_argument('--script', '--startup', type=str, nargs='+', dest='scripts',
                        default=[], action='append', metavar='filename',
                        help='python scripts to run at startup')
    
    # Testing mode
    parser.add_argument('--testing', action='store_true',
                        help='enable testing mode')
    
    # Testing data directory
    parser.add_argument('--data-dir', type=str,
                        help='testing data directory')
    
    # Output directory
    parser.add_argument('--output-dir', type=str,
                        help='output directory for writing test output')
    
    # Interactive testing mode
    parser.add_argument('--interactive', action='store_true',
                        help='enable interactive testing mode')
    
    return parser


def flatten_list_of_lists(lol):
    """Flatten a list of lists into a single list."""
    return [item for sublist in lol for item in sublist]


def parse_args(parser=None, argv=None):
    """
    Parse command-line arguments using a parser with standard args.
    
    Parameters:
    -----------
    parser : argparse.ArgumentParser, optional
        If provided, use this parser. Otherwise create a new one.
    argv : list, optional
        Arguments to parse. If None, uses sys.argv.
        
    Returns:
    --------
    argparse.Namespace
        Parsed arguments
    """
    if parser is None:
        parser = argparse.ArgumentParser()
    
    add_standard_args(parser)
    
    if argv is None:
        import sys
        argv = sys.argv[1:]
    
    args = parser.parse_args(argv)
    
    # Flatten list-of-lists for data_files
    if args.data_files:
        args.data_files = flatten_list_of_lists(args.data_files)
    
    # Flatten list-of-lists for scripts
    if args.scripts:
        args.scripts = flatten_list_of_lists(args.scripts)
    
    # Ensure modules is always a list
    if not hasattr(args, 'modules') or args.modules is None:
        args.modules = []
    
    return args

