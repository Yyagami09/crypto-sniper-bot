import argparse
import logging
import signal
import time

from dotenv import load_dotenv

from pump.config import ROOT, load_rules, settings
from pump.engine import scan
from pump.gmgn import GMGN, APIError
from pump.storage import make_store, StorageError


def main():
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser(description='Radar GMGN em segundo plano, somente consultas')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    config = settings()
    try:
        store = make_store(config, args.demo)
        if args.demo:
            from pump.demo import DemoAPI
            api = DemoAPI()
        else:
            api = GMGN(config)
    except (StorageError, APIError) as exc:
        logging.error('Configuração incompleta: %s', exc)
        return 2
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while running:
        start = time.monotonic()
        try:
            rules = load_rules()
            result = scan(store, api, rules, config, args.demo)
            logging.info('Varredura: %s', result)
        except (StorageError, ValueError, OSError):
            # Logs contain no URLs/credentials or raw exception bodies.
            logging.error('Varredura interrompida; confira banco e configuração')
            if args.once:
                return 1
            rules = None
        if args.once:
            return 0 if result in ('ok', 'partial') else 1
        # Interval is between starts; slow cycles never overlap.
        wait = max(1, (rules.interval_seconds if rules else 600) - (time.monotonic()-start))
        deadline = time.monotonic() + wait
        while running and time.monotonic() < deadline:
            time.sleep(min(1, deadline-time.monotonic()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
