"""
Command-line interface for NF-Subway.

Provides various modes for monitoring Nextflow pipelines.
"""

import sys
import argparse
from pathlib import Path

from . import __version__
from .monitor import monitor_nextflow_stdout, monitor_nextflow_logfile


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='nf-subway',
        description='Git-graph style visualization for Nextflow pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor pipeline from stdin (pipe mode)
  nextflow run pipeline.nf | nf-subway

  # Monitor a running pipeline's log file
  nf-subway --log .nextflow.log

  # Monitor with custom refresh rate
  nf-subway --log .nextflow.log --refresh 10
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '--log',
        type=str,
        metavar='FILE',
        help='Monitor a Nextflow log file (like tail -f)'
    )
    
    parser.add_argument(
        '--refresh',
        type=int,
        default=4,
        metavar='RATE',
        help='Refresh rate in updates per second (default: 4)'
    )
    
    parser.add_argument(
        '--no-original',
        action='store_true',
        help='Hide original Nextflow output (only show subway graph)'
    )
    
    parser.add_argument(
        '--orientation',
        type=str,
        choices=['vertical', 'horizontal', 'auto'],
        default='auto',
        help='Pipeline layout orientation: vertical, horizontal, or auto (default: auto)'
    )

    args = parser.parse_args()

    # Determine mode
    if args.log:
        # Log file monitoring mode
        log_path = Path(args.log)
        if not log_path.exists():
            print(f"Error: Log file not found: {args.log}", file=sys.stderr)
            print("The log file will be monitored once it's created.", file=sys.stderr)
        
        monitor_nextflow_logfile(
            args.log,
            orientation=args.orientation,
            refresh_rate=args.refresh,
            show_original=not args.no_original,
        )
    else:
        # stdin pipe mode (default)
        if sys.stdin.isatty():
            # No input piped
            parser.print_help()
            print("\n⚠️  No input detected. Either pipe Nextflow output or use --log option.",
                  file=sys.stderr)
            sys.exit(1)
        
        monitor_nextflow_stdout(
            orientation=args.orientation,
            refresh_rate=args.refresh,
            show_original=not args.no_original,
        )



if __name__ == '__main__':
    main()
