import pandas as pd


LOCAL_TIMEZONE = "Europe/Brussels"

MODES = {
    "Auto's": "car",
    "Fietsers": "bike",
    "Zwaar verkeer": "heavy",
    "Voetgangers": "pedestrian",
}


def prepare_measurements(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bereid ruwe Telraam-metingen voor analyse voor.
    """

    if df.empty:
        return df.copy()

    result = df.copy()

    result["measured_at"] = pd.to_datetime(
        result["measured_at"],
        utc=True,
    )

    result["measured_at_local"] = (
        result["measured_at"]
        .dt.tz_convert(LOCAL_TIMEZONE)
    )

    result["date"] = result["measured_at_local"].dt.date
    result["hour"] = result["measured_at_local"].dt.hour

    return result


def filter_measurements(
    df: pd.DataFrame,
    start_hour: int = 8,
    end_hour: int = 18,
    min_uptime: float = 0.5,
) -> pd.DataFrame:
    """
    Filter op lokale uren en minimale uptime.

    8-18 betekent:
    08:00 t.e.m. 17:59.
    """

    if df.empty:
        return df.copy()

    result = df[
        (df["hour"] >= start_hour)
        & (df["hour"] < end_hour)
    ].copy()

    if min_uptime is not None:
        result = result[
            result["uptime"] >= min_uptime
        ].copy()

    return result


def add_combined_mode(
    df: pd.DataFrame,
    modes: list[str],
) -> pd.DataFrame:
    """
    Combineer één of meerdere vervoersmodi.

    Bijvoorbeeld:
    car + heavy = gemotoriseerd verkeer.
    """

    if df.empty:
        return df.copy()

    if not modes:
        raise ValueError(
            "Selecteer minstens één vervoersmiddel."
        )

    allowed_modes = {
        "car",
        "bike",
        "heavy",
        "pedestrian",
    }

    invalid_modes = set(modes) - allowed_modes

    if invalid_modes:
        raise ValueError(
            f"Onbekende vervoersmiddelen: {invalid_modes}"
        )

    result = df.copy()

    result["selected_traffic"] = (
        result[modes]
        .fillna(0)
        .sum(axis=1)
    )

    return result


def daily_selected_traffic(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Bereken geselecteerd verkeer per lokale kalenderdag.
    """

    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "value",
                "hours",
                "avg_uptime",
            ]
        )

    result = (
        df
        .groupby("date", as_index=False)
        .agg(
            value=("selected_traffic", "sum"),
            hours=("selected_traffic", "count"),
            avg_uptime=("uptime", "mean"),
        )
    )

    result["date"] = pd.to_datetime(
        result["date"]
    )

    return result



def weekly_average_daily_traffic(
    daily_df: pd.DataFrame,
    min_hours_per_day: int = 8,
) -> pd.DataFrame:
    """
    Bereken gemiddeld dagelijks verkeer per kalenderweek.

    Dagen met onvoldoende geldige meeturen worden uitgesloten.
    """

    if daily_df.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "avg_daily_traffic",
                "sum_valid_traffic",
                "valid_days",
                "avg_uptime",
            ]
        )

    valid_days = daily_df[
        daily_df["hours"] >= min_hours_per_day
    ].copy()

    if valid_days.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "avg_daily_traffic",
                "sum_valid_traffic",
                "valid_days",
                "avg_uptime",
            ]
        )

    valid_days["week"] = (
        valid_days["date"]
        .dt.to_period("W-SUN")
        .dt.start_time
    )

    result = (
        valid_days
        .groupby("week", as_index=False)
        .agg(
            avg_daily_traffic=("value", "mean"),
            sum_valid_traffic=("value", "sum"),
            valid_days=("date", "count"),
            avg_uptime=("avg_uptime", "mean"),
        )
    )

    return result


def monthly_average_daily_traffic(
    daily_df: pd.DataFrame,
    min_hours_per_day: int = 8,
) -> pd.DataFrame:
    """
    Bereken gemiddeld dagelijks verkeer per maand.

    Dagen met onvoldoende geldige meeturen worden uitgesloten.
    """

    if daily_df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "avg_daily_traffic",
                "sum_valid_traffic",
                "valid_days",
                "avg_uptime",
            ]
        )

    valid_days = daily_df[
        daily_df["hours"] >= min_hours_per_day
    ].copy()

    if valid_days.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "avg_daily_traffic",
                "sum_valid_traffic",
                "valid_days",
                "avg_uptime",
            ]
        )

    valid_days["month"] = (
        valid_days["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    result = (
        valid_days
        .groupby("month", as_index=False)
        .agg(
            avg_daily_traffic=("value", "mean"),
            sum_valid_traffic=("value", "sum"),
            valid_days=("date", "count"),
            avg_uptime=("avg_uptime", "mean"),
        )
    )

    return result

def yearly_average_daily_traffic(
    daily_df: pd.DataFrame,
    min_hours_per_day: int = 8,
) -> pd.DataFrame:
    """
    Bereken gemiddeld dagelijks verkeer per kalenderjaar.

    Dagen met onvoldoende geldige meeturen worden uitgesloten.
    De som is uitsluitend de som over geldige dagen en is dus
    niet noodzakelijk een volledig kalenderjaartotaal.
    """

    columns = [
        "year",
        "avg_daily_traffic",
        "sum_valid_traffic",
        "valid_days",
        "calendar_days",
        "coverage",
        "avg_uptime",
    ]

    if daily_df.empty:
        return pd.DataFrame(columns=columns)

    valid_days = daily_df[
        daily_df["hours"] >= min_hours_per_day
    ].copy()

    if valid_days.empty:
        return pd.DataFrame(columns=columns)

    valid_days["year_number"] = valid_days["date"].dt.year
    valid_days["year"] = pd.to_datetime(
        valid_days["year_number"].astype(str) + "-01-01"
    )

    result = (
        valid_days
        .groupby(["year", "year_number"], as_index=False)
        .agg(
            avg_daily_traffic=("value", "mean"),
            sum_valid_traffic=("value", "sum"),
            valid_days=("date", "count"),
            avg_uptime=("avg_uptime", "mean"),
        )
    )

    result["calendar_days"] = result["year_number"].map(
        lambda year: 366 if pd.Timestamp(
            year=year, month=12, day=31
        ).is_leap_year else 365
    )
    result["coverage"] = (
        result["valid_days"] / result["calendar_days"]
    )

    return result.drop(columns=["year_number"])


def add_missing_days_as_gaps(
    daily_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Voeg ontbrekende kalenderdagen toe als lege waarden.

    Daardoor ziet Plotly een echte onderbreking in de data
    en wordt er geen lijn over periodes zonder metingen getrokken.
    """

    if daily_df.empty:
        return daily_df.copy()

    result = daily_df.copy()

    result["date"] = pd.to_datetime(
        result["date"]
    )

    full_range = pd.date_range(
        start=result["date"].min(),
        end=result["date"].max(),
        freq="D",
    )

    result = (
        result
        .set_index("date")
        .reindex(full_range)
        .rename_axis("date")
        .reset_index()
    )

    return result

def add_rolling_average(
    daily_df: pd.DataFrame,
    window_days: int = 30,
) -> pd.DataFrame:
    """
    Bereken een voortschrijdend gemiddelde over kalenderdagen.

    Ontbrekende dagen blijven NaN.
    Bij lange datagaten wordt de trendlijn onderbroken.
    """

    if daily_df.empty:
        return daily_df.copy()

    result = daily_df.copy()

    result["date"] = pd.to_datetime(result["date"])

    result = (
        result
        .sort_values("date")
        .set_index("date")
    )

    # Minstens 60% van het venster moet echte data bevatten.
    min_periods = max(
        1,
        round(window_days * 0.60),
    )

    result["rolling_average"] = (
        result["value"]
        .rolling(
            window=window_days,
            min_periods=min_periods,
        )
        .mean()
    )

    # Op een dag zonder echte meting tekenen we ook
    # geen rolling-averagepunt.
    result.loc[
        result["value"].isna(),
        "rolling_average",
    ] = float("nan")

    return result.reset_index()