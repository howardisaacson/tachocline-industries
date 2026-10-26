"""Pydantic models for one SWPC wind row and one SWPC mag row.

A pydantic model is a class that declares the fields of one record.
``model_validate`` checks a dictionary from the JSON file. It returns
the object when the record fits, and raises ``ValidationError`` when it
does not. The loader counts those failures and skips the bad rows.

https://pydantic.dev/docs/validation/latest/concepts/models/

The columns are the ones in ``db/migrations/0001_solar_wind.sql``. The
live files also carry alpha-particle values, proton velocity, angles,
and quality flags (checked 2026-10-25). Those stay in the raw JSON.
``extra="ignore"`` means a new unused key does not reject the row. A
missing key that we do store still rejects it: the field is required,
and JSON ``null`` is allowed because the feed has gaps (ADR 0003).

``time_tag`` in the file is a UTC clock with no zone suffix, for example
``2026-10-25T21:10:00``. A naive value is stored as UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SwpcRow(BaseModel):
    """Fields shared by the wind and magnetic-field files."""

    model_config = ConfigDict(extra="ignore")

    time_tag: datetime
    # strict: a number or the string "true" is a different shape, not a quiet success.
    source: Annotated[str, Field(strict=True)]
    active: Annotated[bool, Field(strict=True)]

    @field_validator("time_tag")
    @classmethod
    def time_tag_as_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("source")
    @classmethod
    def source_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source is blank")
        return stripped

    def as_params(self) -> tuple[object, ...]:
        """Column values in the same order as the INSERT for this table."""
        raise NotImplementedError


class WindRow(SwpcRow):
    """One plasma minute from ``rtsw_wind_1m``.

    The measurement fields are required keys. ``null`` is a gap and is
    stored. Omitting the key is a schema change and is rejected.
    """

    proton_speed: float | None
    proton_density: float | None
    proton_temperature: float | None

    def as_params(self) -> tuple[object, ...]:
        return (
            self.time_tag,
            self.source,
            self.active,
            self.proton_speed,
            self.proton_density,
            self.proton_temperature,
        )


class MagRow(SwpcRow):
    """One magnetic-field minute from ``rtsw_mag_1m``. Values are nanotesla."""

    bt: float | None
    bx_gse: float | None
    by_gse: float | None
    bz_gse: float | None
    bx_gsm: float | None
    by_gsm: float | None
    bz_gsm: float | None

    def as_params(self) -> tuple[object, ...]:
        return (
            self.time_tag,
            self.source,
            self.active,
            self.bt,
            self.bx_gse,
            self.by_gse,
            self.bz_gse,
            self.bx_gsm,
            self.by_gsm,
            self.bz_gsm,
        )
