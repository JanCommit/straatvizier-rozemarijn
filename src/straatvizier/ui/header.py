"""Render de vaste dashboardheader met de actuele analysecontext."""

import re

import streamlit as st


IVORY = "#F4F1E8"
SAGE = "#C7D0C2"


def render_frozen_header(
    title,
    selected_street,
    valid_days,
    avg_uptime_text,
    start_hour,
    end_hour,
    uptime_pct,
    min_hours,
    direction_choice,
    main_first,
    main_last,
    compare,
    comparison_street,
    comparison_layout,
):
    """Render de vaste header voor analyse-type, straatcontext en gekozen weergave."""
    comparison_note = (
        (
            f" · vergelijking met {comparison_street}"
            + (
                " · samen in één grafiek"
                if comparison_layout == "Samen in één grafiek"
                else ""
            )
        )
        if compare
        else ""
    )

    uptime_match = re.search(r"(\d+(?:[.,]\d+)?)", str(avg_uptime_text))
    uptime_pct_value = (
        max(0.0, min(100.0, float(uptime_match.group(1).replace(",", "."))))
        if uptime_match
        else None
    )
    uptime_degrees = (
        uptime_pct_value * 3.6
        if uptime_pct_value is not None
        else 0
    )

    st.html(
        f"""
        <style>
            .sv-head {{
                position: fixed;
                top: 3.6rem;
                left: 22rem;
                right: 1.25rem;
                z-index: 9999;
                overflow: hidden;
                background:
                    radial-gradient(circle at 78% 15%, rgba(45,127,203,.18), transparent 34%),
                    linear-gradient(118deg, #082B52 0%, #0A315D 55%, #0D467D 100%);
                border: 1px solid rgba(255,255,255,.10);
                border-radius: 15px;
                padding: .9rem 1.15rem 1rem;
                box-shadow: 0 10px 28px rgba(14,42,67,.18);
            }}

            .sv-wave {{
                position: absolute;
                z-index: 0;
                right: 0;
                bottom: 0;
                width: 49%;
                height: 100%;
                pointer-events: none;
                opacity: .98;
            }}

            .sv-head-content {{
                position: relative;
                z-index: 2;
            }}

            .sv-title {{
                font-size: 1.38rem;
                font-weight: 720;
                line-height: 1.2;
                color: {IVORY};
                margin-bottom: .22rem;
                letter-spacing: -.012em;
            }}

            .sv-context {{
                font-size: .84rem;
                color: #C7D8E6;
                margin-bottom: .82rem;
            }}

            .sv-metrics {{
                display: grid;
                grid-template-columns: repeat(4, minmax(0,1fr));
                gap: 0;
            }}

            .sv-metric {{
                display: grid;
                grid-template-columns: 2.75rem minmax(0,1fr);
                align-items: center;
                gap: .72rem;
                min-width: 0;
                padding: .15rem 1rem .1rem 0;
            }}

            .sv-metric + .sv-metric {{
                padding-left: 1.15rem;
                border-left: 1px solid rgba(205,225,240,.19);
            }}

            .sv-iconbox {{
                width: 2.62rem;
                height: 2.62rem;
                display: grid;
                place-items: center;
                border-radius: .76rem;
                background:
                    linear-gradient(
                        145deg,
                        rgba(73,154,226,.24),
                        rgba(37,102,169,.14)
                    );
                border: 1px solid rgba(118,183,238,.23);
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.05),
                    0 4px 12px rgba(1,21,43,.08);
            }}

            .sv-label {{
                font-size: .72rem;
                font-weight: 650;
                letter-spacing: .02em;
                color: #9FC7E5;
                margin-bottom: .07rem;
            }}

            .sv-value {{
                font-size: 1.16rem;
                line-height: 1.12;
                font-weight: 720;
                color: #F8F7F2;
            }}

            /* Pure CSS calendar icon: no external icon font or SVG dependency. */
            .sv-calendar {{
                position: relative;
                width: 1.45rem;
                height: 1.28rem;
                border: 2px solid #EDF7FF;
                border-radius: .22rem;
                box-sizing: border-box;
            }}

            .sv-calendar::before {{
                content: "";
                position: absolute;
                left: -.12rem;
                right: -.12rem;
                top: .28rem;
                border-top: 2px solid #EDF7FF;
                box-shadow:
                    .36rem -.42rem 0 -.28rem #EDF7FF,
                    1.02rem -.42rem 0 -.28rem #EDF7FF;
            }}

            .sv-calendar-dots {{
                position: absolute;
                left: .27rem;
                top: .62rem;
                width: .18rem;
                height: .18rem;
                border-radius: 50%;
                background: #75BFFF;
                box-shadow:
                    .38rem 0 #75BFFF,
                    .76rem 0 #75BFFF,
                    0 .34rem #75BFFF,
                    .38rem .34rem #75BFFF,
                    .76rem .34rem #75BFFF;
            }}

            .sv-badge {{
                position: absolute;
                right: -.48rem;
                bottom: -.43rem;
                width: .95rem;
                height: .95rem;
                display: grid;
                place-items: center;
                border-radius: 50%;
                font-size: .63rem;
                line-height: 1;
                font-weight: 800;
                border: 2px solid #0A315D;
            }}

            .sv-badge-blue {{
                color: #EAF6FF;
                background: #2C8FE7;
            }}

            .sv-badge-green {{
                color: #07375A;
                background: #42D27A;
            }}

            .sv-uptime-ring {{
                width: 1.72rem;
                height: 1.72rem;
                border-radius: 50%;
                background:
                    conic-gradient(
                        #42D27A 0deg {uptime_degrees:.2f}deg,
                        rgba(117,190,224,.20) {uptime_degrees:.2f}deg 360deg
                    );
                position: relative;
                box-shadow: 0 0 12px rgba(66,210,122,.12);
            }}

            .sv-uptime-ring::after {{
                content: "";
                position: absolute;
                inset: .23rem;
                border-radius: 50%;
                background: #0A315D;
            }}

            .sv-uptime-ring.na {{
                background: rgba(117,190,224,.20);
            }}

            .sv-spacer {{
                height: 10.3rem;
            }}

            @media(max-width:900px) {{
                .sv-head {{
                    left: 1rem;
                    right: 1rem;
                    top: 3.4rem;
                }}

                .sv-wave {{
                    width: 68%;
                    opacity: .76;
                }}

                .sv-metrics {{
                    grid-template-columns: repeat(2,1fr);
                    row-gap: .68rem;
                }}

                .sv-metric:nth-child(3) {{
                    border-left: none;
                    padding-left: 0;
                }}

                .sv-spacer {{
                    height: 14.3rem;
                }}
            }}
        </style>

        <div class="sv-head">
            <svg class="sv-wave"
                 viewBox="0 0 760 220"
                 preserveAspectRatio="none"
                 aria-hidden="true">
                <defs>
                    <linearGradient id="svWaveA" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="#0B3E74" stop-opacity="0"/>
                        <stop offset="54%" stop-color="#1F6FB5" stop-opacity=".26"/>
                        <stop offset="100%" stop-color="#56A9E9" stop-opacity=".47"/>
                    </linearGradient>
                    <linearGradient id="svWaveB" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="#1D72B7" stop-opacity="0"/>
                        <stop offset="63%" stop-color="#3095D7" stop-opacity=".18"/>
                        <stop offset="100%" stop-color="#79BDE9" stop-opacity=".30"/>
                    </linearGradient>
                    <linearGradient id="svGreenLine" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="#42D27A" stop-opacity="0"/>
                        <stop offset="65%" stop-color="#42D27A" stop-opacity=".38"/>
                        <stop offset="100%" stop-color="#42D27A" stop-opacity=".82"/>
                    </linearGradient>
                </defs>

                <path
                    d="M0,220
                       C90,210 135,190 192,169
                       C262,143 288,152 343,135
                       C414,113 432,75 503,66
                       C573,57 591,82 641,50
                       C685,22 711,5 760,2
                       L760,220 Z"
                    fill="url(#svWaveA)"
                />

                <path
                    d="M70,220
                       C155,194 194,193 252,181
                       C328,165 347,137 411,130
                       C476,123 504,143 557,119
                       C616,92 632,72 684,77
                       C711,80 734,67 760,58
                       L760,220 Z"
                    fill="url(#svWaveB)"
                />

                <path
                    d="M144,220
                       C226,199 270,202 329,190
                       C399,175 421,148 480,143
                       C541,138 563,157 613,144
                       C669,129 701,99 760,100"
                    fill="none"
                    stroke="#8AC7F0"
                    stroke-opacity=".48"
                    stroke-width="1.4"
                />

                <path
                    d="M352,220
                       C428,207 465,208 514,195
                       C568,181 596,156 646,157
                       C696,157 724,134 760,127"
                    fill="none"
                    stroke="url(#svGreenLine)"
                    stroke-width="1.6"
                />
            </svg>

            <div class="sv-head-content">
                <div class="sv-title">
                    {title} — {selected_street}
                </div>

                <div class="sv-context">
                    Lokale Belgische tijd
                    {start_hour:02d}:00–{end_hour:02d}:00
                    · minimum uptime {uptime_pct}%
                    · minimum {min_hours} geldige uren per dag
                    · {direction_choice}
                    {comparison_note}
                </div>

                <div class="sv-metrics">
                    <div class="sv-metric">
                        <div class="sv-iconbox" aria-hidden="true">
                            <div class="sv-calendar">
                                <span class="sv-calendar-dots"></span>
                                <span class="sv-badge sv-badge-blue">→</span>
                            </div>
                        </div>
                        <div>
                            <div class="sv-label">Eerste meting</div>
                            <div class="sv-value">
                                {main_first.strftime("%d/%m/%Y")}
                            </div>
                        </div>
                    </div>

                    <div class="sv-metric">
                        <div class="sv-iconbox" aria-hidden="true">
                            <div class="sv-calendar">
                                <span class="sv-calendar-dots"></span>
                                <span class="sv-badge sv-badge-blue">←</span>
                            </div>
                        </div>
                        <div>
                            <div class="sv-label">Laatste meting</div>
                            <div class="sv-value">
                                {main_last.strftime("%d/%m/%Y")}
                            </div>
                        </div>
                    </div>

                    <div class="sv-metric">
                        <div class="sv-iconbox" aria-hidden="true">
                            <div class="sv-calendar">
                                <span class="sv-calendar-dots"></span>
                                <span class="sv-badge sv-badge-green">✓</span>
                            </div>
                        </div>
                        <div>
                            <div class="sv-label">Geldige dagen</div>
                            <div class="sv-value">{valid_days}</div>
                        </div>
                    </div>

                    <div class="sv-metric">
                        <div class="sv-iconbox" aria-hidden="true">
                            <div class="sv-uptime-ring{' na' if uptime_pct_value is None else ''}"></div>
                        </div>
                        <div>
                            <div class="sv-label">Gem. uptime</div>
                            <div class="sv-value">{avg_uptime_text}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="sv-spacer"></div>
        """
    )
