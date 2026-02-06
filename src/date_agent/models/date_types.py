"""Date-related Pydantic models."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class DateInfo(BaseModel):
    """Comprehensive information about a single date.

    Used for representing detailed date information including
    both standard and localized representations.
    """

    # Core date in ISO format
    date: str = Field(description="Date in YYYY-MM-DD format")

    # Date components
    year: int = Field(description="Year (e.g., 2024)")
    month: int = Field(ge=1, le=12, description="Month (1-12)")
    day: int = Field(ge=1, le=31, description="Day of month (1-31)")

    # Day of week
    weekday: int = Field(ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    weekday_name: str = Field(description="Weekday name in English")
    weekday_name_localized: Optional[str] = Field(
        None, description="Weekday name in configured locale"
    )

    # Month info
    month_name: str = Field(description="Month name in English")
    month_name_localized: Optional[str] = Field(
        None, description="Month name in configured locale"
    )

    # ISO week info
    iso_week: Optional[int] = Field(None, description="ISO week number (1-53)")
    iso_year: Optional[int] = Field(None, description="ISO year for the week")

    # Quarter info
    quarter: Optional[int] = Field(None, ge=1, le=4, description="Quarter (1-4)")

    # Business day flag
    is_business_day: Optional[bool] = Field(
        None, description="Whether this is a business day in the configured calendar"
    )
    is_weekend: Optional[bool] = Field(None, description="Whether this is a weekend day")
    is_holiday: Optional[bool] = Field(
        None, description="Whether this is a holiday in the configured calendar"
    )
    holiday_name: Optional[str] = Field(
        None, description="Holiday name if this is a holiday"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-07-28",
                "year": 2024,
                "month": 7,
                "day": 28,
                "weekday": 6,
                "weekday_name": "Sunday",
                "weekday_name_localized": "Domingo",
                "month_name": "July",
                "month_name_localized": "Julio",
                "iso_week": 30,
                "iso_year": 2024,
                "quarter": 3,
                "is_business_day": False,
                "is_weekend": True,
                "is_holiday": True,
                "holiday_name": "Fiestas Patrias",
            }
        }


class DateRange(BaseModel):
    """A date range with start and end dates.

    Used for representing resolved periods like "last quarter"
    or explicit date ranges.
    """

    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")

    # Range metadata
    calendar_days: int = Field(ge=0, description="Total calendar days in range (inclusive)")
    business_days: Optional[int] = Field(
        None, description="Total business days in range (if calculated)"
    )

    # Boundary handling
    boundary_type: str = Field(
        default="inclusive", description="How boundaries are handled: inclusive, exclusive, etc."
    )

    # Source information
    period_type: Optional[str] = Field(
        None, description="The semantic period type that generated this range"
    )
    description: Optional[str] = Field(
        None, description="Human-readable description of the range"
    )
    description_localized: Optional[str] = Field(
        None, description="Localized description"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2024-07-01",
                "end_date": "2024-09-30",
                "calendar_days": 92,
                "business_days": 65,
                "boundary_type": "inclusive",
                "period_type": "q3_2024",
                "description": "Q3 2024",
                "description_localized": "Tercer trimestre 2024",
            }
        }


class DateResult(BaseModel):
    """Result of a date calculation operation.

    The standard output model for date tools, containing
    the result date(s) and computation metadata.
    """

    # Primary result
    result_date: str = Field(description="Result date in YYYY-MM-DD format")

    # Alternative: date range result
    result_start: Optional[str] = Field(
        None, description="Start of range (if result is a range)"
    )
    result_end: Optional[str] = Field(
        None, description="End of range (if result is a range)"
    )

    # Computation trace (for audit)
    base_date: str = Field(description="The base date used for calculation")
    operation: str = Field(description="The operation that was performed")
    calendar_system: str = Field(description="Calendar system used")
    timezone: str = Field(description="Timezone used")

    # Steps taken
    operations_applied: list[str] = Field(
        default_factory=list,
        description="Ordered list of operations applied",
    )

    # Excluded dates (for business day calculations)
    holidays_excluded: Optional[list[str]] = Field(
        None, description="Holidays that were skipped"
    )
    weekends_excluded: Optional[list[str]] = Field(
        None, description="Weekend days that were skipped"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "result_date": "2024-07-25",
                "base_date": "2024-07-31",
                "operation": "subtract_business_days",
                "calendar_system": "PERU_BANKING",
                "timezone": "America/Lima",
                "operations_applied": [
                    "Calculated month_end: 2024-07-31",
                    "Subtracted 3 business days",
                    "Skipped 2024-07-28 (Fiestas Patrias)",
                    "Skipped 2024-07-29 (Fiestas Patrias)",
                    "Result: 2024-07-25",
                ],
                "holidays_excluded": ["2024-07-28", "2024-07-29"],
                "weekends_excluded": ["2024-07-27"],
            }
        }
