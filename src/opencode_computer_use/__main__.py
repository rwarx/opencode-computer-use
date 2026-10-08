"""Entry point: python -m opencode_computer_use"""
from .server import main as _main


def main() -> None:
    _main()


if __name__ == "__main__":
    _main()
