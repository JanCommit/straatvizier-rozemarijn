"""Voeg zichtbare autosnelheidstraces en bijbehorende hovermetadata toe aan Plotly."""

import pandas as pd
import plotly.graph_objects as go

MAIN_STREET_COLOR = "#287A8B"
COMPARE_STREET_COLOR = "#80649A"

# De V50–V95-band blijft duidelijk zichtbaar op verschillende schermen,
# maar laat de V85-lijn visueel dominant.
BAND_OPACITY = 0.28


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

    band_fill = (
        f"rgba(128, 100, 154, {BAND_OPACITY})"
        if is_comparison
        else f"rgba(40, 122, 139, {BAND_OPACITY})"
    )

    # In unified hover toont alleen V50 de gedeelde metadata.
    # Zo worden periode en aantal auto's slechts één keer vermeld.
    speed_customdata = data[["cars"]]

    # Bouw de V50–V95-band per aaneengesloten blok geldige data.
    # Plotly kan fill="tonexty" anders over NaN-gaten heen sluiten,
    # wat bij uur-, dag- en weekreeksen diagonale driehoeken veroorzaakt.
    band_valid = (
        data["x"].notna()
        & data["v50"].notna()
        & data["v95"].notna()
    )

    band_group = (
        (~band_valid)
        .cumsum()
    )

    band_segments = [
        segment
        for _, segment in data[band_valid].groupby(
            band_group[band_valid]
        )
        if not segment.empty
    ]

    for segment_index, segment in enumerate(band_segments):
        show_band_legend = segment_index == 0

        # Ondergrens van één aaneengesloten percentielband.
        fig.add_trace(
            go.Scatter(
                x=segment["x"],
                y=segment["v50"],
                mode="lines",
                connectgaps=False,
                name=f"{street} V50",
                line=dict(
                    color=base,
                    width=0,
                ),
                showlegend=False,
                hovertemplate=(
                    "V50: %{y:.1f} km/u"
                    "<extra></extra>"
                ),
            ),
            row=row,
            col=1,
        )

        # Bovengrens vult alleen tot de vorige trace van hetzelfde segment.
        # Daardoor kan de band nooit over een ontbrekende periode springen.
        fig.add_trace(
            go.Scatter(
                x=segment["x"],
                y=segment["v95"],
                mode="lines",
                connectgaps=False,
                name=f"{street} V50–V95",
                line=dict(
                    color=base,
                    width=0,
                ),
                fill="tonexty",
                fillcolor=band_fill,
                showlegend=show_band_legend,
                legendgroup=f"{street}-speed-band",
                hovertemplate=(
                    "V95: %{y:.1f} km/u"
                    "<extra></extra>"
                ),
            ),
            row=row,
            col=1,
        )

    # V85 blijft de enige duidelijke percentiellijn.
    fig.add_trace(
        go.Scatter(
            x=data["x"],
            y=data["v85"],
            mode="lines+markers",
            connectgaps=False,
            name=f"{street} V85",
            line=dict(
                color=base,
                width=2.8,
            ),
            marker=dict(
                size=4,
                color=base,
            ),
            hovertemplate=(
                "V85: %{y:.1f} km/u"
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
