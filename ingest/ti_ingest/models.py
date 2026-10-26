"""Pydantic models for SWPC solar-wind, GOES X-ray, Kp, and alert rows.

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

``time_tag`` in the solar-wind and Kp files is a UTC clock with no zone
suffix, for example ``2026-10-25T21:10:00``. The GOES X-ray file appends
``Z`` (checked 2026-10-25). Alert ``issue_datetime`` uses a space and
fractional seconds, for example ``2026-10-25 09:27:50.723``. A naive
value is stored as UTC. The X-ray columns are in
``db/migrations/0002_goes_xray_flux.sql``. The Kp and alert columns are
in ``db/migrations/0003_kp_alerts.sql``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _as_utc(value: datetime) -> datetime:
    """SWPC writes UTC. A naive clock is that UTC, not the machine's zone."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class StoredRow(BaseModel):
    """A row the loader can upsert. Each feed subclasses this.

    ``as_params`` is the column order of that table's INSERT. The loader
    does not care which feed it is, only that the tuple matches the SQL.
    """

    model_config = ConfigDict(extra="ignore")

    def as_params(self) -> tuple[object, ...]:
        raise NotImplementedError


class SwpcRow(StoredRow):
    """Fields shared by the wind and magnetic-field files."""

    model_config = ConfigDict(extra="ignore")

    time_tag: datetime
    # strict: a number or the string "true" is a different shape, not a quiet success.
    source: Annotated[str, Field(strict=True)]
    active: Annotated[bool, Field(strict=True)]

    @field_validator("time_tag")
    @classmethod
    def time_tag_as_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @field_validator("source")
    @classmethod
    def source_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("source is blank")
        return stripped


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


class XrayRow(StoredRow):
    """One GOES X-ray minute from ``xrays-6-hour.json`` (issue #31).

    The file has two rows per minute, one per ``energy`` band. ``flux``
    is the electron-corrected value SWPC publishes for the chart, in
    watts per square metre. ``observed_flux`` is the measurement before
    that correction. The JSON key ``electron_contaminaton`` is misspelled
    upstream (checked 2026-10-25). ``validation_alias`` reads that key
    and the corrected spelling, so a quiet fix upstream does not reject
    the file. The Python name and the SQL column use the corrected word.

    A missing key is a schema change and is rejected. JSON ``null`` is a
    gap and is stored. ``extra="ignore"`` keeps unused keys in the raw file.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    time_tag: datetime
    satellite: Annotated[int, Field(strict=True, gt=0)]
    energy: Annotated[str, Field(strict=True)]
    flux: float | None
    observed_flux: float | None
    electron_correction: float | None
    electron_contamination: bool | None = Field(
        strict=True,
        validation_alias=AliasChoices(
            "electron_contaminaton",
            "electron_contamination",
        ),
    )

    @field_validator("time_tag")
    @classmethod
    def time_tag_as_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @field_validator("energy")
    @classmethod
    def energy_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("energy is blank")
        return stripped

    def as_params(self) -> tuple[object, ...]:
        return (
            self.time_tag,
            self.satellite,
            self.energy,
            self.flux,
            self.observed_flux,
            self.electron_correction,
            self.electron_contamination,
        )


class Kp1mRow(StoredRow):
    """One minute from ``planetary_k_index_1m.json`` (issue #32).

    ``estimated_kp`` is the number the dashboard plots beside Bz.
    ``kp`` is the short string in the same object (``0Z``, ``1M``).
    ``kp_index`` is the integer the file publishes next to them. A missing
    key is a schema change and is rejected. JSON ``null`` is a gap and is
    stored. ``extra="ignore"`` keeps unused keys in the raw file.
    """

    time_tag: datetime
    kp_index: int | None = Field(strict=True)
    estimated_kp: float | None
    kp: str | None = Field(strict=True)

    @field_validator("time_tag")
    @classmethod
    def time_tag_as_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @field_validator("kp")
    @classmethod
    def kp_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("kp is blank")
        return stripped

    def as_params(self) -> tuple[object, ...]:
        return (self.time_tag, self.kp_index, self.estimated_kp, self.kp)


class Kp3hRow(StoredRow):
    """One 3-hour block from ``noaa-planetary-k-index.json`` (issue #32).

    The Kp number's JSON key is ``Kp``. The column and the Python name are
    ``kp``. ``a_running`` is the running a index beside it.
    ``station_count`` is how many magnetometers contributed.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    time_tag: datetime
    kp: float | None = Field(validation_alias="Kp")
    a_running: int | None = Field(strict=True)
    station_count: int | None = Field(strict=True)

    @field_validator("time_tag")
    @classmethod
    def time_tag_as_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)

    def as_params(self) -> tuple[object, ...]:
        return (self.time_tag, self.kp, self.a_running, self.station_count)


class AlertRow(StoredRow):
    """One object from ``alerts.json`` (issue #32).

    ``product_id`` is a short code such as ``K04A``. Many messages share
    one code, so the row identity is ``(issue_datetime, product_id)``.
    ``message`` is the full text, including the serial number. The issue
    time has no ``Z``; it is UTC.
    """

    issue_datetime: datetime
    product_id: Annotated[str, Field(strict=True)]
    message: str | None = Field(strict=True)

    @field_validator("issue_datetime")
    @classmethod
    def issue_datetime_as_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)

    @field_validator("product_id")
    @classmethod
    def product_id_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("product_id is blank")
        return stripped

    def as_params(self) -> tuple[object, ...]:
        return (self.issue_datetime, self.product_id, self.message)
