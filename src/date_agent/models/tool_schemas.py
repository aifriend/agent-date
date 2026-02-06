"""Input and output schemas for date tools."""

from typing import Optional
from pydantic import BaseModel, Field

from date_agent.core.constants import BoundaryType, DateOperation


# =============================================================================
# get_current_date_info Tool
# =============================================================================


class CurrentDateInput(BaseModel):
    """Input schema for get_current_date_info tool."""

    timezone: str = Field(
        default="America/Lima",
        description="IANA timezone identifier (e.g., 'America/Lima', 'UTC')",
    )
    include_week_info: bool = Field(
        default=True,
        description="Include ISO week information",
    )
    include_boundaries: bool = Field(
        default=True,
        description="Include week/month/quarter boundaries",
    )
    lookback_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Number of months for financial lookback limit",
    )
    locale: str = Field(
        default="es",
        description="Locale for localized names (es, en)",
    )


class CurrentDateOutput(BaseModel):
    """Output schema for get_current_date_info tool.

    This is the IMMUTABLE REFERENCE POINT for all date calculations.
    """

    # Core date information
    date: str = Field(description="Current date in YYYY-MM-DD format")
    datetime_iso: str = Field(description="Full ISO 8601 datetime with timezone")
    timestamp_utc: int = Field(description="Unix timestamp in UTC (seconds)")
    timezone: str = Field(description="Timezone used for calculation")

    # Date components
    year: int
    month: int
    day: int
    weekday: int = Field(description="0=Monday, 6=Sunday")
    weekday_name: str
    weekday_name_localized: str = Field(description="Localized weekday name")
    month_name: str
    month_name_localized: str = Field(description="Localized month name")

    # ISO week info (optional)
    iso_week: Optional[int] = None
    iso_year: Optional[int] = None

    # Current quarter
    current_quarter: Optional[int] = None

    # Week boundaries
    this_week_monday: Optional[str] = None
    this_week_sunday: Optional[str] = None
    last_week_monday: Optional[str] = None
    last_week_sunday: Optional[str] = None

    # Month boundaries
    this_month_start: Optional[str] = None
    this_month_end: Optional[str] = None
    last_month_start: Optional[str] = None
    last_month_end: Optional[str] = None

    # Quarter boundaries
    quarter_start: Optional[str] = None
    quarter_end: Optional[str] = None

    # Financial limit (from BIO: 6-month lookback)
    lookback_limit_date: Optional[str] = Field(
        None,
        description="Earliest allowed date for financial queries",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-07-15",
                "datetime_iso": "2024-07-15T10:30:00-05:00",
                "timestamp_utc": 1721054400,
                "timezone": "America/Lima",
                "year": 2024,
                "month": 7,
                "day": 15,
                "weekday": 0,
                "weekday_name": "Monday",
                "weekday_name_localized": "Lunes",
                "month_name": "July",
                "month_name_localized": "Julio",
                "iso_week": 29,
                "iso_year": 2024,
                "current_quarter": 3,
                "this_week_monday": "2024-07-15",
                "this_week_sunday": "2024-07-21",
                "this_month_start": "2024-07-01",
                "this_month_end": "2024-07-31",
                "quarter_start": "2024-07-01",
                "quarter_end": "2024-09-30",
                "lookback_limit_date": "2024-01-15",
            }
        }


# =============================================================================
# resolve_period Tool
# =============================================================================


class ResolvePeriodInput(BaseModel):
    """Input schema for resolve_period tool."""

    period: str = Field(
        description="Semantic period expression (e.g., 'last_quarter', 'Q3 2024', 'semana pasada')"
    )
    reference_date: Optional[str] = Field(
        None,
        description="Override reference date (YYYY-MM-DD). Uses current date if not provided.",
    )
    calendar_system: str = Field(
        default="GREGORIAN",
        description="Calendar system to use (GREGORIAN, PERU_BANKING)",
    )
    boundary_type: str = Field(
        default="inclusive",
        description="How to handle range boundaries: inclusive, exclusive, etc.",
    )
    locale: str = Field(
        default="es",
        description="Locale for parsing period names (en, es)",
    )


class ResolvePeriodOutput(BaseModel):
    """Output schema for resolve_period tool."""

    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")

    # Metadata about the resolution
    period_type: str = Field(description="Canonical period type that was resolved")
    calendar_system: str = Field(description="Calendar system used")
    boundary_type: str = Field(description="Boundary handling applied")

    # Count information
    calendar_days: int = Field(description="Total calendar days in range (inclusive)")

    # For audit trail
    reference_date_used: str = Field(description="The reference date that was used")

    # Localized description
    description: str = Field(description="Human-readable description of the period")
    description_localized: str = Field(description="Localized description")

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2024-07-01",
                "end_date": "2024-09-30",
                "period_type": "q3_2024",
                "calendar_system": "GREGORIAN",
                "boundary_type": "inclusive",
                "calendar_days": 92,
                "reference_date_used": "2024-07-15",
                "description": "Q3 2024 (July 1 - September 30)",
                "description_localized": "Tercer trimestre 2024 (1 de julio - 30 de septiembre)",
            }
        }


# =============================================================================
# get_holiday_calendar Tool
# =============================================================================


class GetHolidayCalendarInput(BaseModel):
    """Input schema for get_holiday_calendar tool."""

    calendar_system: str = Field(
        description="Which calendar system to retrieve (GREGORIAN, PERU_BANKING)"
    )
    start_date: str = Field(description="Start of date range (YYYY-MM-DD)")
    end_date: str = Field(description="End of date range (YYYY-MM-DD)")
    include_weekends: bool = Field(
        default=False,
        description="Whether to include weekend dates in the result",
    )
    locale: str = Field(
        default="es",
        description="Locale for holiday names (en, es)",
    )


class HolidayEntry(BaseModel):
    """A single holiday entry."""

    date: str = Field(description="Holiday date in YYYY-MM-DD format")
    name: str = Field(description="Holiday name")
    name_localized: Optional[str] = Field(None, description="Localized name")
    holiday_type: str = Field(description="Type: national, banking, religious, etc.")
    observed: bool = Field(default=True, description="Whether it's observed")


class GetHolidayCalendarOutput(BaseModel):
    """Output schema for get_holiday_calendar tool."""

    calendar_system: str
    start_date: str
    end_date: str

    holidays: list[HolidayEntry] = Field(description="List of holidays in the range")
    weekend_dates: Optional[list[str]] = Field(
        None,
        description="Weekend dates if include_weekends=True",
    )

    # Summary statistics
    total_calendar_days: int
    total_holidays: int
    total_weekend_days: int
    total_non_business_days: int
    total_business_days: int

    class Config:
        json_schema_extra = {
            "example": {
                "calendar_system": "PERU_BANKING",
                "start_date": "2024-07-01",
                "end_date": "2024-07-31",
                "holidays": [
                    {
                        "date": "2024-07-28",
                        "name": "Independence Day",
                        "name_localized": "Fiestas Patrias",
                        "holiday_type": "national",
                        "observed": True,
                    }
                ],
                "total_calendar_days": 31,
                "total_holidays": 2,
                "total_weekend_days": 8,
                "total_non_business_days": 10,
                "total_business_days": 21,
            }
        }


# =============================================================================
# compute_date_range Tool
# =============================================================================


class ChainedOperation(BaseModel):
    """A chained operation for compositional queries."""

    operation: str = Field(description="The operation to perform")
    value: Optional[int] = Field(None, description="Numeric value for the operation")
    calendar_system: Optional[str] = Field(
        None, description="Override calendar system for this operation"
    )


class ComputeDateRangeInput(BaseModel):
    """Input schema for compute_date_range tool."""

    base_date: str = Field(description="Starting date for calculation (YYYY-MM-DD)")
    operation: str = Field(
        description="The date operation to perform (e.g., add_business_days, month_end)"
    )
    value: Optional[int] = Field(
        None,
        description="Numeric value for the operation (e.g., number of days to add)",
    )
    calendar_system: str = Field(
        default="GREGORIAN",
        description="Calendar system for business day calculations",
    )

    # For compositional queries
    then_operations: Optional[list[ChainedOperation]] = Field(
        None,
        description="Chain additional operations (for compositional queries)",
    )


class ComputeDateRangeOutput(BaseModel):
    """Output schema for compute_date_range tool."""

    result_date: str = Field(description="Resulting date in YYYY-MM-DD format")

    # If input was a range or resulted in a range
    result_start: Optional[str] = None
    result_end: Optional[str] = None

    # Computation trace (for audit)
    operations_applied: list[str] = Field(
        description="Ordered list of operations that were applied"
    )
    holidays_excluded: Optional[list[str]] = Field(
        None,
        description="Holiday dates that were skipped (for business day calculations)",
    )
    weekends_excluded: Optional[list[str]] = Field(
        None,
        description="Weekend dates that were skipped",
    )

    # Metadata
    calendar_system_used: str
    base_date_used: str

    class Config:
        json_schema_extra = {
            "example": {
                "result_date": "2024-07-25",
                "operations_applied": [
                    "Base: 2024-07-31",
                    "Operation: subtract_business_days(3)",
                    "Skipped: 2024-07-28 (Fiestas Patrias)",
                    "Skipped: 2024-07-29 (Fiestas Patrias)",
                    "Skipped: 2024-07-27 (Saturday)",
                    "Result: 2024-07-25",
                ],
                "holidays_excluded": ["2024-07-28", "2024-07-29"],
                "weekends_excluded": ["2024-07-27"],
                "calendar_system_used": "PERU_BANKING",
                "base_date_used": "2024-07-31",
            }
        }
