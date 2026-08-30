"""Voeg zichtbare autosnelheidstraces en bijbehorende hovermetadata toe aan Plotly."""

import plotly.graph_objects as go

MAIN_STREET_COLOR = "#1E88E5"
COMPARE_STREET_COLOR = "#80649A"
MAIN_TREND_COLOR = "#E8655B"
COMPARE_TREND_COLOR = "#6F5A8C"


def valid_daily_speed(
    df,
    min_hours,
):
    """Beperk dagelijkse snelheidsdata tot dagen met voldoende geldige meeturen."""
    if df.empty:
        return df.copy()

    return df[
        df["hours"] >= min_hours
    ].copy()


def add_speed_traces(
    fig,
    row,
    data,
    street,
    is_comparison=False,
):
    """Voeg V50/V85/V95 en de benodigde hovermetadata voor één straat toe."""
    if data is None or data.empty:
        return

    base = (
        COMPARE_STREET_COLOR
        if is_comparison
        else MAIN_STREET_COLOR
    )

    trend = (
        COMPARE_TREND_COLOR
        if is_comparison
        else MAIN_TREND_COLOR
    )

    # In unified hover toont alleen V50 de gedeelde metadata.
    # Zo worden periode en aantal auto's slechts één keer vermeld.
    speed_customdata = data[["cars"]]

    v50_hover = (
        "V50: %{y:.1f} km/u"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v50"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V50",
            line=dict(
                color=base,
                width=2,
            ),
            marker=dict(
                size=4,
                color=base,
            ),
            customdata=speed_customdata,
            hovertemplate=v50_hover,
        ),
        row=row,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v85"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V85",
            line=dict(
                color=trend,
                width=2.8,
            ),
            marker=dict(
                size=4,
                color=trend,
            ),
            hovertemplate=(
                "V85: %{y:.1f} km/u"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v95"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V95",
            line=dict(
                color=base,
                width=1.5,
                dash="dash",
            ),
            marker=dict(
                size=4,
                color=base,
            ),
            hovertemplate=(
                "V95: %{y:.1f} km/u"
                "<extra></extra>"
            ),
        ),
        row=row,
        col=1,
    )


    metadata_hover = (
        "Auto's in verdeling: %{customdata[0]:,.0f}"
        "<extra></extra>"
    )

    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v50"],
            mode="markers",
            marker=dict(
                size=0.1,
                opacity=0,
            ),
            showlegend=False,
            customdata=speed_customdata,
            hovertemplate=metadata_hover,
        ),
        row=row,
        col=1,
    )
