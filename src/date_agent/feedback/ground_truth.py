"""Independent ground truth computer for date periods.

CRITICAL: This module must NOT import anything from date_agent.tools
or date_agent.agent. It implements date math from scratch using only
Python stdlib so that bugs in the agent cannot affect validation.
"""

import calendar
import re
from datetime import date, timedelta
from typing import Dict, Optional, Tuple


# Quarter start months: Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct
QUARTER_START = {1: 1, 2: 4, 3: 7, 4: 10}
QUARTER_END = {1: 3, 2: 6, 3: 9, 4: 12}


class GroundTruthComputer:
    """Computes ground truth dates independently of the date agent.

    All date math uses only datetime, calendar, and re from stdlib.
    """

    def __init__(self, reference_date: date):
        self.ref = reference_date

    def compute_period(
        self, period_type: str, params: Optional[Dict] = None
    ) -> Tuple[str, str, int]:
        """Compute (start_date, end_date, calendar_days) for a period type.

        Args:
            period_type: Canonical period type (e.g. "last_week", "named_quarter").
            params: Optional parameters (e.g. {"quarter": 1, "year": 2024}).

        Returns:
            Tuple of (start_date_iso, end_date_iso, calendar_days).
        """
        params = params or {}
        start, end = self._resolve(period_type, params)
        days = (end - start).days + 1
        return start.isoformat(), end.isoformat(), days

    def _resolve(self, period_type: str, params: dict) -> Tuple[date, date]:
        """Route to the appropriate resolver."""
        # Handle dynamic last_N_X patterns
        m = re.match(r"last_(\d+)_(days|weeks|months|business_days)$", period_type)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            if unit == "days":
                return self._last_n_days(n)
            elif unit == "weeks":
                return self._last_n_weeks(n)
            elif unit == "months":
                return self._last_n_months(n)
            elif unit == "business_days":
                return self._last_n_business_days(n)

        resolvers = {
            "today": self._today,
            "yesterday": self._yesterday,
            "this_week": self._this_week,
            "last_week": self._last_week,
            "week_before_last": self._week_before_last,
            "last_weekend": self._last_weekend,
            "recent": self._recent,
            "this_month": self._this_month,
            "last_month": self._last_month,
            "this_quarter": self._this_quarter,
            "last_quarter": self._last_quarter,
            "this_year": self._this_year,
            "last_year": self._last_year,
            "ytd": self._ytd,
            "named_quarter": lambda: self._named_quarter(
                params.get("quarter", 1), params.get("year", self.ref.year)
            ),
            "named_month": lambda: self._named_month(
                params.get("month", 1), params.get("year", self.ref.year)
            ),
            "named_year": lambda: self._named_year(
                params.get("year", self.ref.year)
            ),
            "days_ago": lambda: self._days_ago(params.get("n", 1)),
            "custom": lambda: self._custom(
                params.get("start"), params.get("end")
            ),
        }

        resolver = resolvers.get(period_type)
        if resolver is None:
            raise ValueError(f"Unknown period type: {period_type}")
        return resolver()

    # --- Single-day periods ---

    def _today(self) -> Tuple[date, date]:
        return self.ref, self.ref

    def _yesterday(self) -> Tuple[date, date]:
        d = self.ref - timedelta(days=1)
        return d, d

    # --- Week-relative periods (Monday=0, Sunday=6) ---

    def _this_week(self) -> Tuple[date, date]:
        monday = self.ref - timedelta(days=self.ref.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday

    def _last_week(self) -> Tuple[date, date]:
        this_monday = self.ref - timedelta(days=self.ref.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        return last_monday, last_sunday

    def _week_before_last(self) -> Tuple[date, date]:
        this_monday = self.ref - timedelta(days=self.ref.weekday())
        wbl_monday = this_monday - timedelta(days=14)
        wbl_sunday = wbl_monday + timedelta(days=6)
        return wbl_monday, wbl_sunday

    def _last_weekend(self) -> Tuple[date, date]:
        # Agent convention: Saturday and Sunday before this Monday
        this_monday = self.ref - timedelta(days=self.ref.weekday())
        last_sunday = this_monday - timedelta(days=1)
        last_saturday = last_sunday - timedelta(days=1)
        return last_saturday, last_sunday

    def _recent(self) -> Tuple[date, date]:
        # Agent convention: ref - 7 to ref (8 days rolling)
        start = self.ref - timedelta(days=7)
        return start, self.ref

    # --- Month-relative periods ---

    def _this_month(self) -> Tuple[date, date]:
        start = self.ref.replace(day=1)
        _, last_day = calendar.monthrange(self.ref.year, self.ref.month)
        end = self.ref.replace(day=last_day)
        return start, end

    def _last_month(self) -> Tuple[date, date]:
        if self.ref.month == 1:
            start = date(self.ref.year - 1, 12, 1)
            end = date(self.ref.year - 1, 12, 31)
        else:
            start = date(self.ref.year, self.ref.month - 1, 1)
            _, last_day = calendar.monthrange(self.ref.year, self.ref.month - 1)
            end = date(self.ref.year, self.ref.month - 1, last_day)
        return start, end

    # --- Quarter-relative periods ---

    def _this_quarter(self) -> Tuple[date, date]:
        q = (self.ref.month - 1) // 3 + 1
        start_month = QUARTER_START[q]
        end_month = QUARTER_END[q]
        _, last_day = calendar.monthrange(self.ref.year, end_month)
        return date(self.ref.year, start_month, 1), date(self.ref.year, end_month, last_day)

    def _last_quarter(self) -> Tuple[date, date]:
        q = (self.ref.month - 1) // 3 + 1
        prev_q = q - 1 if q > 1 else 4
        year = self.ref.year if q > 1 else self.ref.year - 1
        start_month = QUARTER_START[prev_q]
        end_month = QUARTER_END[prev_q]
        _, last_day = calendar.monthrange(year, end_month)
        return date(year, start_month, 1), date(year, end_month, last_day)

    # --- Year-relative periods ---

    def _this_year(self) -> Tuple[date, date]:
        return date(self.ref.year, 1, 1), date(self.ref.year, 12, 31)

    def _last_year(self) -> Tuple[date, date]:
        y = self.ref.year - 1
        return date(y, 1, 1), date(y, 12, 31)

    def _ytd(self) -> Tuple[date, date]:
        return date(self.ref.year, 1, 1), self.ref

    # --- Named periods ---

    def _named_quarter(self, quarter: int, year: int) -> Tuple[date, date]:
        start_month = QUARTER_START[quarter]
        end_month = QUARTER_END[quarter]
        _, last_day = calendar.monthrange(year, end_month)
        return date(year, start_month, 1), date(year, end_month, last_day)

    def _named_month(self, month: int, year: int) -> Tuple[date, date]:
        _, last_day = calendar.monthrange(year, month)
        return date(year, month, 1), date(year, month, last_day)

    def _named_year(self, year: int) -> Tuple[date, date]:
        return date(year, 1, 1), date(year, 12, 31)

    def _days_ago(self, n: int) -> Tuple[date, date]:
        d = self.ref - timedelta(days=n)
        return d, d

    def _custom(self, start_str: str, end_str: str) -> Tuple[date, date]:
        return date.fromisoformat(start_str), date.fromisoformat(end_str)

    # --- Dynamic last_N_X periods ---

    def _last_n_days(self, n: int) -> Tuple[date, date]:
        # Agent convention: rolling window ref-N to ref (includes today)
        start = self.ref - timedelta(days=n)
        return start, self.ref

    def _last_n_weeks(self, n: int) -> Tuple[date, date]:
        # Agent convention: rolling window ref-N*7 to ref (includes today)
        start = self.ref - timedelta(weeks=n)
        return start, self.ref

    def _last_n_months(self, n: int) -> Tuple[date, date]:
        # Agent convention: first of (month-N) to ref (rolling, includes today)
        target_month = self.ref.month - n
        target_year = self.ref.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        start = date(target_year, target_month, 1)
        return start, self.ref

    def _last_n_business_days(self, n: int) -> Tuple[date, date]:
        # Agent convention: walk backward from ref counting business days, end is ref
        count = 0
        current = self.ref
        while count < n:
            current = current - timedelta(days=1)
            if current.weekday() < 5:  # Mon-Fri
                count += 1
        return current, self.ref
