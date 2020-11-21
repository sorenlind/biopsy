"""CLI entry point."""
# pylint:disable=import-outside-toplevel
import argparse
from argparse import ArgumentParser
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List

from .version import VERSION

MAINPARSER_HELP = "print current version number"
SUBPARSERS_HELP = "%(prog)s must be called with a command:"
DESCRIPTION = """Description"""


def main():
    """Handle CLI arguments."""
    _create_parser(DESCRIPTION, VERSION, [_preprocess_parser])


def command(success_msg: str, fail_msg: str) -> Callable:
    """Wrap a command for the CLI with a sucess and a fail message."""

    def decorator_command(func: Callable[..., Any]) -> Callable:
        @wraps(func)
        def wrapper_command(*args: List[Any], **kwargs: Dict[str, Any]):
            try:
                func(*args, **kwargs)
                print(success_msg + " ✅")
                sys.exit(0)
            except Exception as error:
                print("")
                print(fail_msg + " 💔 💔 💔")
                print("Error: " + str(error))
                print("")
                sys.exit((1))

        return wrapper_command

    return decorator_command


def _create_parser(
    description: str, version: str, subparsers_funcs: List[Callable[..., Any]]
):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {}".format(version),
        help=MAINPARSER_HELP,
    )

    subparsers = parser.add_subparsers(help=SUBPARSERS_HELP, dest="command")
    subparsers.required = True

    for subparsers_func in subparsers_funcs:
        subparsers_func(subparsers)

    args = parser.parse_args()
    args.func(parser, args)


def _preprocess_parser(subparsers: argparse._SubParsersAction) -> ArgumentParser:
    """Create parser for the 'preprocess' command."""
    parser = subparsers.add_parser("preprocess", help="preprocess")
    parser.add_argument("INPUT_FOLDER", type=Path, help="Input folder.")
    parser.add_argument("OUTPUT_FOLDER", type=Path, help="Output folder.")

    parser.add_argument(
        "-l",
        "--level",
        type=int,
        default=2,
        help="zoom level to use for extraction of images from slides",
        required=False,
    )

    parser.add_argument(
        "-s",
        "--tile-size",
        type=int,
        default=512,
        help="size of output tiles in pixels",
        required=False,
    )

    parser.add_argument(
        "-o",
        "--overlap",
        type=float,
        default=0.0,
        help="fraction of image to overlap tiles",
        required=False,
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        help="create augmented images by rotating the original images.",
    )

    parser.set_defaults(func=_preprocess)
    return parser


@command("Successfully preprocessed files", "Preprocessing failed")
def _preprocess(_, args: argparse.Namespace):
    from .preprocessing import preprocess

    if not args.OUTPUT_FOLDER.is_dir():
        raise FileNotFoundError("Output folder does not exist.")

    preprocess(
        args.INPUT_FOLDER,
        args.OUTPUT_FOLDER,
        args.level,
        args.tile_size,
        args.overlap,
        args.rotate,
    )


if __name__ == "__main__":
    main()
