"""Run the in-app reminder processor continuously or for a single batch."""

import argparse
import logging
from time import sleep

from app.reminders.service import process_due_reminders
from db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Process due in-app reminders.")
    parser.add_argument("--once", action="store_true", help="Process all due batches and exit.")
    parser.add_argument("--interval", type=float, default=30, help="Polling interval in seconds.")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.interval <= 0 or args.batch_size <= 0:
        parser.error("--interval and --batch-size must be positive.")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    while True:
        try:
            total = 0
            while True:
                with SessionLocal() as session:
                    processed = process_due_reminders(session, batch_size=args.batch_size)
                total += processed
                if processed < args.batch_size:
                    break
            logging.info("Published %d reminder notifications.", total)
        except Exception:
            logging.exception("Reminder processing failed.")
            if args.once:
                raise
        if args.once:
            return
        sleep(args.interval)


if __name__ == "__main__":
    main()
