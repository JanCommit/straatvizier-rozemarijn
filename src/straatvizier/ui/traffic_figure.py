import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from straatvizier.segment_config import direction_label
from straatvizier.traffic_hover_helpers import traffic_time_hover_data
from straatvizier.ui.chart_helpers import add_time_hover_carrier
from straatvizier.ui.traffic_chart import add_view

GRID_COLOR = "#D1D8DE"
AXIS_TEXT_COLOR = "#3F4B55"
SUBPLOT_TITLE_COLOR = "#365F6B"


def build_traffic_figure(
    view,
    selected_street,
    comparison_street,
    compare,
    comparison_layout,
    directions,
    daily_main_by_direction,
    daily_compare_by_direction,
    valid_main_by_direction,
    valid_compare_by_direction,
    hourly_main_by_direction,
    hourly_compare_by_direction,
    hour_profile_main_by_direction,
    hour_profile_compare_by_direction,
    traffic_label,
    min_hours,
    rolling_days,
    show_rolling,
    y_axis_from_zero,
):
    comparison_overlay = (
        compare
        and comparison_layout == "Samen in één grafiek"
    )

    rows = (
        2
        if compare and not comparison_overlay
        else 1
    )

    fig = make_subplots(
        rows=rows,
        cols=1,
        specs=[
            [{"secondary_y": True}]
            for _ in range(rows)
        ],
        shared_xaxes=(
            compare
            and not comparison_overlay
            and view in {
                "Per uur",
                "Per dag",
                "Per week",
                "Per maand",
                "Per jaar",
            }
        ),
        vertical_spacing=(
            .10
            if compare and not comparison_overlay
            else 0
        ),
        subplot_titles=(
            [
                selected_street,
                comparison_street,
            ]
            if compare and not comparison_overlay
            else None
        ),
    )

    main_hover_direction = directions[0]

    main_time_hover = traffic_time_hover_data(
        view,
        daily_main_by_direction[
            main_hover_direction
        ],
        valid_main_by_direction[
            main_hover_direction
        ],
        hourly=hourly_main_by_direction.get(
            main_hover_direction
        ),
        hour_profile=hour_profile_main_by_direction.get(
            main_hover_direction
        ),
        min_hours=min_hours,
    )

    compare_time_hover = (
        traffic_time_hover_data(
            view,
            daily_compare_by_direction[
                main_hover_direction
            ],
            valid_compare_by_direction[
                main_hover_direction
            ],
            hourly=hourly_compare_by_direction.get(
                main_hover_direction
            ),
            hour_profile=hour_profile_compare_by_direction.get(
                main_hover_direction
            ),
            min_hours=min_hours,
        )
        if compare
        else pd.DataFrame(
            columns=["x", "label"]
        )
    )

    if comparison_overlay and compare:
        combined_time_hover = pd.concat(
            [
                main_time_hover,
                compare_time_hover,
            ],
            ignore_index=True,
        ).drop_duplicates(
            subset=["x"],
            keep="first",
        )

        add_time_hover_carrier(
            fig,
            1,
            combined_time_hover["x"],
            combined_time_hover["label"],
        )
    else:
        add_time_hover_carrier(
            fig,
            1,
            main_time_hover["x"],
            main_time_hover["label"],
        )

        if compare and rows == 2:
            add_time_hover_carrier(
                fig,
                2,
                compare_time_hover["x"],
                compare_time_hover["label"],
            )


    y_label = None

    for direction in directions:
        split = len(directions) > 1
        suffix = (
            direction_label(selected_street, direction)
            if split
            else (
                direction_label(selected_street, direction)
                if direction != "both"
                else None
            )
        )
        dash = "solid" if direction in {"both", "ab"} else "dash"

        current_label = add_view(
            fig=fig,
            row=1,
            view=view,
            street=selected_street,
            daily=daily_main_by_direction[direction],
            valid=valid_main_by_direction[direction],
            label=traffic_label,
            min_hours=min_hours,
            rolling_days=rolling_days,
            show_rolling=show_rolling,
            hourly=hourly_main_by_direction.get(direction),
            hour_profile=hour_profile_main_by_direction.get(direction),
            series_suffix=suffix,
            line_dash=dash,
        )

        y_label = y_label or current_label

    if compare:
        for direction in directions:
            split = len(directions) > 1
            suffix = (
                direction_label(comparison_street, direction)
                if split
                else (
                    direction_label(comparison_street, direction)
                    if direction != "both"
                    else None
                )
            )
            dash = "solid" if direction in {"both", "ab"} else "dash"

            add_view(
                fig=fig,
                row=(1 if comparison_overlay else 2),
                view=view,
                street=comparison_street,
                daily=daily_compare_by_direction[direction],
                valid=valid_compare_by_direction[direction],
                label=traffic_label,
                min_hours=min_hours,
                rolling_days=rolling_days,
                show_rolling=show_rolling,
                hourly=hourly_compare_by_direction.get(direction),
                hour_profile=hour_profile_compare_by_direction.get(direction),
                is_comparison=True,
                series_suffix=suffix,
                line_dash=dash,
            )


    # Forceer de secundaire y-assen om zichtbaar te worden.
    # Zonder een trace op secondary_y laat Plotly de rechter ticklabels soms weg.
    fig.add_trace(
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(opacity=0),
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    if compare and not comparison_overlay:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(opacity=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
            secondary_y=True,
        )


    fig.update_yaxes(
        title_text=y_label,
        gridcolor=GRID_COLOR,
        gridwidth=1.15,
        tickfont=dict(
            size=13,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        title_font=dict(
            size=14,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        zeroline=True,
        zerolinecolor="#B8C2C9",
        zerolinewidth=1.2,
        rangemode=(
            "tozero"
            if y_axis_from_zero
            else "normal"
        ),
        row=1,
        col=1,
    )

    if compare and not comparison_overlay:
        fig.update_yaxes(
            title_text=y_label,
            gridcolor=GRID_COLOR,
            gridwidth=1.15,
            tickfont=dict(
                size=13,
                color=AXIS_TEXT_COLOR,
                family="Arial",
            ),
            title_font=dict(
                size=14,
                color=AXIS_TEXT_COLOR,
                family="Arial",
            ),
            zeroline=True,
            zerolinecolor="#B8C2C9",
            zerolinewidth=1.2,
            rangemode=(
                "tozero"
                if y_axis_from_zero
                else "normal"
            ),
            row=2,
            col=1,
        )


    # Dezelfde y-schaal ook rechts tonen.
    # Alleen de cijfers worden gespiegeld; de as-titel blijft links.
    fig.update_yaxes(
        title_text=None,
        showgrid=False,
        zeroline=False,
        showticklabels=True,
        ticks="outside",
        tickfont=dict(
            size=13,
            color=AXIS_TEXT_COLOR,
            family="Arial",
        ),
        matches="y",
        row=1,
        col=1,
        secondary_y=True,
    )

    if compare and not comparison_overlay:
        fig.update_yaxes(
            title_text=None,
            showgrid=False,
            zeroline=False,
            showticklabels=True,
            ticks="outside",
            tickfont=dict(
                size=13,
                color=AXIS_TEXT_COLOR,
                family="Arial",
            ),
            matches="y3",
            row=2,
            col=1,
            secondary_y=True,
        )


    traffic_x_title = {
        "Per uur": "Tijd (per uur)",
        "Per dag": "Tijd (per dag)",
        "Per week": "Tijd (per week)",
        "Per maand": "Tijd (per maand)",
        "Per jaar": "Tijd (per jaar)",
        "24u-profiel": "Uur in dag",
        "Weekprofiel": "Dag in week",
        "Jaarprofiel": "Maand in jaar",
    }[view]

    fig.update_xaxes(
        title_text=traffic_x_title,
        unifiedhovertitle=dict(
            text="&#8203;",
        ),
        tickfont=dict(
            size=12,
            color=AXIS_TEXT_COLOR,
        ),
        gridcolor="#E7EBEE",
        gridwidth=.7,
    )

    # Bij vergelijking: toon tijdslabels ook op de bovenste gedeelde x-as.
    if (
        compare
        and not comparison_overlay
        and view in {
            "Per uur",
            "Per dag",
            "Per week",
            "Per maand",
            "Per jaar",
        }
    ):
        fig.update_xaxes(
            showticklabels=True,
            row=1,
            col=1,
        )


    for annotation in fig.layout.annotations:
        annotation.font = dict(
            size=17,
            color=SUBPLOT_TITLE_COLOR,
            family="Arial",
        )


    fig.update_layout(
        height=(
            720
            if compare and not comparison_overlay
            else 500
        ),
        hovermode="x unified",
        legend_title=None,
        legend=dict(
            font=dict(
                size=12,
                color=AXIS_TEXT_COLOR,
            ),
            bgcolor="rgba(255,255,255,0.75)",
        ),
        margin=dict(
            t=(
                45
                if compare and not comparison_overlay
                else 20
            ),
            l=20,
            r=55,
            b=20,
        ),
    )


    return fig
