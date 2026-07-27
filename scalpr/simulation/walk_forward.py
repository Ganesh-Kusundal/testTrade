from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WalkForwardValidator:
    """Manages walk-forward optimization segments for robust parameter validation."""

    def __init__(self, train_days: int = 30, test_days: int = 10) -> None:
        self.train_days = train_days
        self.test_days = test_days

    def generate_windows(self, start_date: datetime, end_date: datetime) -> list[dict[str, datetime]]:
        """Generate rolling train/test windows across date bounds."""
        windows = []
        current_train_start = start_date

        while True:
            train_end = current_train_start + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)

            if test_end > end_date:
                # If test window extends past the dataset end, stop
                break

            windows.append({
                "train_start": current_train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end
            })

            # Roll forward by the test period
            current_train_start += timedelta(days=self.test_days)

        logger.info(f"WalkForward: Generated {len(windows)} validation windows.")
        return windows
