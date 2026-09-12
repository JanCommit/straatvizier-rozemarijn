"""Gedeelde Nederlandse labels en Plotly-hoverhelpers voor StraatVizier-grafieken."""

from numbers import Number

import pandas as pd
import plotly.graph_objects as go


MONTH_NAMES_NL = {
    1: "januari",
    2: "februari",
    3: "maart",
    4: "april",
    5: "mei",
    6: "juni",
    7: "juli",
    8: "augustus",
    9: "september",
    10: "oktober",
    11: "november",
    12: "december",
}

MONTH_ABBR_NL = {
    1: "Jan",
    2: "Feb",
    3: "Mrt",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Dec",
}

WEEKDAY_ABBR_NL = [
    "Ma",
    "Di",
    "Wo",
    "Do",
    "Vr",
    "Za",
    "Zo",
]

WEEKDAY_NAMES_NL = [
    "Maandag",
    "Dinsdag",
    "Woensdag",
    "Donderdag",
    "Vrijdag",
    "Zaterdag",
    "Zondag",
]


def hour_period_label(value):
    """Formatteer een timestamp als Nederlandse uurperiode voor de hover."""
    if pd.isna(value):
        return ""

    ts = pd.Timestamp(value)
    end = ts + pd.Timedelta(hours=1)

    return (
        f"{ts.strftime('%d/%m/%Y')} "
        f"{ts.hour:02d}u–{end.hour:02d}u"
    )


def profile_hour_label(value):
    """Formatteer een profieluur als leesbare uurperiode zonder datum."""
    if pd.isna(value):
        return ""

    hour = int(value)
    return f"{hour:02d}u–{(hour + 1) % 24:02d}u"


def month_label(value):
    """Geef de volledige Nederlandse maandnaam met jaar terug."""
    if pd.isna(value):
        return ""

    ts = pd.Timestamp(value)
    return f"{MONTH_NAMES_NL[ts.month].capitalize()} {ts.year}"


def add_time_hover_carrier(
    fig,
    row,
    x,
    labels,
):
    """Voeg één centrale tijdstitel bovenaan de unified hover toe."""
    if x is None or len(x) == 0:
        return

    carrier = pd.DataFrame(
        {
            "x": list(x),
            "label": list(labels),
        }
    ).dropna(subset=["x"])

    if carrier.empty:
        return

    carrier = carrier.drop_duplicates(
        subset=["x"],
        keep="first",
    )

    subplot = fig.get_subplot(row, 1)
    yaxis_name = subplot.yaxis.plotly_name
    target_yaxis = (
        "y"
        if yaxis_name == "yaxis"
        else yaxis_name.replace("yaxis", "y")
    )

    def normalize_x(value):
        if pd.isna(value):
            return None

        if isinstance(value, Number):
            return float(value)

        try:
            return pd.Timestamp(value).value
        except (TypeError, ValueError):
            return str(value)

    carrier_y_by_x = {}

    for trace in fig.data:
        trace_yaxis = getattr(trace, "yaxis", None) or "y"

        if trace_yaxis != target_yaxis:
            continue

        trace_x = getattr(trace, "x", None)
        trace_y = getattr(trace, "y", None)

        if trace_x is None or trace_y is None:
            continue

        for x_value, y_value in zip(trace_x, trace_y):
            if pd.isna(x_value) or pd.isna(y_value):
                continue

            carrier_y_by_x.setdefault(
                normalize_x(x_value),
                y_value,
            )

    carrier_y = [
        carrier_y_by_x.get(
            normalize_x(x_value)
        )
        for x_value in carrier["x"]
    ]

    if not any(pd.notna(value) for value in carrier_y):
        return

    fig.add_trace(
        go.Scatter(
            x=carrier["x"],
            y=carrier_y,
            mode="markers",
            marker=dict(
                size=0.1,
                opacity=0,
            ),
            showlegend=False,
            text=carrier["label"],
            hovertemplate=(
                "<b>%{text}</b>"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=1,
    )

    # Plotly toont unified-hoverregels in tracevolgorde.
    # Zet alleen deze onzichtbare tijdtrace vóór de echte traces
    # van dezelfde subplot, zodat de tijdsaanduiding bovenaan staat.
    carrier_trace = fig.data[-1]
    other_traces = list(fig.data[:-1])

    insert_at = next(
        (
            index
            for index, trace in enumerate(other_traces)
            if (getattr(trace, "yaxis", None) or "y")
            == target_yaxis
        ),
        len(other_traces),
    )

    reordered = (
        other_traces[:insert_at]
        + [carrier_trace]
        + other_traces[insert_at:]
    )

    fig.data = tuple(reordered)

