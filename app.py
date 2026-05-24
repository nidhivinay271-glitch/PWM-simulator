"""
PWM Signal Simulator Dashboard
A web-based dashboard to simulate PWM signals and visualize their effects on LED brightness and motor speed.
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import plotly.graph_objects as go


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="PWM Signal Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        .main {
            padding: 0px;
        }
        .metric-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
            font-weight: bold;
        }
        .led-indicator {
            display: inline-block;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            margin: 10px;
            box-shadow: 0 0 20px rgba(255, 255, 0, 0.8);
        }
        .motor-speed {
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
            margin: 10px 0;
        }
        .feature-card {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(102, 126, 234, 0.12);
            margin-top: 10px;
        }
        .feature-title {
            font-size: 15px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 12px;
            letter-spacing: 0.2px;
        }
        .led-orb {
            width: 74px;
            height: 74px;
            border-radius: 50%;
            margin: 0 auto;
            background: radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 1), rgba(255, 240, 130, 0.92) 32%, rgba(255, 188, 0, 0.95) 62%, rgba(255, 94, 58, 0.88) 100%);
            animation: ledPulse 1.8s ease-in-out infinite;
        }
        @keyframes ledPulse {
            0%, 100% { transform: scale(0.94); }
            50% { transform: scale(1.08); }
        }
        .gear-spin {
            display: inline-block;
            font-size: 64px;
            line-height: 1;
            animation: spin 3s linear infinite;
            transform-origin: center center;
        }
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        .sound-pulse {
            display: inline-block;
            font-size: 54px;
            line-height: 1;
            animation: soundBeat 1.2s ease-in-out infinite;
        }
        @keyframes soundBeat {
            0%, 100% { transform: scale(0.95); opacity: 0.72; }
            50% { transform: scale(1.12); opacity: 1; }
        }
        .heat-stage {
            position: relative;
            border-radius: 14px;
            overflow: hidden;
            padding: 16px 14px 10px;
            background: linear-gradient(135deg, rgba(255, 243, 205, 0.96), rgba(255, 183, 77, 0.92), rgba(211, 47, 47, 0.9));
        }
        .heat-bars {
            display: flex;
            align-items: flex-end;
            justify-content: center;
            gap: 8px;
            min-height: 76px;
        }
        .heat-bars span {
            width: 14px;
            border-radius: 999px 999px 0 0;
            background: linear-gradient(180deg, #fff59d 0%, #ff9800 55%, #f44336 100%);
            animation: heatRise 1.4s ease-in-out infinite;
        }
        @keyframes heatRise {
            0%, 100% { transform: scaleY(0.72); opacity: 0.68; }
            50% { transform: scaleY(1.05); opacity: 1; }
        }
        .insight-card {
            background: rgba(255, 255, 255, 0.94);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.08);
            border-left: 6px solid #667eea;
        }
        .insight-label {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.3px;
            margin-bottom: 10px;
            color: white;
        }
        .comparison-card {
            background: linear-gradient(135deg, rgba(247, 250, 255, 0.95), rgba(235, 244, 255, 0.98));
            border-radius: 16px;
            padding: 18px;
            border: 1px solid rgba(102, 126, 234, 0.14);
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# TITLE AND HEADER
# ============================================================================
st.title("⚡ PWM Signal Simulator Dashboard")
st.markdown("---")
st.markdown(
    "Adjust the duty cycle and frequency to simulate PWM signals and observe their effects on LED brightness and motor speed."
)


# ============================================================================
# INPUT SECTION - Sidebar Controls
# ============================================================================
st.sidebar.header("🎚️ PWM Controls")
st.sidebar.markdown("---")

# === NEW FEATURE START ===
preset_options = {
    "Eco": 25,
    "Normal": 50,
    "Performance": 85
}

if "preset_mode" not in st.session_state:
    st.session_state.preset_mode = "Normal"
if "duty_cycle" not in st.session_state:
    st.session_state.duty_cycle = preset_options[st.session_state.preset_mode]


def apply_preset_mode():
    st.session_state.duty_cycle = preset_options[st.session_state.preset_mode]


preset_mode = st.sidebar.selectbox(
    label="Preset Modes",
    options=list(preset_options.keys()),
    key="preset_mode",
    on_change=apply_preset_mode,
    help="Choose a quick PWM profile for the duty cycle"
)
# === NEW FEATURE END ===

# Duty Cycle Slider
duty_cycle = st.sidebar.slider(
    label="Duty Cycle (%)",
    min_value=0,
    max_value=100,
    step=1,
    key="duty_cycle",
    help="Percentage of time the signal is HIGH in one cycle"
)

# Frequency Input
frequency = st.sidebar.number_input(
    label="Frequency (Hz)",
    min_value=1,
    max_value=10000,
    value=1000,
    step=100,
    help="Number of PWM cycles per second"
)

# Time Duration for waveform display
time_duration = st.sidebar.slider(
    label="Time Window (ms)",
    min_value=1,
    max_value=10,
    value=5,
    step=1,
    help="Duration of waveform to display"
)

# === NEW FEATURE START ===
comparison_mode = st.sidebar.checkbox(
    label="Enable Comparison Mode",
    value=False,
    key="comparison_mode",
    help="Compare the current PWM setting with a second duty cycle"
)

if comparison_mode:
    if "comparison_duty_cycle" not in st.session_state:
        st.session_state.comparison_duty_cycle = min(85, duty_cycle + 20)

    comparison_duty_cycle = st.sidebar.slider(
        label="Comparison Duty Cycle (%)",
        min_value=0,
        max_value=100,
        step=1,
        key="comparison_duty_cycle",
        help="Second PWM setting used for comparison"
    )
else:
    comparison_duty_cycle = None
# === NEW FEATURE END ===

# NEW: Device selection for the application simulation panel
selected_device = st.sidebar.selectbox(
    label="Device",
    options=["LED", "Motor", "Buzzer", "Heater"],
    index=0,
    help="Choose the device to preview in the simulation panel"
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tips:**\n"
    "- Higher duty cycle increases LED brightness\n"
    "- Higher frequency increases motor smoothness\n"
    "- 0% duty cycle turns OFF, 100% turns ON"
)


# ============================================================================
# PROCESSING SECTION - PWM Waveform Generation
# ============================================================================
def generate_pwm_signal(duty_cycle, frequency, time_duration_ms):
    """
    Generate a PWM (Pulse Width Modulation) square waveform.
    
    Parameters:
    -----------
    duty_cycle : int (0-100)
        Percentage of the cycle where signal is HIGH
    frequency : int
        Frequency of the PWM signal in Hz
    time_duration_ms : float
        Duration of the signal in milliseconds
    
    Returns:
    --------
    time_array : ndarray
        Array of time values
    signal_array : ndarray
        Array of PWM signal values (0 or 1)
    """
    # Calculate period of one cycle in seconds
    period = 1 / frequency
    
    # Convert time duration to seconds
    time_duration_sec = time_duration_ms / 1000
    
    # Generate time array with high resolution (2000 samples per millisecond for smooth visualization)
    samples_per_cycle = 2000
    time_array = np.linspace(0, time_duration_sec, int(samples_per_cycle * time_duration_sec))
    
    # Calculate high time based on duty cycle
    high_time = (duty_cycle / 100) * period
    
    # Generate PWM signal
    signal_array = np.array([
        1 if (t % period) < high_time else 0
        for t in time_array
    ])
    
    return time_array * 1000, signal_array  # Return time in milliseconds


def calculate_led_brightness(duty_cycle):
    """
    Calculate LED brightness based on duty cycle.
    
    Parameters:
    -----------
    duty_cycle : int (0-100)
        Percentage of the cycle where signal is HIGH
    
    Returns:
    --------
    brightness : float
        LED brightness as a percentage (same as duty cycle)
    """
    return duty_cycle


def calculate_motor_speed(duty_cycle):
    """
    Determine motor speed category based on duty cycle.
    
    Parameters:
    -----------
    duty_cycle : int (0-100)
        Percentage of the cycle where signal is HIGH
    
    Returns:
    --------
    speed_category : str
        Motor speed category: "OFF", "Low", "Medium", or "High"
    """
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 33:
        return "Low"
    elif duty_cycle < 67:
        return "Medium"
    else:
        return "High"


def get_motor_color(speed_category):
    """
    Get color for motor speed indicator.
    
    Parameters:
    -----------
    speed_category : str
        Motor speed category
    
    Returns:
    --------
    color : str
        Hex color code
    """
    color_map = {
        "OFF": "#808080",
        "Low": "#3498db",
        "Medium": "#f39c12",
        "High": "#e74c3c"
    }
    return color_map.get(speed_category, "#808080")


def calculate_buzzer_status(duty_cycle):
    """
    Determine buzzer sound level based on duty cycle.
    """
    if duty_cycle == 0:
        return "Silent"
    elif duty_cycle < 50:
        return "Low Sound"
    else:
        return "Loud Sound"


def calculate_heater_status(duty_cycle):
    """
    Determine heater state based on duty cycle.
    """
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 50:
        return "Warm"
    else:
        return "Hot"


def get_device_display(device, duty_cycle):
    """
    Build the display content for the selected application device.
    """
    if device == "LED":
        return {
            "title": "💡 LED Brightness",
            "value": f"{duty_cycle}%",
            "subtitle": "Brightness Level",
            "background": f"rgba(255, {int(255 * (100 - duty_cycle) / 100)}, 0, 0.3)",
            "value_color": "#f39c12",
            "text_color": "#555"
        }
    elif device == "Motor":
        motor_status = calculate_motor_speed(duty_cycle)
        return {
            "title": "⚙️ Motor Speed",
            "value": motor_status,
            "subtitle": "Motor Status",
            "background": get_motor_color(motor_status),
            "value_color": "white",
            "text_color": "white"
        }
    elif device == "Buzzer":
        buzzer_status = calculate_buzzer_status(duty_cycle)
        buzzer_color = {
            "Silent": "#808080",
            "Low Sound": "#3498db",
            "Loud Sound": "#e67e22"
        }.get(buzzer_status, "#808080")
        return {
            "title": "🔊 Buzzer Status",
            "value": buzzer_status,
            "subtitle": "Sound Level",
            "background": buzzer_color,
            "value_color": "white",
            "text_color": "white"
        }
    else:
        heater_status = calculate_heater_status(duty_cycle)
        heater_color = {
            "OFF": "#808080",
            "Warm": "#f39c12",
            "Hot": "#e74c3c"
        }.get(heater_status, "#808080")
        return {
            "title": "♨️ Heater State",
            "value": heater_status,
            "subtitle": "Temperature Level",
            "background": heater_color,
            "value_color": "white",
            "text_color": "white"
        }


def get_smart_insight(duty_cycle):
    """
    Return a dynamic insight message based on the duty cycle.
    """
    if duty_cycle < 30:
        return (
            "Energy Saving",
            "Energy-saving mode is active. Power draw stays low and efficient.",
            "#2ecc71"
        )
    elif duty_cycle <= 70:
        return (
            "Balanced",
            "Balanced operating range. Output and efficiency are staying in a healthy middle zone.",
            "#f39c12"
        )
    else:
        return (
            "High Power Warning",
            "High-power region reached. Expect stronger output, more heat, and higher energy usage.",
            "#e74c3c"
        )


# Generate PWM signal
time_array, signal_array = generate_pwm_signal(duty_cycle, frequency, time_duration)

# Calculate real-world parameters
led_brightness = calculate_led_brightness(duty_cycle)
motor_speed = calculate_motor_speed(duty_cycle)
motor_color = get_motor_color(motor_speed)
device_display = get_device_display(selected_device, duty_cycle)
insight_label, insight_text, insight_color = get_smart_insight(duty_cycle)


# ============================================================================
# OUTPUT SECTION - Visualizations and Metrics
# ============================================================================

# Create two main columns
col1, col2 = st.columns([2, 1], gap="large")

# ===== COLUMN 1: Waveform Visualization =====
with col1:
    st.subheader("📊 PWM Waveform")
    
    # Create figure with Matplotlib
    fig, ax = plt.subplots(figsize=(12, 4), dpi=100)
    
    # Plot PWM signal
    ax.plot(time_array, signal_array, linewidth=2, color="#667eea", label="PWM Signal")
    ax.fill_between(time_array, 0, signal_array, alpha=0.3, color="#667eea")
    
    # Styling
    ax.set_xlabel("Time (ms)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Signal Level", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.2, 1.3)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["LOW (0V)", "HIGH (5V)"])
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper right", fontsize=10)
    
    # Add annotations for duty cycle
    ax.text(0.5, 1.15, f"Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round", facecolor="#667eea", alpha=0.7, edgecolor="none"),
            color="white")
    
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)


# ===== COLUMN 2: Metrics and Indicators =====
with col2:
    st.subheader("📈 Real-World Effects")
    st.markdown("")

    # MODIFIED: Dynamic application simulation display based on selected device
    st.markdown(f"#### {device_display['title']}")
    device_html = f"""
    <div style="background-color: {device_display['background']}; padding: 30px; border-radius: 10px; text-align: center; color: {device_display['value_color']};">
        <div style="font-size: 36px; font-weight: bold;">{device_display['value']}</div>
        <div style="font-size: 14px; margin-top: 6px; opacity: 0.9; color: {device_display['text_color']};">{device_display['subtitle']}</div>
    </div>
    """
    st.markdown(device_html, unsafe_allow_html=True)

    # === NEW FEATURE START ===
    st.markdown("#### Animated Device Preview")

    led_intensity = max(0.18, duty_cycle / 100)
    motor_rotation_speed = max(0.9, 5.0 - (duty_cycle / 25))
    buzzer_pulse_speed = max(0.55, 1.7 - (duty_cycle / 120))
    heat_bar_height = max(22, int(28 + (duty_cycle * 0.55)))
    heat_overlay_alpha = 0.28 + (duty_cycle / 180)

    if selected_device == "LED":
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">LED Glow</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="led-orb" style="opacity:{led_intensity}; box-shadow: 0 0 {18 + duty_cycle * 2}px rgba(255, 193, 7, {0.18 + duty_cycle / 160});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Brightness follows duty cycle at {duty_cycle}%</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Motor":
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Motor Animation</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="gear-spin" style="animation-duration:{motor_rotation_speed:.2f}s;">⚙️</div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Rotation speed scales with duty cycle</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Buzzer":
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Buzzer Animation</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="sound-pulse" style="animation-duration:{buzzer_pulse_speed:.2f}s;">🔊</div>
                </div>
                <div style="display:grid; grid-template-columns: repeat(5, 1fr); gap:8px; align-items:end; margin-top:6px; min-height:48px;">
                    <span style="height:{int(14 + duty_cycle * 0.15)}px; border-radius:999px; background:#667eea; opacity:{0.35 + duty_cycle / 140};"></span>
                    <span style="height:{int(18 + duty_cycle * 0.22)}px; border-radius:999px; background:#7c8ff0; opacity:{0.42 + duty_cycle / 130};"></span>
                    <span style="height:{int(24 + duty_cycle * 0.28)}px; border-radius:999px; background:#8ca0f5; opacity:{0.5 + duty_cycle / 120};"></span>
                    <span style="height:{int(18 + duty_cycle * 0.22)}px; border-radius:999px; background:#7c8ff0; opacity:{0.42 + duty_cycle / 130};"></span>
                    <span style="height:{int(14 + duty_cycle * 0.15)}px; border-radius:999px; background:#667eea; opacity:{0.35 + duty_cycle / 140};"></span>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Sound intensity increases with duty cycle</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Heater Animation</div>
                <div class="heat-stage" style="box-shadow: 0 0 {18 + duty_cycle * 1.5}px rgba(255, 120, 0, {heat_overlay_alpha});">
                    <div class="heat-bars">
                        <span style="height:{max(20, int(heat_bar_height * 0.45))}px; animation-duration:{max(1.4, 2.4 - duty_cycle / 100):.2f}s;"></span>
                        <span style="height:{max(24, int(heat_bar_height * 0.65))}px; animation-duration:{max(1.3, 2.2 - duty_cycle / 110):.2f}s;"></span>
                        <span style="height:{max(30, int(heat_bar_height * 0.9))}px; animation-duration:{max(1.1, 2.0 - duty_cycle / 120):.2f}s;"></span>
                        <span style="height:{max(24, int(heat_bar_height * 0.65))}px; animation-duration:{max(1.3, 2.2 - duty_cycle / 110):.2f}s;"></span>
                        <span style="height:{max(20, int(heat_bar_height * 0.45))}px; animation-duration:{max(1.4, 2.4 - duty_cycle / 100):.2f}s;"></span>
                    </div>
                    <div style="text-align:center; margin-top:10px; color:#7a2d1b; font-size:13px; font-weight:600;">Heat intensity rises from yellow to red as duty cycle increases</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    # === NEW FEATURE END ===


# ============================================================================
# DETAILED METRICS SECTION
# ============================================================================
st.markdown("---")
st.subheader("📋 Detailed PWM Parameters")

# Create metrics in three columns
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        label="Duty Cycle",
        value=f"{duty_cycle}%",
        delta="HIGH" if duty_cycle > 50 else ("LOW" if duty_cycle < 50 else "MEDIUM")
    )

with metric_col2:
    period_ms = (1 / frequency) * 1000
    st.metric(
        label="Period",
        value=f"{period_ms:.3f} ms"
    )

with metric_col3:
    high_time_ms = (duty_cycle / 100) * (1 / frequency) * 1000
    st.metric(
        label="HIGH Time",
        value=f"{high_time_ms:.3f} ms"
    )

with metric_col4:
    low_time_ms = ((100 - duty_cycle) / 100) * (1 / frequency) * 1000
    st.metric(
        label="LOW Time",
        value=f"{low_time_ms:.3f} ms"
    )


# === NEW FEATURE START ===
st.markdown("---")
st.subheader("🧠 Smart Insight")

comparison_note = ""
if comparison_mode and comparison_duty_cycle is not None:
    if comparison_duty_cycle > duty_cycle:
        comparison_note = f"The comparison PWM setting is {comparison_duty_cycle - duty_cycle}% higher than the current duty cycle."
    elif comparison_duty_cycle < duty_cycle:
        comparison_note = f"The comparison PWM setting is {duty_cycle - comparison_duty_cycle}% lower than the current duty cycle."
    else:
        comparison_note = "Both PWM settings are matched, so the comparison waveform will overlap."

st.markdown(
    f"""
    <div class="insight-card" style="border-left-color: {insight_color};">
        <div class="insight-label" style="background: {insight_color};">{insight_label}</div>
        <div style="font-size: 16px; color: #2d3748; line-height: 1.65;">{insight_text}</div>
        <div style="margin-top: 10px; font-size: 13px; color: #667085;">Current duty cycle: <strong>{duty_cycle}%</strong></div>
        {f'<div style="margin-top: 6px; font-size: 13px; color: #667085;">Comparison: {comparison_note}</div>' if comparison_note else ''}
    </div>
    """,
    unsafe_allow_html=True
)
# === NEW FEATURE END ===


# ============================================================================
# INTERACTIVE INFO SECTION
# ============================================================================
st.markdown("---")

# Information panels
info_col1, info_col2 = st.columns(2)

with info_col1:
    st.info(
        """
        **What is PWM?**
        
        PWM (Pulse Width Modulation) is a technique to encode information in the duty cycle of a square wave. 
        It's commonly used to:
        - Control LED brightness
        - Adjust motor speed
        - Regulate power supply
        - Generate analog signals from digital circuits
        """
    )

with info_col2:
    st.success(
        """
        **Current Configuration:**
        
        - **Duty Cycle:** Controls the ratio of ON time to total cycle time
        - **Frequency:** Determines how many cycles occur per second
        - **Application:** Higher frequency = smoother motor operation; Higher duty cycle = more power
        """
    )


# === NEW FEATURE START ===
with st.expander("📘 Learn PWM in 60 seconds", expanded=False):
    st.markdown(
        """
        PWM, or Pulse Width Modulation, controls average power by changing how long a signal stays HIGH within each cycle.

        - Low duty cycle means short ON time and low average power.
        - Mid-range duty cycle gives a balanced output.
        - High duty cycle delivers more power, brightness, or speed, depending on the device.

        In this dashboard, the waveform stays digital, but the effect looks analog because the duty cycle changes the energy delivered over time.
        """
    )
# === NEW FEATURE END ===


# ============================================================================
# ADDITIONAL VISUALIZATION: Signal Statistics
# ============================================================================
st.markdown("---")
st.subheader("📊 Advanced View - Signal Characteristics")

# Create advanced visualization with multiple plots
fig_advanced = go.Figure()

# Calculate average voltage (normalized)
avg_voltage = duty_cycle / 100

# Add PWM signal trace
fig_advanced.add_trace(go.Scatter(
    x=time_array,
    y=signal_array,
    mode='lines',
    name='PWM Signal',
    line=dict(color='#667eea', width=2),
    fill='tozeroy',
    fillcolor='rgba(102, 126, 234, 0.3)'
))

# Add average voltage line
fig_advanced.add_hline(
    y=avg_voltage,
    line_dash="dash",
    line_color="red",
    name=f"Average Voltage ({avg_voltage:.2f}V)"
)

# Update layout
fig_advanced.update_layout(
    title=f"PWM Signal Analysis - Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
    xaxis_title="Time (ms)",
    yaxis_title="Normalized Voltage",
    hovermode='x unified',
    height=400,
    template="plotly_white"
)

st.plotly_chart(fig_advanced, use_container_width=True)


# === NEW FEATURE START ===
if comparison_mode and comparison_duty_cycle is not None:
    st.markdown("---")
    st.subheader("🔍 Comparison Mode")

    comparison_time_array, comparison_signal_array = generate_pwm_signal(comparison_duty_cycle, frequency, time_duration)
    comparison_fig = go.Figure()

    comparison_fig.add_trace(go.Scatter(
        x=time_array,
        y=signal_array,
        mode='lines',
        name=f'Primary ({duty_cycle}%)',
        line=dict(color='#667eea', width=2),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.18)'
    ))

    comparison_fig.add_trace(go.Scatter(
        x=comparison_time_array,
        y=comparison_signal_array,
        mode='lines',
        name=f'Comparison ({comparison_duty_cycle}%)',
        line=dict(color='#e67e22', width=2, dash='dash'),
        fill='tozeroy',
        fillcolor='rgba(230, 126, 34, 0.15)'
    ))

    comparison_fig.update_layout(
        title=f"PWM Comparison - {duty_cycle}% vs {comparison_duty_cycle}% Duty Cycle",
        xaxis_title="Time (ms)",
        yaxis_title="Normalized Voltage",
        hovermode='x unified',
        height=420,
        template="plotly_white"
    )

    st.plotly_chart(comparison_fig, use_container_width=True)

    comparison_col1, comparison_col2 = st.columns(2)
    with comparison_col1:
        st.metric("Primary Duty Cycle", f"{duty_cycle}%")
    with comparison_col2:
        st.metric("Comparison Duty Cycle", f"{comparison_duty_cycle}%")
# === NEW FEATURE END ===


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 12px;">
        <p>PWM Signal Simulator Dashboard | Powered by Streamlit</p>
        <p>For educational and simulation purposes</p>
    </div>
    """,
    unsafe_allow_html=True
)
