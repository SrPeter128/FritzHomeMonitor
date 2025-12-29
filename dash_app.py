from datetime import datetime
import math
from pathlib import Path
import numpy as np
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

DATA_DIR = Path(__file__).resolve().parent
REFRESH_MS = 5000
MAX_ROWS = 200000
LOG_MIN_POWER = 0.1


def list_device_files():
    return sorted(p for p in DATA_DIR.glob("*.tsv") if p.name != "devices.tsv")


def load_device_df(path):
    try:
        df = pd.read_csv(path, sep="\t")
    except Exception:
        return pd.DataFrame()

    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df = df.sort_values("Timestamp")

    if len(df) > MAX_ROWS:
        df = df.tail(MAX_ROWS)

    return df


def filter_df_by_range(df, range_value):
    if "Timestamp" not in df.columns or df["Timestamp"].isna().all():
        return df

    now = pd.Timestamp.now()
    if range_value == "day":
        cutoff = now - pd.Timedelta(days=1)
    elif range_value == "hour":
        cutoff = now - pd.Timedelta(hours=1)
    elif range_value == "week":
        cutoff = now - pd.Timedelta(weeks=1)
    elif range_value == "month":
        cutoff = now - pd.Timedelta(days=30)
    else:
        return df

    return df[df["Timestamp"] >= cutoff]


def make_empty_figure(title):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Value",
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        height=260,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def set_log_yaxis(fig, min_value=None, max_value=None):
    fig.update_yaxes(type="log")
    if min_value is None:
        return
    if max_value is not None and max_value > 0:
        upper = max(max_value, min_value * 10)
        fig.update_yaxes(range=[math.log10(min_value), math.log10(upper)])


def clamp_log_series(df, column, min_value):
    if column not in df.columns:
        return df
    df = df.copy()
    df[column] = df[column].clip(lower=min_value)
    return df


def build_time_axis(df):
    if "Timestamp" in df.columns and df["Timestamp"].notna().any():
        return df["Timestamp"]
    return list(range(len(df)))


def add_series(fig, df, column, label):
    if column not in df.columns:
        return
    fig.add_trace(go.Scatter(x=build_time_axis(df), y=df[column], mode="lines", name=label))


def add_switch_markers(fig, df, label, color):
    if "NewSwitchState" not in df.columns:
        return
    changes = df["NewSwitchState"].ne(df["NewSwitchState"].shift(1)) & df["NewSwitchState"].notna()
    if not changes.any():
        return

    on_mask = changes & (df["NewSwitchState"] == "ON")
    off_mask = changes & (df["NewSwitchState"] == "OFF")
    x_values = build_time_axis(df)
    y_values = df.get("NewMultimeterPower", pd.Series([0] * len(df)))
    print(y_values)
    if on_mask.any():
        fig.add_trace(
            go.Scatter(
                x=x_values[on_mask],
                y=np.full((1,y_values.shape[0], 1000)[0],0.12),
                mode="markers",
                name=f"{label} ON",
                marker=dict(color=color, size=8, symbol="triangle-up"),
            )
        )
    if off_mask.any():
        fig.add_trace(
            go.Scatter(
                x=x_values[off_mask],
                y=np.full((1,y_values.shape[0], 1000)[0], 0.12),
                mode="markers",
                name=f"{label} OFF",
                marker=dict(color=color, size=8, symbol="triangle-down", line=dict(color="#222")),
            )
        )


app = dash.Dash(__name__)
app.title = "Energy Monitor Live"

app.layout = html.Div(
    style={
        "minHeight": "100vh",
        "background": "radial-gradient(circle at top, #1d1f2a 0%, #0f1117 45%, #0b0c10 100%)",
        "color": "#e7e9ee",
        "fontFamily": "'Space Grotesk', 'Segoe UI', sans-serif",
    },
    children=[
        html.Div(
            style={"maxWidth": "1100px", "margin": "0 auto", "padding": "28px 24px 40px"},
            children=[
                html.H2("Pfalzsprung Smarthome Live", style={"marginBottom": "6px", "letterSpacing": "0.5px"}),
                html.Div(
                    "Live plots from per-device TSV logs.",
                    style={"color": "#a9afc3", "marginBottom": "18px"},
                ),
                html.Div(
                    style={
                        "display": "flex",
                        "gap": "16px",
                        "alignItems": "center",
                        "flexWrap": "wrap",
                        "marginBottom": "8px",
                    },
                    children=[
                        html.Div("Time window:", style={"fontWeight": "bold", "color": "#cdd3e6"}),
                        dcc.RadioItems(
                            id="time-range",
                            options=[
                                {"label": "Last hour", "value": "hour"},
                                {"label": "Last day", "value": "day"},
                                {"label": "Last week", "value": "week"},
                                {"label": "Last month", "value": "month"},
                                {"label": "All data", "value": "all"},
                            ],
                            value="week",
                            inline=True,
                            style={"color": "#cdd3e6"},
                            inputStyle={"marginRight": "6px", "marginLeft": "8px"},
                        ),
                    ],
                ),
                html.Div(id="data-warning", style={"color": "#ff8f8f", "marginTop": "8px"}),
                html.Div(
                    id="switch-state",
                    style={"marginTop": "8px", "fontWeight": "bold", "color": "#d6dbef"},
                ),
                dcc.Graph(id="power-graph", figure=make_empty_figure("Power (mW)")),
                dcc.Graph(id="energy-graph", figure=make_empty_figure("Energy (Wh)")),
                dcc.Graph(id="temp-graph", figure=make_empty_figure("Temperature (0.1 °C)")),
                dcc.Interval(id="interval", interval=REFRESH_MS, n_intervals=0),
            ],
        )
    ],
)


@app.callback(
    Output("power-graph", "figure"),
    Output("energy-graph", "figure"),
    Output("temp-graph", "figure"),
    Output("switch-state", "children"),
    Output("data-warning", "children"),
    Input("interval", "n_intervals"),
    Input("time-range", "value"),
)
def refresh_graphs(_, time_range):
    device_files = list_device_files()
    if not device_files:
        empty = make_empty_figure("No data")
        return empty, empty, empty, "Switch: —", "No device TSV files found."

    power_fig = make_empty_figure("Leistung (KW)")
    energy_fig = make_empty_figure("Energie (KWh)")
    temp_fig = make_empty_figure("Temperatur (°C)")
    set_log_yaxis(power_fig)
    set_log_yaxis(energy_fig)

    palette = qualitative.D3
    color_map = {p.stem: palette[i % len(palette)] for i, p in enumerate(device_files)}

    switch_state_parts = []
    max_power = None
    for path in device_files:
        df = load_device_df(path)
        if df.empty:
            continue
        df = filter_df_by_range(df, time_range)
        if df.empty:
            continue
        label = path.stem
        color = color_map.get(label, "#444")
        df_power = clamp_log_series(df, "NewMultimeterPower", LOG_MIN_POWER)
        power_max = df_power.get("NewMultimeterPower", pd.Series(dtype="float64")).max()
        if pd.notna(power_max):
            max_power = power_max if max_power is None else max(max_power, power_max)
        add_series(power_fig, df_power, "NewMultimeterPower", label)
        add_switch_markers(power_fig, df_power, label, color)
        add_series(energy_fig, df, "NewMultimeterEnergy", label)
        add_series(temp_fig, df, "NewTemperatureCelsius", label)

        latest = df.iloc[-1]
        latest_ts = latest.get("Timestamp")
        if pd.isna(latest_ts):
            latest_ts = datetime.now()
        ts_label = pd.to_datetime(latest_ts).strftime("%Y-%m-%d %H:%M:%S")
        switch_state = latest.get("NewSwitchState", "—")
        switch_state_parts.append(f"{label}: {switch_state} @ {ts_label}")

    if not power_fig.data:
        empty = make_empty_figure("No data")
        return empty, empty, empty, "Switch: —", "No device data available."

    if max_power is not None:
        set_log_yaxis(power_fig, min_value=LOG_MIN_POWER, max_value=max_power)

    return (
        power_fig,
        energy_fig,
        temp_fig,
        " | ".join(switch_state_parts) if switch_state_parts else "Switch: —",
        "",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=True)
