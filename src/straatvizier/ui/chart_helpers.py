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
    if pd.isna(value):
        return ""

    ts = pd.Timestamp(value)
    end = ts + pd.Timedelta(hours=1)

    return (
        f"{ts.strftime('%d/%m/%Y')} "
        f"{ts.hour:02d}u–{end.hour:02d}u"
    )


def profile_hour_label(value):
    if pd.isna(value):
        return ""

    hour = int(value)
    return f"{hour:02d}u–{(hour + 1) % 24:02d}u"


def month_label(value):
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

    fig.add_trace(
        go.Scatter(
            x=carrier["x"],
            y=[0] * len(carrier),
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
