"""Calendar-related Pydantic models."""

from typing import Optional
from pydantic import BaseModel, Field

from date_agent.core.constants import HolidayType


class HolidayInfo(BaseModel):
    """Information about a single holiday.

    Represents a holiday entry from a calendar system.
    """

    date: str = Field(description="Holiday date in YYYY-MM-DD format")
    name: str = Field(description="Holiday name in English")
    name_localized: Optional[str] = Field(
        None, description="Holiday name in local language"
    )
    holiday_type: str = Field(
        default="national",
        description="Type of holiday: national, banking, religious, regional, optional",
    )
    observed: bool = Field(
        default=True,
        description="Whether the holiday is observed (some may be optional)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2024-07-28",
                "name": "Independence Day",
                "name_localized": "Fiestas Patrias",
                "holiday_type": "national",
                "observed": True,
            }
        }


class BusinessDayInfo(BaseModel):
    """Information about business day calculations.

    Used to provide detailed breakdown of business day counts.
    """

    total_calendar_days: int = Field(description="Total calendar days in range")
    total_business_days: int = Field(description="Total business days in range")
    total_weekend_days: int = Field(description="Total weekend days in range")
    total_holidays: int = Field(description="Total holidays in range")

    # Overlaps (holidays that fall on weekends)
    holiday_weekend_overlaps: int = Field(
        default=0,
        description="Holidays that fall on weekends (not double-counted)",
    )

    # Lists for detailed audit
    weekend_dates: Optional[list[str]] = Field(
        None, description="List of weekend dates"
    )
    holiday_dates: Optional[list[str]] = Field(
        None, description="List of holiday dates"
    )
    non_business_dates: Optional[list[str]] = Field(
        None, description="Combined list of all non-business dates"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_calendar_days": 31,
                "total_business_days": 21,
                "total_weekend_days": 8,
                "total_holidays": 2,
                "holiday_weekend_overlaps": 0,
            }
        }


class CalendarInfo(BaseModel):
    """Information about a calendar system's holidays for a date range.

    The output model for get_holiday_calendar tool.
    """

    calendar_system: str = Field(description="Calendar system identifier")
    start_date: str = Field(description="Start of the queried range")
    end_date: str = Field(description="End of the queried range")

    # Holidays in range
    holidays: list[HolidayInfo] = Field(
        default_factory=list,
        description="List of holidays in the range",
    )

    # Business day statistics
    business_day_info: BusinessDayInfo = Field(
        description="Business day calculation details"
    )

    # Optional: full list of weekend dates
    weekend_dates: Optional[list[str]] = Field(
        None,
        description="Weekend dates if include_weekends=True was specified",
    )

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
                    },
                    {
                        "date": "2024-07-29",
                        "name": "Independence Day (Day 2)",
                        "name_localized": "Fiestas Patrias",
                        "holiday_type": "national",
                        "observed": True,
                    },
                ],
                "business_day_info": {
                    "total_calendar_days": 31,
                    "total_business_days": 21,
                    "total_weekend_days": 8,
                    "total_holidays": 2,
                    "holiday_weekend_overlaps": 0,
                },
            }
        }
