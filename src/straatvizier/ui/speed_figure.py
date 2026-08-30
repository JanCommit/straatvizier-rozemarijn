import pandas as pd
from plotly.subplots import make_subplots

from straatvizier.ui.chart_helpers import (
    MONTH_ABBR_NL,
    WEEKDAY_ABBR_NL,
    add_time_hover_carrier,
)
from straatvizier.speed_helpers import speed_time_hover_data
from straatvizier.ui.speed_chart import add_speed_traces

GRID_COLOR = "#D1D8DE"


def build_speed_figure(
    speed_view,
    main_speed_plot,
    compare_speed_plot,
    selected_street,
    comparison_street,
    compare,
    comparison_layout,
    y_axis_from_zero,
    overlay,
    speed_rows,
):
    speed_fig = make_subplots(
        rows=speed_rows,
        cols=1,
        shared_xaxes=(
            compare
            and not overlay
            and speed_view in {
                "Per uur",
                "Per dag",
                "Per week",
                "Per maand",
                "Per jaar",
            }
        ),
        vertical_spacing=(
            .10
            if speed_rows == 2
            else 0
        ),
        subplot_titles=(
            [
                selected_street,
                comparison_street,
            ]
            if speed_rows == 2
            else None
        ),
    )

    main_speed_hover = speed_time_hover_data(
        speed_view,
        main_speed_plot,
    )

    compare_speed_hover = (
        speed_time_hover_data(
            speed_view,
            compare_speed_plot,
        )
        if compare
        else pd.DataFrame(
            columns=["x", "label"]
        )
    )

    if overlay and compare:
        combined_speed_hover = pd.concat(
            [
                main_speed_hover,
                compare_speed_hover,
            ],
            ignore_index=True,
        ).drop_duplicates(
            subset=["x"],
            keep="first",
        )

        add_time_hover_carrier(
            speed_fig,
            1,
            combined_speed_hover["x"],
            combined_speed_hover["label"],
        )
    else:
        add_time_hover_carrier(
            speed_fig,
            1,
            main_speed_hover["x"],
            main_speed_hover["label"],
        )

        if compare and speed_rows == 2:
            add_time_hover_carrier(
                speed_fig,
                2,
                compare_speed_hover["x"],
                compare_speed_hover["label"],
            )

    add_speed_traces(
        speed_fig,
        1,
        main_speed_plot,
        selected_street,
    )

    if compare:
        add_speed_traces(
            speed_fig,
            1 if overlay else 2,
            compare_speed_plot,
            comparison_street,
            True,
        )

    speed_x_title = {
        "Per uur": "Tijd (per uur)",
        "Per dag": "Tijd (per dag)",
        "Per week": "Tijd (per week)",
        "Per maand": "Tijd (per maand)",
        "Per jaar": "Tijd (per jaar)",
        "24u-profiel": "Uur in dag",
        "Weekprofiel": "Dag in week",
        "Jaarprofiel": "Maand in jaar",
    }[speed_view]

    speed_fig.update_xaxes(
        title_text=speed_x_title,
        unifiedhovertitle=dict(
            text="&#8203;",
        ),
    )

    if speed_view == "24u-profiel":
        speed_fig.update_xaxes(
            dtick=1,
        )

    elif speed_view == "Weekprofiel":
        speed_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=WEEKDAY_ABBR_NL,
        )

    elif speed_view == "Jaarprofiel":
        speed_fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(1, 13)),
            ticktext=[
                MONTH_ABBR_NL[index]
                for index in range(1, 13)
            ],
        )

    speed_fig.update_yaxes(
        title_text=(
            "Autosnelheid (km/u)"
        ),
        gridcolor=GRID_COLOR,
        rangemode=(
            "tozero"
            if y_axis_from_zero
            else "normal"
        ),
    )

    speed_fig.update_layout(
        height=(
            720
            if speed_rows == 2
            else 520
        ),
        hovermode="x unified",
        margin=dict(
            t=(
                45
                if speed_rows == 2
                else 20
            ),
            l=20,
            r=30,
            b=20,
        ),
    )

    return speed_fig


