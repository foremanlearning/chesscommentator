import sys
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for Windows support
init()

class Logger:
    @staticmethod
    def _get_timestamp():
        return datetime.now().strftime('%H:%M:%S.%f')[:-3]

    @staticmethod
    def info(message):
        timestamp = Logger._get_timestamp()
        print(f"{Fore.BLUE}[INFO] {timestamp} - {message}{Style.RESET_ALL}")
        sys.stdout.flush()

    @staticmethod
    def warning(message):
        timestamp = Logger._get_timestamp()
        print(f"{Fore.YELLOW}[WARNING] {timestamp} - {message}{Style.RESET_ALL}")
        sys.stdout.flush()

    @staticmethod
    def error(message):
        timestamp = Logger._get_timestamp()
        print(f"{Fore.RED}[ERROR] {timestamp} - {message}{Style.RESET_ALL}")
        sys.stdout.flush()

    @staticmethod
    def success(message):
        timestamp = Logger._get_timestamp()
        print(f"{Fore.GREEN}[SUCCESS] {timestamp} - {message}{Style.RESET_ALL}")
        sys.stdout.flush()

    @staticmethod
    def debug(message):
        timestamp = Logger._get_timestamp()
        print(f"{Fore.CYAN}[DEBUG] {timestamp} - {message}{Style.RESET_ALL}")
        sys.stdout.flush() 