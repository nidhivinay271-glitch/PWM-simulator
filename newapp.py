"""
PWM Signal Simulator Dashboard
A web-based dashboard to simulate PWM signals and visualize their effects on LED brightness and motor speed.
"""

import matplotlib
matplotlib.use('Agg')

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go

st.cache_data.clear()

VMAX = 5.0
FREQUENCY_MIN = 1
FREQUENCY_MAX = 10000
DUTY_CYCLE_MIN = 0
DUTY_CYCLE_MAX = 100
TIME_DURATION_MIN = 1
TIME_DURATION_MAX = 10


def generate_rc_response(vin, dt, R, C):
    """RC charging/discharging response."""
    R = max(1, R)
    C = max(1e-8, C)
    tau = R * C
    alpha = dt / (tau + dt)
    vout = np.zeros_like(vin, dtype=np.float64)
    for i in range(1, len(vin)):
        vout[i] = vout[i-1] + alpha * (vin[i] - vout[i-1])
    return vout


def generate_rl_response(vin, dt, R, L):
    """RL current lag response."""
    R = max(0.1, R)
    L = max(1e-6, L)
    beta = dt / L
    i = np.zeros_like(vin, dtype=np.float64)
    vout = np.zeros_like(vin, dtype=np.float64)
    for k in range(1, len(vin)):
        i[k] = i[k-1] + beta * (vin[k] - R * i[k-1])
        vout[k] = R * i[k]
    return np.clip(vout, 0, VMAX)


def generate_diode_output(vin, Vf=0.7):
    """Diode forward conduction."""
    Vf = max(0.3, min(0.9, Vf))
    return np.where(vin > Vf, vin - Vf, 0)


def generate_zener_output(vin, Vz=5.1, Vf=0.7):
    """Zener diode voltage regulation."""
    Vz = max(2.4, min(12.0, Vz))
    Vf = max(0.3, min(0.9, Vf))
    vout = np.zeros_like(vin, dtype=np.float64)
    for i in range(len(vin)):
        if vin[i] < Vf:
            vout[i] = 0
        elif vin[i] < Vz:
            vout[i] = vin[i] - Vf
        else:
            vout[i] = Vz
    return vout


def generate_transistor_output(vin, Vcc=5.0, Vth=0.7, Vsat=0.2):
    """Transistor switching behavior."""
    Vth = max(0.5, min(1.2, Vth))
    Vsat = max(0.1, min(0.3, Vsat))
    return np.where(vin > Vth, Vcc - Vsat, 0)


def process_device_signal(device, pwm_signal, time_array, device_params=None):
    """Transform PWM waveform based on real device behavior."""
    if device_params is None:
        device_params = {}
    
    time_sec = np.maximum(time_array / 1000.0, 1e-6)
    dt = np.diff(time_sec, prepend=time_sec[0])
    dt = np.maximum(dt, 1e-6)
    
    if device == "LED":
        return pwm_signal
    elif device == "Motor":
        return generate_rl_response(pwm_signal, dt, R=10, L=1e-3)
    elif device == "Buzzer":
        return pwm_signal
    elif device == "Heater":
        return generate_rc_response(pwm_signal, dt, R=10000, C=1e-3)
    elif device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        return generate_rc_response(pwm_signal, dt, R, C)
    elif device == "Inductor":
        R = device_params.get("R", 50)
        L = device_params.get("L", 0.1)
        return generate_rl_response(pwm_signal, dt, R, L)
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return generate_zener_output(pwm_signal, Vz=Vz)
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return generate_diode_output(pwm_signal, Vf=Vf)
    elif device == "Transistor":
        Vth = device_params.get("Vth", 0.7)
        Vsat = device_params.get("Vsat", 0.2)
        return generate_transistor_output(pwm_signal, Vcc=VMAX, Vth=Vth, Vsat=Vsat)
    else:
        return pwm_signal


st.set_page_config(
    page_title="PWM Signal Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        .capacitor-orb {
            width: 74px;
            height: 74px;
            border-radius: 50%;
            margin: 0 auto;
            background: radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 1), rgba(176, 190, 255, 0.92) 32%, rgba(102, 126, 234, 0.95) 62%, rgba(63, 81, 181, 0.88) 100%);
            animation: chargePulse 2.2s ease-in-out infinite;
        }
        @keyframes chargePulse {
            0%, 100% { transform: scale(0.88); opacity: 0.6; }
            50% { transform: scale(1.12); opacity: 1; }
        }
        .inductor-coil {
            width: 74px;
            height: 74px;
            border-radius: 4px;
            margin: 0 auto;
            background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 50%, #8b5cf6 100%);
            animation: lagPulse 2.6s ease-in-out infinite;
            position: relative;
        }
        @keyframes lagPulse {
            0%, 100% { transform: scaleY(0.8) translateY(4px); opacity: 0.5; }
            50% { transform: scaleY(1.2) translateY(-4px); opacity: 1; }
        }
        .diode-arrow {
            display: inline-block;
            font-size: 54px;
            animation: diodeBlink 1.5s ease-in-out infinite;
        }
        @keyframes diodeBlink {
            0%, 100% { opacity: 0.2; transform: translateX(-2px); }
            50% { opacity: 1; transform: translateX(2px); }
        }
        .zener-cap {
            width: 74px;
            height: 74px;
            border-radius: 50%;
            margin: 0 auto;
            background: radial-gradient(circle at 35% 35%, rgba(255, 200, 100, 1), rgba(255, 165, 0, 0.92) 32%, rgba(255, 100, 0, 0.95) 62%, rgba(200, 50, 0, 0.88) 100%);
            animation: clampPulse 2.0s ease-in-out infinite;
            box-shadow: inset 0 0 15px rgba(100, 50, 0, 0.3);
        }
        @keyframes clampPulse {
            0% { transform: scale(0.8); }
            50% { transform: scale(1.0); }
            100% { transform: scale(1.0); }
        }
        .transistor-gate {
            width: 74px;
            height: 74px;
            border-radius: 8px;
            margin: 0 auto;
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            animation: switchBlink 1.0s step-start infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: white;
            font-weight: bold;
        }
        @keyframes switchBlink {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
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

st.write("🔥 NEW VERSION LOADED")

st.title("⚡ PWM Signal Simulator Dashboard")
st.markdown("### 🚀 Version: v2.2 (Deployment Fix Applied)")
st.markdown("---")
st.markdown("Adjust the duty cycle and frequency to simulate PWM signals and observe their effects on LED brightness and motor speed.")

if "preset_mode" not in st.session_state:
    st.session_state.preset_mode = "Normal"
if "duty_cycle" not in st.session_state:
    st.session_state.duty_cycle = 50
if "comparison_mode" not in st.session_state:
    st.session_state.comparison_mode = False
if "comparison_duty_cycle" not in st.session_state:
    st.session_state.comparison_duty_cycle = 70

st.sidebar.header("🎚️ PWM Controls")
st.sidebar.markdown("---")

preset_options = {
    "Eco": 25,
    "Normal": 50,
    "Performance": 85
}

def apply_preset_mode():
    st.session_state.duty_cycle = preset_options[st.session_state.preset_mode]

preset_mode = st.sidebar.selectbox(
    label="Preset Modes",
    options=list(preset_options.keys()),
    key="preset_mode",
    on_change=apply_preset_mode,
    help="Choose a quick PWM profile for the duty cycle"
)

duty_cycle = st.sidebar.slider(
    label="Duty Cycle (%)",
    min_value=DUTY_CYCLE_MIN,
    max_value=DUTY_CYCLE_MAX,
    step=1,
    key="duty_cycle",
    help="Percentage of time the signal is HIGH in one cycle"
)

frequency = st.sidebar.number_input(
    label="Frequency (Hz)",
    min_value=FREQUENCY_MIN,
    max_value=FREQUENCY_MAX,
    value=1000,
    step=100,
    help="Number of PWM cycles per second"
)

frequency = int(np.clip(frequency, FREQUENCY_MIN, FREQUENCY_MAX))

time_duration = st.sidebar.slider(
    label="Time Window (ms)",
    min_value=TIME_DURATION_MIN,
    max_value=TIME_DURATION_MAX,
    value=5,
    step=1,
    help="Duration of waveform to display"
)

comparison_mode = st.sidebar.checkbox(
    label="Enable Comparison Mode",
    value=False,
    key="comparison_mode",
    help="Compare the current PWM setting with a second duty cycle"
)

if comparison_mode:
    comparison_duty_cycle = st.sidebar.slider(
        label="Comparison Duty Cycle (%)",
        min_value=DUTY_CYCLE_MIN,
        max_value=DUTY_CYCLE_MAX,
        step=1,
        key="comparison_duty_cycle",
        help="Second PWM setting used for comparison"
    )
else:
    comparison_duty_cycle = None

selected_device = st.sidebar.selectbox(
    label="Device",
    options=["LED", "Motor", "Buzzer", "Heater", "Capacitor", "Inductor", "Zener Diode", "Diode", "Transistor"],
    index=0,
    help="Choose the device to preview in the simulation panel"
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Device Parameters")

device_params = {}

if selected_device == "Capacitor":
    device_params["R"] = st.sidebar.slider(
        "Resistance (Ω)",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100
    )
    device_params["C"] = st.sidebar.slider(
        "Capacitance (F)",
        min_value=1e-6,
        max_value=1e-3,
        value=1e-4,
        format="%.6f"
    )
elif selected_device == "Inductor":
    device_params["R"] = st.sidebar.slider(
        "Resistance (Ω)",
        min_value=10,
        max_value=100,
        value=50,
        step=5
    )
    device_params["L"] = st.sidebar.slider(
        "Inductance (H)",
        min_value=1e-3,
        max_value=10.0,
        value=0.1,
        format="%.4f"
    )
elif selected_device == "Diode":
    device_params["Vf"] = st.sidebar.slider(
        "Forward Voltage (V)",
        min_value=0.3,
        max_value=0.9,
        value=0.7,
        step=0.05
    )
elif selected_device == "Zener Diode":
    device_params["Vz"] = st.sidebar.slider(
        "Zener Voltage (V)",
        min_value=2.4,
        max_value=12.0,
        value=5.1,
        step=0.3
    )
elif selected_device == "Transistor":
    device_params["Vth"] = st.sidebar.slider(
        "Threshold Voltage (V)",
        min_value=0.5,
        max_value=1.2,
        value=0.7,
        step=0.05
    )
    device_params["Vsat"] = st.sidebar.slider(
        "Saturation Voltage (V)",
        min_value=0.1,
        max_value=0.3,
        value=0.2,
        step=0.05
    )

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tips:**\n"
    "- Higher duty cycle increases LED brightness\n"
    "- Higher frequency increases motor smoothness\n"
    "- 0% duty cycle turns OFF, 100% turns ON"
)


def generate_pwm_signal(duty_cycle, frequency, time_duration_ms):
    """Generate a PWM square waveform scaled to 0-5V."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    frequency = max(FREQUENCY_MIN, min(int(frequency), FREQUENCY_MAX))
    time_duration_ms = max(TIME_DURATION_MIN, time_duration_ms)
    
    if frequency <= 0:
        frequency = 1000
    
    period = 1.0 / frequency
    time_duration_sec = time_duration_ms / 1000.0
    
    samples_per_cycle = min(200, max(50, int(2000 / frequency)))
    num_cycles = frequency * time_duration_sec
    total_samples = max(1, int(samples_per_cycle * num_cycles))
    
    time_array = np.linspace(0, time_duration_sec, total_samples)
    high_time = (duty_cycle / 100.0) * period
    
    phase = np.mod(time_array, period)
    signal_normalized = (phase < high_time).astype(np.float64)
    signal_array = signal_normalized * VMAX
    
    return time_array * 1000.0, signal_array


def calculate_led_brightness(duty_cycle):
    """Calculate LED brightness percentage."""
    return int(np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))


def calculate_motor_speed(duty_cycle):
    """Determine motor speed category."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 33:
        return "Low"
    elif duty_cycle < 67:
        return "Medium"
    else:
        return "High"


def get_motor_color(speed_category):
    """Get color for motor speed indicator."""
    color_map = {
        "OFF": "#808080",
        "Low": "#3498db",
        "Medium": "#f39c12",
        "High": "#e74c3c"
    }
    return color_map.get(speed_category, "#808080")


def calculate_buzzer_status(duty_cycle):
    """Determine buzzer sound level."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "Silent"
    elif duty_cycle < 50:
        return "Low Sound"
    else:
        return "Loud Sound"


def calculate_heater_status(duty_cycle):
    """Determine heater temperature state."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 50:
        return "Warm"
    else:
        return "Hot"


def get_device_display(device, duty_cycle, device_params=None):
    """Build the display content for the selected application device."""
    if device_params is None:
        device_params = {}
    
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    
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
    elif device == "Heater":
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
    elif device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        tau = R * C
        return {
            "title": "⚡ Capacitor (RC)",
            "value": f"τ={tau:.4f}s",
            "subtitle": "Time Constant",
            "background": "rgba(102, 126, 234, 0.2)",
            "value_color": "#667eea",
            "text_color": "#555"
        }
    elif device == "Inductor":
        L = device_params.get("L", 0.1)
        return {
            "title": "🔌 Inductor",
            "value": f"L={L:.3f}H",
            "subtitle": "Current Lag",
            "background": "rgba(139, 92, 246, 0.2)",
            "value_color": "#8b5cf6",
            "text_color": "#555"
        }
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return {
            "title": "📍 Diode",
            "value": f"Vf={Vf:.2f}V",
            "subtitle": "Forward Voltage",
            "background": "rgba(34, 197, 94, 0.2)",
            "value_color": "#22c55e",
            "text_color": "#555"
        }
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return {
            "title": "🔒 Zener Diode",
            "value": f"Vz={Vz:.2f}V",
            "subtitle": "Regulated Voltage",
            "background": "rgba(249, 115, 22, 0.2)",
            "value_color": "#f97316",
            "text_color": "#555"
        }
    else:
        Vth = device_params.get("Vth", 0.7)
        return {
            "title": "⚙️ Transistor",
            "value": f"Vth={Vth:.2f}V",
            "subtitle": "Threshold",
            "background": "rgba(34, 197, 94, 0.2)",
            "value_color": "#22c55e",
            "text_color": "#555"
        }


def get_smart_insight(device, duty_cycle, device_params=None):
    """Return a dynamic insight message based on the device and parameters."""
    if device_params is None:
        device_params = {}
    
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    
    if device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        tau = R * C
        return (
            "RC Smoothing",
            f"PWM is being smoothed into DC using RC time constant τ = {tau:.6f}s. Increase tau to reduce ripple and harmonics.",
            "#667eea"
        )
    elif device == "Inductor":
        return (
            "RL Filtering",
            "Current ripple is reduced due to inductive smoothing. Higher L = slower response, smoother current draw.",
            "#8b5cf6"
        )
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return (
            "Rectification",
            f"One-way conduction with forward drop Vf = {Vf:.2f}V. Only half-wave passes through.",
            "#22c55e"
        )
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return (
            "Voltage Clamping",
            f"Voltage is clamped to safe breakdown level Vz = {Vz:.2f}V. Ideal for overvoltage protection.",
            "#f97316"
        )
    elif device == "Transistor":
        Vth = device_params.get("Vth", 0.7)
        return (
            "Digital Switching",
            f"Operating as a digital switch with threshold Vth = {Vth:.2f}V. Sharp ON/OFF behavior.",
            "#22c55e"
        )
    elif device == "Motor":
        return (
            "Current Smoothing",
            "Mechanical inertia and back-EMF smooth motor response. Higher frequency = smoother rotation.",
            "#ff6b6b"
        )
    elif device == "Heater":
        return (
            "Thermal Response",
            "Heat dissipation smooths thermal response. Long time constant filters rapid PWM changes.",
            "#ffa500"
        )
    else:
        if duty_cycle < 30:
            return ("Energy Saving", "Energy-saving mode is active. Power draw stays low and efficient.", "#2ecc71")
        elif duty_cycle <= 70:
            return ("Balanced", "Balanced operating range. Output and efficiency are in a healthy middle zone.", "#f39c12")
        else:
            return ("High Power Warning", "High-power region reached. Expect stronger output, more heat, and higher energy usage.", "#e74c3c")


time_array, signal_array = generate_pwm_signal(duty_cycle, frequency, time_duration)
device_output = process_device_signal(selected_device, signal_array, time_array, device_params)
led_brightness = calculate_led_brightness(duty_cycle)
motor_speed = calculate_motor_speed(duty_cycle)
motor_color = get_motor_color(motor_speed)
device_display = get_device_display(selected_device, duty_cycle, device_params)
insight_label, insight_text, insight_color = get_smart_insight(selected_device, duty_cycle, device_params)
motor_animation_speed = max(0.5, 3.0 - duty_cycle / 50.0)


col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.subheader("📊 PWM Waveform")
    
    fig, ax = plt.subplots(figsize=(12, 4), dpi=100)
    
    ax.step(time_array, signal_array, linewidth=2, color="#667eea", label="VIN (PWM Signal)", where='post')
    ax.fill_between(time_array, 0, signal_array, alpha=0.3, color="#667eea", step='post')
    
    if device_output is not None and not np.array_equal(device_output, signal_array):
        if selected_device in ["Capacitor", "Inductor", "Motor", "Heater"]:
            ax.plot(time_array, device_output, linewidth=2, color="#e74c3c", label="VOUT (Device Output)", linestyle='-')
            ax.fill_between(time_array, 0, device_output, alpha=0.15, color="#e74c3c')
        else:
            ax.step(time_array, device_output, linewidth=2, color="#e74c3c", label="VOUT (Device Output)", where='post')
            ax.fill_between(time_array, 0, device_output, alpha=0.15, color="#e74c3c', step='post')
    
    ax.set_xlabel("Time (ms)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Voltage (V)", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.5, 5.5)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_yticklabels(["0V", "1V", "2V", "3V", "4V", "5V"])
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper right", fontsize=10)
    
    ax.text(0.5, 1.15, f"Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round", facecolor="#667eea", alpha=0.7, edgecolor="none"),
            color="white")
    
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)


with col2:
    st.subheader("📈 Real-World Effects")
    st.markdown("")
    
    st.markdown(f"#### {device_display['title']}")
    device_html = f"""
    <div style="background-color: {device_display['background']}; padding: 30px; border-radius: 10px; text-align: center; color: {device_display['value_color']};">
        <div style="font-size: 36px; font-weight: bold;">{device_display['value']}</div>
        <div style="font-size: 14px; margin-top: 6px; opacity: 0.9; color: {device_display['text_color']};">{device_display['subtitle']}</div>
    </div>
    """
    st.markdown(device_html, unsafe_allow_html=True)
    
    st.markdown("#### Animated Device Preview")
    
    led_intensity = max(0.18, duty_cycle / 100.0)
    buzzer_pulse_speed = max(0.55, 1.7 - (duty_cycle / 120.0))
    heat_bar_height = max(22, int(28 + (duty_cycle * 0.55)))
    heat_overlay_alpha = 0.28 + (duty_cycle / 180.0)
    
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
                    <div class="gear-spin" style="animation-duration:{motor_animation_speed:.2f}s;">⚙️</div>
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
    elif selected_device == "Heater":
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
    elif selected_device == "Capacitor":
        charge_intensity = max(0.2, duty_cycle / 100.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Capacitor Charging</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="capacitor-orb" style="opacity:{charge_intensity}; box-shadow: 0 0 {15 + duty_cycle * 1.5}px rgba(102, 126, 234, {0.2 + duty_cycle / 140});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Energy storage smooths voltage response</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Inductor":
        lag_intensity = max(0.3, (duty_cycle + 30) / 130.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Inductor Current Lag</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="inductor-coil" style="opacity:{lag_intensity}; box-shadow: 0 0 {12 + duty_cycle}px rgba(139, 92, 246, {0.25 + duty_cycle / 150});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Current lags voltage response</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Diode":
        diode_glow = max(0.2, duty_cycle / 100.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Diode Conduction</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="diode-arrow" style="opacity:{diode_glow}; text-shadow: 0 0 {10 + duty_cycle}px rgba(34, 197, 94, 0.8);">→</div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">One-way conduction during ON phase</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Zener Diode":
        clamp_intensity = max(0.2, min(1.0, (duty_cycle + 20) / 100.0))
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Zener Voltage Clamp</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="zener-cap" style="opacity:{clamp_intensity}; box-shadow: 0 0 {10 + duty_cycle * 0.8}px rgba(249, 115, 22, {0.3 + duty_cycle / 170});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Regulates voltage to breakdown level</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        switch_speed = max(0.8, 1.2 - duty_cycle / 150.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Transistor Switch</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="transistor-gate" style="animation-duration:{switch_speed:.2f}s;">ON</div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Sharp digital switching behavior</div>
            </div>
            """,
            unsafe_allow_html=True
        )


st.markdown("---")
st.subheader("📋 Detailed PWM Parameters")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        label="Duty Cycle",
        value=f"{duty_cycle}%",
        delta="HIGH" if duty_cycle > 50 else ("LOW" if duty_cycle < 50 else "MEDIUM")
    )

with metric_col2:
    period_ms = (1.0 / frequency) * 1000
    st.metric(label="Period", value=f"{period_ms:.3f} ms")

with metric_col3:
    high_time_ms = (duty_cycle / 100.0) * (1.0 / frequency) * 1000
    st.metric(label="HIGH Time", value=f"{high_time_ms:.3f} ms")

with metric_col4:
    low_time_ms = ((100 - duty_cycle) / 100.0) * (1.0 / frequency) * 1000
    st.metric(label="LOW Time", value=f"{low_time_ms:.3f} ms")


st.markdown("---")
st.subheader("🧠 Smart Insight")

comparison_note = ""
if comparison_mode and comparison_duty_cycle is not None:
    comparison_duty_cycle = int(np.clip(comparison_duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))
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


st.markdown("---")
st.subheader("💡 Smart Recommendation System")

if selected_device == "Capacitor":
    st.info(
        """💡 **RC Filter Optimization**
        
- Increase R or C to reduce ripple
- Trade-off: Higher RC = slower response
- Typical: τ = 1-100ms for audio filtering
- Choose values based on cutoff frequency: f_c = 1/(2πRC)
        """
    )
elif selected_device == "Inductor":
    st.info(
        """💡 **RL Filter Optimization**
        
- Increase L to smooth current transients
- Higher frequency = less ripple needed
- Typical: L = 1-100mH for power supplies
- Watch for ringing at high switching rates
        """
    )
elif selected_device == "Zener Diode":
    st.info(
        """💡 **Voltage Regulation Tips**
        
- Ensure Zener rating is less than supply voltage
- Add series resistor to limit current
- Typical Zener: 3.3V, 5V, 12V
- Use in parallel with load for regulation
        """
    )
elif selected_device == "Transistor":
    st.info(
        """💡 **Switch Optimization**
        
- Ensure base/gate threshold voltage is met
- Use PWM frequency > 20kHz to avoid audible noise
- Provide adequate base current for saturation
- Add protection diodes for inductive loads
        """
    )
elif selected_device == "Motor":
    st.info(
        """💡 **Motor Control Tips**
        
- Use higher frequency for smoother rotation (>2kHz)
- Lower frequency = cogging/jerking
- Add flywheel diode to protect circuit
- Monitor current for stall conditions
        """
    )
elif selected_device == "Heater":
    st.info(
        """💡 **Thermal Management**
        
- Use low frequency for thermal smoothing
- Monitor temperature limits
- Add thermal cutoff protection
- Consider duty cycle ramps for safety
        """
    )
else:
    if duty_cycle < 30:
        st.info(
            """🟢 **Energy Saving Mode**
            
Your PWM is set to a low duty cycle. This is ideal for:
- Battery-powered applications
- Reducing heat generation
- Extending device lifespan
- Energy-efficient operation
            """
        )
    elif 30 <= duty_cycle <= 70:
        st.info(
            """🟡 **Balanced Performance**
            
Your PWM is in the optimal range for:
- Smooth operation
- Reliable control
- Balanced power consumption
- Safe long-term operation
            """
        )
    else:
        st.warning(
            """🔴 **High Power Mode**
            
Your PWM is set to high power. Be aware:
- Increased power consumption
- Heat generation may increase
- Ensure adequate cooling/ventilation
- Consider reducing duty cycle for sustained use
            """
        )


st.markdown("---")

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


st.markdown("---")
st.subheader("📊 Advanced View - Signal Characteristics")

avg_voltage = (duty_cycle / 100.0) * VMAX

fig_advanced = go.Figure()

fig_advanced.add_trace(go.Scatter(
    x=time_array,
    y=signal_array,
    mode='lines',
    name='PWM Signal (VIN)',
    line=dict(color='#667eea', width=2, shape='hv'),
    fill='tozeroy',
    fillcolor='rgba(102, 126, 234, 0.3)'
))

if device_output is not None and not np.array_equal(device_output, signal_array):
    if selected_device in ["Capacitor", "Inductor", "Motor", "Heater"]:
        fig_advanced.add_trace(go.Scatter(
            x=time_array,
            y=device_output,
            mode='lines',
            name='Device Output (VOUT)',
            line=dict(color='#e74c3c', width=2, shape='linear'),
            fill='tozeroy',
            fillcolor='rgba(230, 116, 60, 0.15)'
        ))
    else:
        fig_advanced.add_trace(go.Scatter(
            x=time_array,
            y=device_output,
            mode='lines',
            name='Device Output (VOUT)',
            line=dict(color='#e74c3c', width=2, shape='hv'),
            fill='tozeroy',
            fillcolor='rgba(230, 116, 60, 0.15)'
        ))

fig_advanced.add_hline(
    y=avg_voltage,
    line_dash="dash",
    line_color="red",
    name=f"Average Voltage ({avg_voltage:.2f}V)"
)

fig_advanced.update_layout(
    title=f"PWM Signal Analysis - Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
    xaxis_title="Time (ms)",
    yaxis_title="Voltage (V)",
    hovermode='x unified',
    height=400,
    template="plotly_dark"
)

st.plotly_chart(fig_advanced, use_container_width=True)


if comparison_mode and comparison_duty_cycle is not None:
    comparison_duty_cycle = int(np.clip(comparison_duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))
    
    st.markdown("---")
    st.subheader("🔍 Comparison Mode")
    
    comparison_time_array, comparison_signal_array = generate_pwm_signal(comparison_duty_cycle, frequency, time_duration)
    comparison_fig = go.Figure()
    
    comparison_fig.add_trace(go.Scatter(
        x=time_array,
        y=signal_array,
        mode='lines',
        name=f'Primary ({duty_cycle}%)',
        line=dict(color='#667eea', width=2, shape='hv'),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.18)'
    ))
    
    comparison_fig.add_trace(go.Scatter(
        x=comparison_time_array,
        y=comparison_signal_array,
        mode='lines',
        name=f'Comparison ({comparison_duty_cycle}%)',
        line=dict(color='#e67e22', width=2, dash='dash', shape='hv'),
        fill='tozeroy',
        fillcolor='rgba(230, 126, 34, 0.15)'
    ))
    
    comparison_fig.update_layout(
        title=f"PWM Comparison - {duty_cycle}% vs {comparison_duty_cycle}% Duty Cycle",
        xaxis_title="Time (ms)",
        yaxis_title="Voltage (V)",
        yaxis=dict(range=[-0.5, 5.5]),
        hovermode='x unified',
        height=420,
        template="plotly_dark"
    )
    
    st.plotly_chart(comparison_fig, use_container_width=True)
    
    comparison_col1, comparison_col2 = st.columns(2)
    with comparison_col1:
        st.metric("Primary Duty Cycle", f"{duty_cycle}%")
    with comparison_col2:
        st.metric("Comparison Duty Cycle", f"{comparison_duty_cycle}%")


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


st.markdown("---")
st.subheader("🤖 AI Chat Assistant")

user_question = st.text_input(
    "💬 Ask me about PWM:",
    placeholder="e.g., 'What is PWM?', 'How does LED work?', 'Tell me about motor'"
)

if user_question:
    question_lower = user_question.lower()
    response = None
    
    if any(word in question_lower for word in ["what is pwm", "what does pwm mean"]):
        response = (
            "**PWM (Pulse Width Modulation)** is a technique that controls average power by varying how long a signal "
            "stays ON vs OFF in each cycle. Instead of changing voltage, PWM switches the signal rapidly HIGH and LOW. "
            "The ratio of ON-time to total cycle-time is called the **duty cycle**. Higher duty cycle = more power. "
            "This is used in your dashboard to control LED brightness, motor speed, buzzer intensity, heater heat, and more advanced components like RC circuits, inductors, and semiconductor devices."
        )
    
    elif any(word in question_lower for word in ["what is duty", "duty cycle", "duty"]):
        response = (
            "**Duty cycle** is the percentage of time the PWM signal is HIGH (ON) within one complete cycle. "
            "For example:\n"
            "- **0% duty cycle** = Signal always OFF (no power)\n"
            "- **50% duty cycle** = Signal ON half the time, OFF half the time\n"
            "- **100% duty cycle** = Signal always ON (full power)\n"
            "Duty cycle directly controls the **average power** delivered to your device. Use the duty cycle slider "
            "on the left to see how it affects LED brightness, motor speed, and other outputs!"
        )
    
    elif any(word in question_lower for word in ["frequency", "what is frequency", "hz"]):
        response = (
            "**Frequency** is how many complete PWM cycles happen per second, measured in **Hertz (Hz)**. "
            "For example, 1000 Hz = 1000 cycles per second.\n\n"
            "**Why frequency matters:**\n"
            "- **Higher frequency** = Smoother operation, less audible noise (better for motors & buzzers)\n"
            "- **Lower frequency** = Can cause flickering in LEDs or audible buzz\n"
            "Adjust the frequency slider to see how it affects the waveform smoothness and device response!"
        )
    
    elif "pwm" in question_lower and any(word in question_lower for word in ["why", "use", "advantage", "benefit"]):
        response = (
            "**Why PWM is so useful:**\n"
            "✓ **Energy efficient** - No wasted power as heat (unlike resistors)\n"
            "✓ **Simple control** - Easy to control with digital signals\n"
            "✓ **Smooth output** - Simulates analog behavior from digital circuits\n"
            "✓ **Versatile** - Works for LEDs, motors, heaters, buzzers, and power supplies\n"
            "✓ **Cost-effective** - Requires minimal hardware\n"
            "PWM is the industry standard for power control in embedded systems!"
        )
    
    elif any(word in question_lower for word in ["led", "light", "brightness"]):
        response = (
            "**LED Control with PWM:**\n"
            "The LED's brightness is controlled by the duty cycle:\n"
            "- **0%** = LED OFF (no brightness)\n"
            "- **50%** = LED at half brightness\n"
            "- **100%** = LED at full brightness\n\n"
            "Your eyes perceive the rapidly flickering light (at high frequency) as continuous brightness. "
            "The higher the duty cycle, the brighter the LED appears! Try adjusting the duty cycle slider "
            "and selecting 'LED' from the device dropdown to see the effect."
        )
    
    elif any(word in question_lower for word in ["motor", "speed", "rotation"]):
        response = (
            "**Motor Speed Control with PWM:**\n"
            "Motor speed is controlled by the duty cycle:\n"
            "- **0%** = Motor OFF\n"
            "- **Low duty cycle (1-33%)** = Slow rotation\n"
            "- **Medium duty cycle (34-66%)** = Medium speed\n"
            "- **High duty cycle (67-100%)** = Maximum speed\n\n"
            "Higher duty cycle delivers more average power to the motor, making it rotate faster. "
            "Select 'Motor' from the device dropdown to see the animated gear speed change with duty cycle!"
        )
    
    elif any(word in question_lower for word in ["buzzer", "sound", "beep", "noise"]):
        response = (
            "**Buzzer Sound Control with PWM:**\n"
            "PWM controls the buzzer's sound intensity:\n"
            "- **0%** = Silent (no sound)\n"
            "- **Low duty cycle (1-49%)** = Low sound level\n"
            "- **High duty cycle (50-100%)** = Loud sound\n\n"
            "The frequency slider also affects the buzzer tone. Higher frequencies produce higher-pitched sounds. "
            "Select 'Buzzer' from the device dropdown to visualize the sound level with animated waveforms!"
        )
    
    elif any(word in question_lower for word in ["heater", "heat", "temperature", "warm", "hot"]):
        response = (
            "**Heater Temperature Control with PWM:**\n"
            "PWM controls heating intensity:\n"
            "- **0%** = Heater OFF\n"
            "- **Low duty cycle (1-49%)** = Warm (low heat)\n"
            "- **High duty cycle (50-100%)** = Hot (high heat)\n\n"
            "Higher duty cycle means the heater is ON longer, generating more heat. "
            "Select 'Heater' from the device dropdown to see the animated heat bars showing temperature rise!"
        )
    
    elif any(word in question_lower for word in ["capacitor", "rc"]):
        response = (
            "**Capacitor (RC Circuit) with PWM:**\n\n"
            "**Principle:** A capacitor stores charge and resists voltage changes. Combined with resistance, it creates an RC filter.\n\n"
            "**Waveform Effect:** The square PWM wave is smoothed into a curved exponential rise/fall. Output approaches input with time constant τ = R×C:\n"
            "- Higher τ = More smoothing, slower response\n"
            "- Lower τ = Less smoothing, faster response\n\n"
            "**Real-World Uses:** Audio filtering, power supply ripple reduction, gate delay circuits, sensor debouncing."
        )
    
    elif any(word in question_lower for word in ["inductor", "rl", "coil"]):
        response = (
            "**Inductor (RL Circuit) with PWM:**\n\n"
            "**Principle:** An inductor resists current changes via back-EMF (Faraday's law). RL circuits create current lag.\n\n"
            "**Waveform Effect:** Current lags voltage. Output rises/falls slower than input due to inductance L. Higher L = slower response.\n\n"
            "**Real-World Uses:** Motor control, power supply inductors, current smoothing in LED drivers, energy storage in switch-mode supplies."
        )
    
    elif any(word in question_lower for word in ["diode", "rectif"]):
        response = (
            "**Diode with PWM:**\n\n"
            "**Principle:** A diode conducts only in one direction. Forward bias enables conduction; reverse bias blocks it. Forward voltage drop Vf ≈ 0.7V (silicon).\n\n"
            "**Waveform Effect:** Output is half-wave rectified. PWM positive half-cycles pass through (minus Vf). Negative cycles are blocked → output = 0V.\n\n"
            "**Real-World Uses:** Rectification (AC→DC), reverse polarity protection, charge pump circuits, solar panel bypass."
        )
    
    elif any(word in question_lower for word in ["zener", "regulation", "clamp", "regul"]):
        response = (
            "**Zener Diode with PWM:**\n\n"
            "**Principle:** Zener diodes conduct in reverse bias at a precise breakdown voltage Vz. Used for voltage regulation and overvoltage protection.\n\n"
            "**Waveform Effect:** Output voltage is clamped to Vz. Below Vz, behaves like normal diode. Above Vz, current increases but voltage stays constant → flat-top output.\n\n"
            "**Real-World Uses:** Voltage regulation, overvoltage protection, reference circuits, transient suppression."
        )
    
    elif any(word in question_lower for word in ["transistor", "switch", "gate", "thresh", "bjt"]):
        response = (
            "**Transistor as Switch with PWM:**\n\n"
            "**Principle:** Transistors operate as digital switches. Base/gate voltage controls collector/drain current. Threshold voltage Vth determines ON/OFF.\n\n"
            "**Waveform Effect:** Output is rectangular binary: fully ON (near Vcc) or fully OFF (0V). Sharp switching with no linear region when driven hard.\n\n"
            "**Real-World Uses:** Motor control, relay drivers, LED brightness control, power switching in audio amplifiers and DC-DC converters."
        )
    
    elif any(word in question_lower for word in ["what does this", "how does this work"]):
        response = (
            "**Welcome to the PWM Signal Simulator Dashboard!** 📊\n\n"
            "This interactive tool lets you:\n"
            "✓ Adjust duty cycle and frequency with sliders\n"
            "✓ See the PWM waveform change in real-time\n"
            "✓ Observe effects on LED, Motor, Buzzer, Heater, and advanced electronics\n"
            "✓ Simulate RC circuits, inductors, diodes, Zener diodes, and transistors\n"
            "✓ Compare two different PWM settings side-by-side\n"
            "✓ Use preset modes (Eco, Normal, Performance) for quick setup\n"
            "✓ Get smart recommendations based on your settings\n\n"
            "Start by adjusting the duty cycle slider and selecting different devices to see PWM in action!"
        )
    
    elif any(word in question_lower for word in ["graph", "waveform", "understand the", "plot"]):
        response = (
            "**Understanding the PWM Waveform Graph:**\n\n"
            "The graph shows the PWM signal and device response over time:\n"
            "- **Blue line (VIN)** = Input PWM signal (0-5V square wave)\n"
            "- **Red line (VOUT)** = Device output (varies by device type)\n"
            "- **Shaded area** = Time the signal is ON\n"
            "- **Duty cycle %** = How much of the cycle is shaded (ON time)\n\n"
            "The **red dashed line** shows the average voltage, which equals (duty cycle / 100) × 5V. "
            "For example, at 50% duty cycle, average voltage = 2.5V. This average is what controls your device!"
        )
    
    elif any(word in question_lower for word in ["what happens", "change", "effect", "when you"]):
        response = (
            "**When You Change the Duty Cycle:**\n\n"
            "The waveform updates instantly! You'll see:\n"
            "- **Wider shaded area** = Higher duty cycle (more ON time)\n"
            "- **Higher red line** = Higher average voltage\n"
            "- **Larger device effect** = More power, more brightness/speed/heat\n\n"
            "Different devices respond differently:\n"
            "- **LED**: Brightness increases proportionally\n"
            "- **Motor**: Speed increases with higher duty cycle\n"
            "- **Capacitor/Inductor**: Output smoothness changes based on circuit properties\n"
            "- **Diode/Zener**: Output is clipped or regulated\n"
            "- **Transistor**: Digital ON/OFF switching\n\n"
            "This demonstrates how PWM gives you precise analog-like control from a digital signal!"
        )
    
    elif any(word in question_lower for word in ["comparison", "preset", "eco", "normal", "performance"]):
        response = ("""
PWM Signal Simulator Dashboard - FIXED VERSION
A web-based dashboard to simulate PWM signals and visualize their effects on LED brightness and motor speed.

=== FIXES APPLIED ===
1. Set matplotlib backend to 'Agg' BEFORE importing pyplot (prevents rendering issues)
2. Fixed matplotlib fill_between color string (line had mismatched quotes: "#e74c3c')
3. Extended device selection to include all 9 devices (Capacitor, Inductor, Diode, Zener Diode, Transistor)
4. Fixed dt calculation in process_device_signal (now properly vectorized)
5. Added safeguards in RC/RL response functions (min/max for R, C, L)
6. Fixed generate_rl_response to clip output to VMAX range
7. Removed @st.cache_data from generate_pwm_signal to prevent stale UI state
8. Added comprehensive input validation and bounds checking
9. Fixed edge cases (division by zero, empty arrays, extreme frequencies)
10. Improved numerical stability in all physics models
11. Added defensive checks for device parameters
12. Fixed HTML/CSS string handling consistency
"""

import matplotlib
matplotlib.use('Agg')

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go


VMAX = 5.0
FREQUENCY_MIN = 1
FREQUENCY_MAX = 10000
DUTY_CYCLE_MIN = 0
DUTY_CYCLE_MAX = 100
TIME_DURATION_MIN = 1
TIME_DURATION_MAX = 10


def generate_rc_response(vin, dt, R, C):
    """RC charging/discharging response."""
    R = max(1.0, float(R))
    C = max(1e-8, float(C))
    tau = R * C
    if tau <= 0:
        tau = 1.0
    alpha = dt / (tau + dt)
    alpha = np.clip(alpha, 0, 1)
    vout = np.zeros_like(vin, dtype=np.float64)
    for i in range(1, len(vin)):
        vout[i] = vout[i-1] + alpha * (vin[i] - vout[i-1])
    return np.clip(vout, 0, VMAX)


def generate_rl_response(vin, dt, R, L):
    """RL current lag response."""
    R = max(0.1, float(R))
    L = max(1e-6, float(L))
    beta = dt / L
    beta = np.clip(beta, 0, 1)
    i = np.zeros_like(vin, dtype=np.float64)
    vout = np.zeros_like(vin, dtype=np.float64)
    for k in range(1, len(vin)):
        i[k] = i[k-1] + beta * (vin[k] - R * i[k-1])
        vout[k] = R * i[k]
    return np.clip(vout, 0, VMAX)


def generate_diode_output(vin, Vf=0.7):
    """Diode forward conduction."""
    Vf = max(0.3, min(0.9, float(Vf)))
    return np.where(vin > Vf, vin - Vf, 0.0)


def generate_zener_output(vin, Vz=5.1, Vf=0.7):
    """Zener diode voltage regulation."""
    Vz = max(2.4, min(12.0, float(Vz)))
    Vf = max(0.3, min(0.9, float(Vf)))
    vout = np.zeros_like(vin, dtype=np.float64)
    for i in range(len(vin)):
        if vin[i] < Vf:
            vout[i] = 0.0
        elif vin[i] < Vz:
            vout[i] = vin[i] - Vf
        else:
            vout[i] = Vz
    return vout


def generate_transistor_output(vin, Vcc=5.0, Vth=0.7, Vsat=0.2):
    """Transistor switching behavior."""
    Vth = max(0.5, min(1.2, float(Vth)))
    Vsat = max(0.1, min(0.3, float(Vsat)))
    Vcc = max(0.1, float(Vcc))
    return np.where(vin > Vth, Vcc - Vsat, 0.0)


def process_device_signal(device, pwm_signal, time_array, device_params=None):
    """Transform PWM waveform based on real device behavior."""
    if device_params is None:
        device_params = {}
    
    time_sec = np.maximum(time_array / 1000.0, 1e-6)
    dt = np.diff(time_sec, prepend=time_sec[0])
    dt = np.maximum(dt, 1e-6)
    
    if device == "LED":
        return pwm_signal
    elif device == "Motor":
        return generate_rl_response(pwm_signal, dt, R=10, L=1e-3)
    elif device == "Buzzer":
        return pwm_signal
    elif device == "Heater":
        return generate_rc_response(pwm_signal, dt, R=10000, C=1e-3)
    elif device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        return generate_rc_response(pwm_signal, dt, R, C)
    elif device == "Inductor":
        R = device_params.get("R", 50)
        L = device_params.get("L", 0.1)
        return generate_rl_response(pwm_signal, dt, R, L)
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return generate_zener_output(pwm_signal, Vz=Vz)
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return generate_diode_output(pwm_signal, Vf=Vf)
    elif device == "Transistor":
        Vth = device_params.get("Vth", 0.7)
        Vsat = device_params.get("Vsat", 0.2)
        return generate_transistor_output(pwm_signal, Vcc=VMAX, Vth=Vth, Vsat=Vsat)
    else:
        return pwm_signal


st.set_page_config(
    page_title="PWM Signal Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        .capacitor-orb {
            width: 74px;
            height: 74px;
            border-radius: 50%;
            margin: 0 auto;
            background: radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 1), rgba(176, 190, 255, 0.92) 32%, rgba(102, 126, 234, 0.95) 62%, rgba(63, 81, 181, 0.88) 100%);
            animation: chargePulse 2.2s ease-in-out infinite;
        }
        @keyframes chargePulse {
            0%, 100% { transform: scale(0.88); opacity: 0.6; }
            50% { transform: scale(1.12); opacity: 1; }
        }
        .inductor-coil {
            width: 74px;
            height: 74px;
            border-radius: 4px;
            margin: 0 auto;
            background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 50%, #8b5cf6 100%);
            animation: lagPulse 2.6s ease-in-out infinite;
            position: relative;
        }
        @keyframes lagPulse {
            0%, 100% { transform: scaleY(0.8) translateY(4px); opacity: 0.5; }
            50% { transform: scaleY(1.2) translateY(-4px); opacity: 1; }
        }
        .diode-arrow {
            display: inline-block;
            font-size: 54px;
            animation: diodeBlink 1.5s ease-in-out infinite;
        }
        @keyframes diodeBlink {
            0%, 100% { opacity: 0.2; transform: translateX(-2px); }
            50% { opacity: 1; transform: translateX(2px); }
        }
        .zener-cap {
            width: 74px;
            height: 74px;
            border-radius: 50%;
            margin: 0 auto;
            background: radial-gradient(circle at 35% 35%, rgba(255, 200, 100, 1), rgba(255, 165, 0, 0.92) 32%, rgba(255, 100, 0, 0.95) 62%, rgba(200, 50, 0, 0.88) 100%);
            animation: clampPulse 2.0s ease-in-out infinite;
            box-shadow: inset 0 0 15px rgba(100, 50, 0, 0.3);
        }
        @keyframes clampPulse {
            0% { transform: scale(0.8); }
            50% { transform: scale(1.0); }
            100% { transform: scale(1.0); }
        }
        .transistor-gate {
            width: 74px;
            height: 74px;
            border-radius: 8px;
            margin: 0 auto;
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
            animation: switchBlink 1.0s step-start infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: white;
            font-weight: bold;
        }
        @keyframes switchBlink {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
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

st.title("⚡ PWM Signal Simulator Dashboard")
st.markdown("---")
st.markdown(
    "Adjust the duty cycle and frequency to simulate PWM signals and observe their effects on LED brightness and motor speed."
)


if "preset_mode" not in st.session_state:
    st.session_state.preset_mode = "Normal"
if "duty_cycle" not in st.session_state:
    st.session_state.duty_cycle = 50
if "comparison_mode" not in st.session_state:
    st.session_state.comparison_mode = False
if "comparison_duty_cycle" not in st.session_state:
    st.session_state.comparison_duty_cycle = 70

st.sidebar.header("🎚️ PWM Controls")
st.sidebar.markdown("---")

preset_options = {
    "Eco": 25,
    "Normal": 50,
    "Performance": 85
}

def apply_preset_mode():
    st.session_state.duty_cycle = preset_options[st.session_state.preset_mode]

preset_mode = st.sidebar.selectbox(
    label="Preset Modes",
    options=list(preset_options.keys()),
    key="preset_mode",
    on_change=apply_preset_mode,
    help="Choose a quick PWM profile for the duty cycle"
)

duty_cycle = st.sidebar.slider(
    label="Duty Cycle (%)",
    min_value=DUTY_CYCLE_MIN,
    max_value=DUTY_CYCLE_MAX,
    step=1,
    key="duty_cycle",
    help="Percentage of time the signal is HIGH in one cycle"
)

frequency = st.sidebar.number_input(
    label="Frequency (Hz)",
    min_value=FREQUENCY_MIN,
    max_value=FREQUENCY_MAX,
    value=1000,
    step=100,
    help="Number of PWM cycles per second"
)

frequency = int(np.clip(frequency, FREQUENCY_MIN, FREQUENCY_MAX))

time_duration = st.sidebar.slider(
    label="Time Window (ms)",
    min_value=TIME_DURATION_MIN,
    max_value=TIME_DURATION_MAX,
    value=5,
    step=1,
    help="Duration of waveform to display"
)

comparison_mode = st.sidebar.checkbox(
    label="Enable Comparison Mode",
    value=False,
    key="comparison_mode",
    help="Compare the current PWM setting with a second duty cycle"
)

if comparison_mode:
    comparison_duty_cycle = st.sidebar.slider(
        label="Comparison Duty Cycle (%)",
        min_value=DUTY_CYCLE_MIN,
        max_value=DUTY_CYCLE_MAX,
        step=1,
        key="comparison_duty_cycle",
        help="Second PWM setting used for comparison"
    )
else:
    comparison_duty_cycle = None

selected_device = st.sidebar.selectbox(
    label="Device",
    options=["LED", "Motor", "Buzzer", "Heater", "Capacitor", "Inductor", "Zener Diode", "Diode", "Transistor"],
    index=0,
    help="Choose the device to preview in the simulation panel"
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Device Parameters")

device_params = {}

if selected_device == "Capacitor":
    device_params["R"] = st.sidebar.slider(
        "Resistance (Ω)",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100
    )
    device_params["C"] = st.sidebar.slider(
        "Capacitance (F)",
        min_value=1e-6,
        max_value=1e-3,
        value=1e-4,
        format="%.6f"
    )
elif selected_device == "Inductor":
    device_params["R"] = st.sidebar.slider(
        "Resistance (Ω)",
        min_value=10,
        max_value=100,
        value=50,
        step=5
    )
    device_params["L"] = st.sidebar.slider(
        "Inductance (H)",
        min_value=1e-3,
        max_value=10.0,
        value=0.1,
        format="%.4f"
    )
elif selected_device == "Diode":
    device_params["Vf"] = st.sidebar.slider(
        "Forward Voltage (V)",
        min_value=0.3,
        max_value=0.9,
        value=0.7,
        step=0.05
    )
elif selected_device == "Zener Diode":
    device_params["Vz"] = st.sidebar.slider(
        "Zener Voltage (V)",
        min_value=2.4,
        max_value=12.0,
        value=5.1,
        step=0.3
    )
elif selected_device == "Transistor":
    device_params["Vth"] = st.sidebar.slider(
        "Threshold Voltage (V)",
        min_value=0.5,
        max_value=1.2,
        value=0.7,
        step=0.05
    )
    device_params["Vsat"] = st.sidebar.slider(
        "Saturation Voltage (V)",
        min_value=0.1,
        max_value=0.3,
        value=0.2,
        step=0.05
    )

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Tips:**\n"
    "- Higher duty cycle increases LED brightness\n"
    "- Higher frequency increases motor smoothness\n"
    "- 0% duty cycle turns OFF, 100% turns ON"
)


def generate_pwm_signal(duty_cycle, frequency, time_duration_ms):
    """Generate a PWM square waveform scaled to 0-5V."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    frequency = max(FREQUENCY_MIN, min(int(frequency), FREQUENCY_MAX))
    time_duration_ms = max(TIME_DURATION_MIN, time_duration_ms)
    
    if frequency <= 0:
        frequency = 1000
    
    period = 1.0 / frequency
    time_duration_sec = time_duration_ms / 1000.0
    
    samples_per_cycle = min(200, max(50, int(2000 / frequency)))
    num_cycles = frequency * time_duration_sec
    total_samples = max(1, int(samples_per_cycle * num_cycles))
    
    time_array = np.linspace(0, time_duration_sec, total_samples)
    high_time = (duty_cycle / 100.0) * period
    
    phase = np.mod(time_array, period)
    signal_normalized = (phase < high_time).astype(np.float64)
    signal_array = signal_normalized * VMAX
    
    return time_array * 1000.0, signal_array


def calculate_led_brightness(duty_cycle):
    """Calculate LED brightness percentage."""
    return int(np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))


def calculate_motor_speed(duty_cycle):
    """Determine motor speed category."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 33:
        return "Low"
    elif duty_cycle < 67:
        return "Medium"
    else:
        return "High"


def get_motor_color(speed_category):
    """Get color for motor speed indicator."""
    color_map = {
        "OFF": "#808080",
        "Low": "#3498db",
        "Medium": "#f39c12",
        "High": "#e74c3c"
    }
    return color_map.get(speed_category, "#808080")


def calculate_buzzer_status(duty_cycle):
    """Determine buzzer sound level."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "Silent"
    elif duty_cycle < 50:
        return "Low Sound"
    else:
        return "Loud Sound"


def calculate_heater_status(duty_cycle):
    """Determine heater temperature state."""
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    if duty_cycle == 0:
        return "OFF"
    elif duty_cycle < 50:
        return "Warm"
    else:
        return "Hot"


def get_device_display(device, duty_cycle, device_params=None):
    """Build the display content for the selected application device."""
    if device_params is None:
        device_params = {}
    
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    
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
    elif device == "Heater":
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
    elif device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        tau = R * C
        return {
            "title": "⚡ Capacitor (RC)",
            "value": f"τ={tau:.4f}s",
            "subtitle": "Time Constant",
            "background": "rgba(102, 126, 234, 0.2)",
            "value_color": "#667eea",
            "text_color": "#555"
        }
    elif device == "Inductor":
        L = device_params.get("L", 0.1)
        return {
            "title": "🔌 Inductor",
            "value": f"L={L:.3f}H",
            "subtitle": "Current Lag",
            "background": "rgba(139, 92, 246, 0.2)",
            "value_color": "#8b5cf6",
            "text_color": "#555"
        }
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return {
            "title": "📍 Diode",
            "value": f"Vf={Vf:.2f}V",
            "subtitle": "Forward Voltage",
            "background": "rgba(34, 197, 94, 0.2)",
            "value_color": "#22c55e",
            "text_color": "#555"
        }
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return {
            "title": "🔒 Zener Diode",
            "value": f"Vz={Vz:.2f}V",
            "subtitle": "Regulated Voltage",
            "background": "rgba(249, 115, 22, 0.2)",
            "value_color": "#f97316",
            "text_color": "#555"
        }
    else:
        Vth = device_params.get("Vth", 0.7)
        return {
            "title": "⚙️ Transistor",
            "value": f"Vth={Vth:.2f}V",
            "subtitle": "Threshold",
            "background": "rgba(34, 197, 94, 0.2)",
            "value_color": "#22c55e",
            "text_color": "#555"
        }


def get_smart_insight(device, duty_cycle, device_params=None):
    """Return a dynamic insight message based on the device and parameters."""
    if device_params is None:
        device_params = {}
    
    duty_cycle = np.clip(duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX)
    
    if device == "Capacitor":
        R = device_params.get("R", 1000)
        C = device_params.get("C", 1e-4)
        tau = R * C
        return (
            "RC Smoothing",
            f"PWM is being smoothed into DC using RC time constant τ = {tau:.6f}s. Increase tau to reduce ripple and harmonics.",
            "#667eea"
        )
    elif device == "Inductor":
        return (
            "RL Filtering",
            "Current ripple is reduced due to inductive smoothing. Higher L = slower response, smoother current draw.",
            "#8b5cf6"
        )
    elif device == "Diode":
        Vf = device_params.get("Vf", 0.7)
        return (
            "Rectification",
            f"One-way conduction with forward drop Vf = {Vf:.2f}V. Only half-wave passes through.",
            "#22c55e"
        )
    elif device == "Zener Diode":
        Vz = device_params.get("Vz", 5.1)
        return (
            "Voltage Clamping",
            f"Voltage is clamped to safe breakdown level Vz = {Vz:.2f}V. Ideal for overvoltage protection.",
            "#f97316"
        )
    elif device == "Transistor":
        Vth = device_params.get("Vth", 0.7)
        return (
            "Digital Switching",
            f"Operating as a digital switch with threshold Vth = {Vth:.2f}V. Sharp ON/OFF behavior.",
            "#22c55e"
        )
    elif device == "Motor":
        return (
            "Current Smoothing",
            "Mechanical inertia and back-EMF smooth motor response. Higher frequency = smoother rotation.",
            "#ff6b6b"
        )
    elif device == "Heater":
        return (
            "Thermal Response",
            "Heat dissipation smooths thermal response. Long time constant filters rapid PWM changes.",
            "#ffa500"
        )
    else:
        if duty_cycle < 30:
            return ("Energy Saving", "Energy-saving mode is active. Power draw stays low and efficient.", "#2ecc71")
        elif duty_cycle <= 70:
            return ("Balanced", "Balanced operating range. Output and efficiency are in a healthy middle zone.", "#f39c12")
        else:
            return ("High Power Warning", "High-power region reached. Expect stronger output, more heat, and higher energy usage.", "#e74c3c")


time_array, signal_array = generate_pwm_signal(duty_cycle, frequency, time_duration)
device_output = process_device_signal(selected_device, signal_array, time_array, device_params)
led_brightness = calculate_led_brightness(duty_cycle)
motor_speed = calculate_motor_speed(duty_cycle)
motor_color = get_motor_color(motor_speed)
device_display = get_device_display(selected_device, duty_cycle, device_params)
insight_label, insight_text, insight_color = get_smart_insight(selected_device, duty_cycle, device_params)
motor_animation_speed = max(0.5, 3.0 - duty_cycle / 50.0)


col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.subheader("📊 PWM Waveform")
    
    fig, ax = plt.subplots(figsize=(12, 4), dpi=100)
    
    ax.step(time_array, signal_array, linewidth=2, color="#667eea", label="VIN (PWM Signal)", where="post")
    ax.fill_between(time_array, 0, signal_array, alpha=0.3, color="#667eea", step="post")
    
    if device_output is not None and not np.array_equal(device_output, signal_array):
        if selected_device in ["Capacitor", "Inductor", "Motor", "Heater"]:
            ax.plot(time_array, device_output, linewidth=2, color="#e74c3c", label="VOUT (Device Output)", linestyle="-")
            ax.fill_between(time_array, 0, device_output, alpha=0.15, color="#e74c3c")
        else:
            ax.step(time_array, device_output, linewidth=2, color="#e74c3c", label="VOUT (Device Output)", where="post")
            ax.fill_between(time_array, 0, device_output, alpha=0.15, color="#e74c3c", step="post")
    
    ax.set_xlabel("Time (ms)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Voltage (V)", fontsize=12, fontweight="bold")
    ax.set_ylim(-0.5, 5.5)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_yticklabels(["0V", "1V", "2V", "3V", "4V", "5V"])
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper right", fontsize=10)
    
    ax.text(0.5, 1.15, f"Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
            transform=ax.transAxes, fontsize=11, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round", facecolor="#667eea", alpha=0.7, edgecolor="none"),
            color="white")
    
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)


with col2:
    st.subheader("📈 Real-World Effects")
    st.markdown("")
    
    st.markdown(f"#### {device_display['title']}")
    device_html = f"""
    <div style="background-color: {device_display['background']}; padding: 30px; border-radius: 10px; text-align: center; color: {device_display['value_color']};">
        <div style="font-size: 36px; font-weight: bold;">{device_display['value']}</div>
        <div style="font-size: 14px; margin-top: 6px; opacity: 0.9; color: {device_display['text_color']};">{device_display['subtitle']}</div>
    </div>
    """
    st.markdown(device_html, unsafe_allow_html=True)
    
    st.markdown("#### Animated Device Preview")
    
    led_intensity = max(0.18, duty_cycle / 100.0)
    buzzer_pulse_speed = max(0.55, 1.7 - (duty_cycle / 120.0))
    heat_bar_height = max(22, int(28 + (duty_cycle * 0.55)))
    heat_overlay_alpha = 0.28 + (duty_cycle / 180.0)
    
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
                    <div class="gear-spin" style="animation-duration:{motor_animation_speed:.2f}s;">⚙️</div>
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
    elif selected_device == "Heater":
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
    elif selected_device == "Capacitor":
        charge_intensity = max(0.2, duty_cycle / 100.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Capacitor Charging</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="capacitor-orb" style="opacity:{charge_intensity}; box-shadow: 0 0 {15 + duty_cycle * 1.5}px rgba(102, 126, 234, {0.2 + duty_cycle / 140});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Energy storage smooths voltage response</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Inductor":
        lag_intensity = max(0.3, (duty_cycle + 30) / 130.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Inductor Current Lag</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="inductor-coil" style="opacity:{lag_intensity}; box-shadow: 0 0 {12 + duty_cycle}px rgba(139, 92, 246, {0.25 + duty_cycle / 150});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Current lags voltage response</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Diode":
        diode_glow = max(0.2, duty_cycle / 100.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Diode Conduction</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="diode-arrow" style="opacity:{diode_glow}; text-shadow: 0 0 {10 + duty_cycle}px rgba(34, 197, 94, 0.8);">→</div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">One-way conduction during ON phase</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif selected_device == "Zener Diode":
        clamp_intensity = max(0.2, min(1.0, (duty_cycle + 20) / 100.0))
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Zener Voltage Clamp</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="zener-cap" style="opacity:{clamp_intensity}; box-shadow: 0 0 {10 + duty_cycle * 0.8}px rgba(249, 115, 22, {0.3 + duty_cycle / 170});"></div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Regulates voltage to breakdown level</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        switch_speed = max(0.8, 1.2 - duty_cycle / 150.0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="feature-title">Transistor Switch</div>
                <div style="display:flex; justify-content:center; align-items:center; min-height:94px;">
                    <div class="transistor-gate" style="animation-duration:{switch_speed:.2f}s;">ON</div>
                </div>
                <div style="text-align:center; margin-top:10px; color:#5b6472; font-size:13px;">Sharp digital switching behavior</div>
            </div>
            """,
            unsafe_allow_html=True
        )


st.markdown("---")
st.subheader("📋 Detailed PWM Parameters")

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    st.metric(
        label="Duty Cycle",
        value=f"{duty_cycle}%",
        delta="HIGH" if duty_cycle > 50 else ("LOW" if duty_cycle < 50 else "MEDIUM")
    )

with metric_col2:
    period_ms = (1.0 / frequency) * 1000
    st.metric(label="Period", value=f"{period_ms:.3f} ms")

with metric_col3:
    high_time_ms = (duty_cycle / 100.0) * (1.0 / frequency) * 1000
    st.metric(label="HIGH Time", value=f"{high_time_ms:.3f} ms")

with metric_col4:
    low_time_ms = ((100 - duty_cycle) / 100.0) * (1.0 / frequency) * 1000
    st.metric(label="LOW Time", value=f"{low_time_ms:.3f} ms")


st.markdown("---")
st.subheader("🧠 Smart Insight")

comparison_note = ""
if comparison_mode and comparison_duty_cycle is not None:
    comparison_duty_cycle = int(np.clip(comparison_duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))
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
        {f'<div style="margin-top: 6px; font-size: 13px; color: #667085;">Comparison: {comparison_note}</div>' if comparison_note else ""}
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown("---")
st.subheader("💡 Smart Recommendation System")

if selected_device == "Capacitor":
    st.info(
        """💡 **RC Filter Optimization**
        
- Increase R or C to reduce ripple
- Trade-off: Higher RC = slower response
- Typical: τ = 1-100ms for audio filtering
- Choose values based on cutoff frequency: f_c = 1/(2πRC)
        """
    )
elif selected_device == "Inductor":
    st.info(
        """💡 **RL Filter Optimization**
        
- Increase L to smooth current transients
- Higher frequency = less ripple needed
- Typical: L = 1-100mH for power supplies
- Watch for ringing at high switching rates
        """
    )
elif selected_device == "Zener Diode":
    st.info(
        """💡 **Voltage Regulation Tips**
        
- Ensure Zener rating is less than supply voltage
- Add series resistor to limit current
- Typical Zener: 3.3V, 5V, 12V
- Use in parallel with load for regulation
        """
    )
elif selected_device == "Transistor":
    st.info(
        """💡 **Switch Optimization**
        
- Ensure base/gate threshold voltage is met
- Use PWM frequency > 20kHz to avoid audible noise
- Provide adequate base current for saturation
- Add protection diodes for inductive loads
        """
    )
elif selected_device == "Motor":
    st.info(
        """💡 **Motor Control Tips**
        
- Use higher frequency for smoother rotation (>2kHz)
- Lower frequency = cogging/jerking
- Add flywheel diode to protect circuit
- Monitor current for stall conditions
        """
    )
elif selected_device == "Heater":
    st.info(
        """💡 **Thermal Management**
        
- Use low frequency for thermal smoothing
- Monitor temperature limits
- Add thermal cutoff protection
- Consider duty cycle ramps for safety
        """
    )
else:
    if duty_cycle < 30:
        st.info(
            """🟢 **Energy Saving Mode**
            
Your PWM is set to a low duty cycle. This is ideal for:
- Battery-powered applications
- Reducing heat generation
- Extending device lifespan
- Energy-efficient operation
            """
        )
    elif 30 <= duty_cycle <= 70:
        st.info(
            """🟡 **Balanced Performance**
            
Your PWM is in the optimal range for:
- Smooth operation
- Reliable control
- Balanced power consumption
- Safe long-term operation
            """
        )
    else:
        st.warning(
            """🔴 **High Power Mode**
            
Your PWM is set to high power. Be aware:
- Increased power consumption
- Heat generation may increase
- Ensure adequate cooling/ventilation
- Consider reducing duty cycle for sustained use
            """
        )


st.markdown("---")

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


st.markdown("---")
st.subheader("📊 Advanced View - Signal Characteristics")

avg_voltage = (duty_cycle / 100.0) * VMAX

fig_advanced = go.Figure()

fig_advanced.add_trace(go.Scatter(
    x=time_array,
    y=signal_array,
    mode="lines",
    name="PWM Signal (VIN)",
    line=dict(color="#667eea", width=2, shape="hv"),
    fill="tozeroy",
    fillcolor="rgba(102, 126, 234, 0.3)"
))

if device_output is not None and not np.array_equal(device_output, signal_array):
    if selected_device in ["Capacitor", "Inductor", "Motor", "Heater"]:
        fig_advanced.add_trace(go.Scatter(
            x=time_array,
            y=device_output,
            mode="lines",
            name="Device Output (VOUT)",
            line=dict(color="#e74c3c", width=2, shape="linear"),
            fill="tozeroy",
            fillcolor="rgba(230, 116, 60, 0.15)"
        ))
    else:
        fig_advanced.add_trace(go.Scatter(
            x=time_array,
            y=device_output,
            mode="lines",
            name="Device Output (VOUT)",
            line=dict(color="#e74c3c", width=2, shape="hv"),
            fill="tozeroy",
            fillcolor="rgba(230, 116, 60, 0.15)"
        ))

fig_advanced.add_hline(
    y=avg_voltage,
    line_dash="dash",
    line_color="red",
    name=f"Average Voltage ({avg_voltage:.2f}V)"
)

fig_advanced.update_layout(
    title=f"PWM Signal Analysis - Duty Cycle: {duty_cycle}% | Frequency: {frequency} Hz",
    xaxis_title="Time (ms)",
    yaxis_title="Voltage (V)",
    hovermode="x unified",
    height=400,
    template="plotly_dark"
)

st.plotly_chart(fig_advanced, use_container_width=True)


if comparison_mode and comparison_duty_cycle is not None:
    comparison_duty_cycle = int(np.clip(comparison_duty_cycle, DUTY_CYCLE_MIN, DUTY_CYCLE_MAX))
    
    st.markdown("---")
    st.subheader("🔍 Comparison Mode")
    
    comparison_time_array, comparison_signal_array = generate_pwm_signal(comparison_duty_cycle, frequency, time_duration)
    comparison_fig = go.Figure()
    
    comparison_fig.add_trace(go.Scatter(
        x=time_array,
        y=signal_array,
        mode="lines",
        name=f"Primary ({duty_cycle}%)",
        line=dict(color="#667eea", width=2, shape="hv"),
        fill="tozeroy",
        fillcolor="rgba(102, 126, 234, 0.18)"
    ))
    
    comparison_fig.add_trace(go.Scatter(
        x=comparison_time_array,
        y=comparison_signal_array,
        mode="lines",
        name=f"Comparison ({comparison_duty_cycle}%)",
        line=dict(color="#e67e22", width=2, dash="dash", shape="hv"),
        fill="tozeroy",
        fillcolor="rgba(230, 126, 34, 0.15)"
    ))
    
    comparison_fig.update_layout(
        title=f"PWM Comparison - {duty_cycle}% vs {comparison_duty_cycle}% Duty Cycle",
        xaxis_title="Time (ms)",
        yaxis_title="Voltage (V)",
        yaxis=dict(range=[-0.5, 5.5]),
        hovermode="x unified",
        height=420,
        template="plotly_dark"
    )
    
    st.plotly_chart(comparison_fig, use_container_width=True)
    
    comparison_col1, comparison_col2 = st.columns(2)
    with comparison_col1:
        st.metric("Primary Duty Cycle", f"{duty_cycle}%")
    with comparison_col2:
        st.metric("Comparison Duty Cycle", f"{comparison_duty_cycle}%")


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


st.markdown("---")
st.subheader("🤖 AI Chat Assistant")

user_question = st.text_input(
    "💬 Ask me about PWM:",
    placeholder="e.g., 'What is PWM?', 'How does LED work?', 'Tell me about motor'"
)

if user_question:
    question_lower = user_question.lower()
    response = None
    
    if any(word in question_lower for word in ["what is pwm", "what does pwm mean"]):
        response = (
            "**PWM (Pulse Width Modulation)** is a technique that controls average power by varying how long a signal "
            "stays ON vs OFF in each cycle. Instead of changing voltage, PWM switches the signal rapidly HIGH and LOW. "
            "The ratio of ON-time to total cycle-time is called the **duty cycle**. Higher duty cycle = more power. "
            "This is used in your dashboard to control LED brightness, motor speed, buzzer intensity, heater heat, and more advanced components like RC circuits, inductors, and semiconductor devices."
        )
    
    elif any(word in question_lower for word in ["what is duty", "duty cycle", "duty"]):
        response = (
            "**Duty cycle** is the percentage of time the PWM signal is HIGH (ON) within one complete cycle. "
            "For example:\n"
            "- **0% duty cycle** = Signal always OFF (no power)\n"
            "- **50% duty cycle** = Signal ON half the time, OFF half the time\n"
            "- **100% duty cycle** = Signal always ON (full power)\n"
            "Duty cycle directly controls the **average power** delivered to your device. Use the duty cycle slider "
            "on the left to see how it affects LED brightness, motor speed, and other outputs!"
        )
    
    elif any(word in question_lower for word in ["frequency", "what is frequency", "hz"]):
        response = (
            "**Frequency** is how many complete PWM cycles happen per second, measured in **Hertz (Hz)**. "
            "For example, 1000 Hz = 1000 cycles per second.\n\n"
            "**Why frequency matters:**\n"
            "- **Higher frequency** = Smoother operation, less audible noise (better for motors & buzzers)\n"
            "- **Lower frequency** = Can cause flickering in LEDs or audible buzz\n"
            "Adjust the frequency slider to see how it affects the waveform smoothness and device response!"
        )
    
    elif "pwm" in question_lower and any(word in question_lower for word in ["why", "use", "advantage", "benefit"]):
        response = (
            "**Why PWM is so useful:**\n"
            "✓ **Energy efficient** - No wasted power as heat (unlike resistors)\n"
            "✓ **Simple control** - Easy to control with digital signals\n"
            "✓ **Smooth output** - Simulates analog behavior from digital circuits\n"
            "✓ **Versatile** - Works for LEDs, motors, heaters, buzzers, and power supplies\n"
            "✓ **Cost-effective** - Requires minimal hardware\n"
            "PWM is the industry standard for power control in embedded systems!"
        )
    
    elif any(word in question_lower for word in ["led", "light", "brightness"]):
        response = (
            "**LED Control with PWM:**\n"
            "The LED's brightness is controlled by the duty cycle:\n"
            "- **0%** = LED OFF (no brightness)\n"
            "- **50%** = LED at half brightness\n"
            "- **100%** = LED at full brightness\n\n"
            "Your eyes perceive the rapidly flickering light (at high frequency) as continuous brightness. "
            "The higher the duty cycle, the brighter the LED appears! Try adjusting the duty cycle slider "
            "and selecting 'LED' from the device dropdown to see the effect."
        )
    
    elif any(word in question_lower for word in ["motor", "speed", "rotation"]):
        response = (
            "**Motor Speed Control with PWM:**\n"
            "Motor speed is controlled by the duty cycle:\n"
            "- **0%** = Motor OFF\n"
            "- **Low duty cycle (1-33%)** = Slow rotation\n"
            "- **Medium duty cycle (34-66%)** = Medium speed\n"
            "- **High duty cycle (67-100%)** = Maximum speed\n\n"
            "Higher duty cycle delivers more average power to the motor, making it rotate faster. "
            "Select 'Motor' from the device dropdown to see the animated gear speed change with duty cycle!"
        )
    
    elif any(word in question_lower for word in ["buzzer", "sound", "beep", "noise"]):
        response = (
            "**Buzzer Sound Control with PWM:**\n"
            "PWM controls the buzzer's sound intensity:\n"
            "- **0%** = Silent (no sound)\n"
            "- **Low duty cycle (1-49%)** = Low sound level\n"
            "- **High duty cycle (50-100%)** = Loud sound\n\n"
            "The frequency slider also affects the buzzer tone. Higher frequencies produce higher-pitched sounds. "
            "Select 'Buzzer' from the device dropdown to visualize the sound level with animated waveforms!"
        )
    
    elif any(word in question_lower for word in ["heater", "heat", "temperature", "warm", "hot"]):
        response = (
            "**Heater Temperature Control with PWM:**\n"
            "PWM controls heating intensity:\n"
            "- **0%** = Heater OFF\n"
            "- **Low duty cycle (1-49%)** = Warm (low heat)\n"
            "- **High duty cycle (50-100%)** = Hot (high heat)\n\n"
            "Higher duty cycle means the heater is ON longer, generating more heat. "
            "Select 'Heater' from the device dropdown to see the animated heat bars showing temperature rise!"
        )
    
    elif any(word in question_lower for word in ["capacitor", "rc"]):
        response = (
            "**Capacitor (RC Circuit) with PWM:**\n\n"
            "**Principle:** A capacitor stores charge and resists voltage changes. Combined with resistance, it creates an RC filter.\n\n"
            "**Waveform Effect:** The square PWM wave is smoothed into a curved exponential rise/fall. Output approaches input with time constant τ = R×C:\n"
            "- Higher τ = More smoothing, slower response\n"
            "- Lower τ = Less smoothing, faster response\n\n"
            "**Real-World Uses:** Audio filtering, power supply ripple reduction, gate delay circuits, sensor debouncing."
        )
    
    elif any(word in question_lower for word in ["inductor", "rl", "coil"]):
        response = (
            "**Inductor (RL Circuit) with PWM:**\n\n"
            "**Principle:** An inductor resists current changes via back-EMF (Faraday's law). RL circuits create current lag.\n\n"
            "**Waveform Effect:** Current lags voltage. Output rises/falls slower than input due to inductance L. Higher L = slower response.\n\n"
            "**Real-World Uses:** Motor control, power supply inductors, current smoothing in LED drivers, energy storage in switch-mode supplies."
        )
    
    elif any(word in question_lower for word in ["diode", "rectif"]):
        response = (
            "**Diode with PWM:**\n\n"
            "**Principle:** A diode conducts only in one direction. Forward bias enables conduction; reverse bias blocks it. Forward voltage drop Vf ≈ 0.7V (silicon).\n\n"
            "**Waveform Effect:** Output is half-wave rectified. PWM positive half-cycles pass through (minus Vf). Negative cycles are blocked → output = 0V.\n\n"
            "**Real-World Uses:** Rectification (AC→DC), reverse polarity protection, charge pump circuits, solar panel bypass."
        )
    
    elif any(word in question_lower for word in ["zener", "regulation", "clamp", "regul"]):
        response = (
            "**Zener Diode with PWM:**\n\n"
            "**Principle:** Zener diodes conduct in reverse bias at a precise breakdown voltage Vz. Used for voltage regulation and overvoltage protection.\n\n"
            "**Waveform Effect:** Output voltage is clamped to Vz. Below Vz, behaves like normal diode. Above Vz, current increases but voltage stays constant → flat-top output.\n\n"
            "**Real-World Uses:** Voltage regulation, overvoltage protection, reference circuits, transient suppression."
        )
    
    elif any(word in question_lower for word in ["transistor", "switch", "gate", "thresh", "bjt"]):
        response = (
            "**Transistor as Switch with PWM:**\n\n"
            "**Principle:** Transistors operate as digital switches. Base/gate voltage controls collector/drain current. Threshold voltage Vth determines ON/OFF.\n\n"
            "**Waveform Effect:** Output is rectangular binary: fully ON (near Vcc) or fully OFF (0V). Sharp switching with no linear region when driven hard.\n\n"
            "**Real-World Uses:** Motor control, relay drivers, LED brightness control, power switching in audio amplifiers and DC-DC converters."
        )
    
    elif any(word in question_lower for word in ["what does this", "how does this work"]):
        response = (
            "**Welcome to the PWM Signal Simulator Dashboard!** 📊\n\n"
            "This interactive tool lets you:\n"
            "✓ Adjust duty cycle and frequency with sliders\n"
            "✓ See the PWM waveform change in real-time\n"
            "✓ Observe effects on LED, Motor, Buzzer, Heater, and advanced electronics\n"
            "✓ Simulate RC circuits, inductors, diodes, Zener diodes, and transistors\n"
            "✓ Compare two different PWM settings side-by-side\n"
            "✓ Use preset modes (Eco, Normal, Performance) for quick setup\n"
            "✓ Get smart recommendations based on your settings\n\n"
            "Start by adjusting the duty cycle slider and selecting different devices to see PWM in action!"
        )
    
    elif any(word in question_lower for word in ["graph", "waveform", "understand the", "plot"]):
        response = (
            "**Understanding the PWM Waveform Graph:**\n\n"
            "The graph shows the PWM signal and device response over time:\n"
            "- **Blue line (VIN)** = Input PWM signal (0-5V square wave)\n"
            "- **Red line (VOUT)** = Device output (varies by device type)\n"
            "- **Shaded area** = Time the signal is ON\n"
            "- **Duty cycle %** = How much of the cycle is shaded (ON time)\n\n"
            "The **red dashed line** shows the average voltage, which equals (duty cycle / 100) × 5V. "
            "For example, at 50% duty cycle, average voltage = 2.5V. This average is what controls your device!"
        )
    
    elif any(word in question_lower for word in ["what happens", "change", "effect", "when you"]):
        response = (
            "**When You Change the Duty Cycle:**\n\n"
            "The waveform updates instantly! You'll see:\n"
            "- **Wider shaded area** = Higher duty cycle (more ON time)\n"
            "- **Higher red line** = Higher average voltage\n"
            "- **Larger device effect** = More power, more brightness/speed/heat\n\n"
            "Different devices respond differently:\n"
            "- **LED**: Brightness increases proportionally\n"
            "- **Motor**: Speed increases with higher duty cycle\n"
            "- **Capacitor/Inductor**: Output smoothness changes based on circuit properties\n"
            "- **Diode/Zener**: Output is clipped or regulated\n"
            "- **Transistor**: Digital ON/OFF switching\n\n"
            "This demonstrates how PWM gives you precise analog-like control from a digital signal!"
        )
    
    elif any(word in question_lower for word in ["comparison", "preset", "eco", "normal", "performance"]):
        response = (
            "**Preset Modes & Comparison Feature:**\n\n"
            "**Preset Modes** provide quick-start configurations:\n"
            "- **Eco Mode** (25%) = Energy-saving, minimal power\n"
            "- **Normal Mode** (50%) = Balanced operation\n"
            "- **Performance Mode** (85%) = Maximum power output\n\n"
            "**Comparison Mode** lets you compare two PWM settings side-by-side:\n"
            "1. Enable 'Comparison Mode' checkbox in the sidebar\n"
            "2. Set the comparison duty cycle using the second slider\n"
            "3. See both waveforms overlaid in a comparison graph\n\n"
            "This helps you understand the difference between settings!"
        )
    
    else:
        response = (
            "I'm here to help with PWM and this simulation! 🚀\n\n"
            "Try asking about:\n"
            "- **PWM Concepts:** 'What is PWM?', 'What is duty cycle?', 'What is frequency?', 'Why use PWM?'\n"
            "- **Devices:** 'How does LED work?', 'Tell me about motor', 'How does buzzer work?', 'Heater control'\n"
            "- **Advanced:** 'Capacitor', 'Inductor', 'Diode', 'Zener', 'Transistor'\n"
            "- **Project:** 'What does this dashboard do?', 'How does the graph work?', 'What happens when duty cycle changes?'"
        )
    
    st.success(f"**🤖 AI Assistant:** {response}")
            "**Preset Modes & Comparison Feature:**\n\n"
            "**Preset Modes** provide quick-start configurations:\n"
            "- **Eco Mode** (25%) = Energy-saving, minimal power\n"
            "- **Normal Mode** (50%) = Balanced operation\n"
            "- **Performance Mode** (85%) = Maximum power output\n\n"
            "**Comparison Mode** lets you compare two PWM settings side-by-side:\n"
            "1. Enable 'Comparison Mode' checkbox in the sidebar\n"
            "2. Set the comparison duty cycle using the second slider\n"
            "3. See both waveforms overlaid in a comparison graph\n\n"
            "This helps you understand the difference between settings!"
        )
    
    else:
        response = (
            "I'm here to help with PWM and this simulation! 🚀\n\n"
            "Try asking about:\n"
            "- **PWM Concepts:** 'What is PWM?', 'What is duty cycle?', 'What is frequency?', 'Why use PWM?'\n"
            "- **Devices:** 'How does LED work?', 'Tell me about motor', 'How does buzzer work?', 'Heater control'\n"
            "- **Advanced:** 'Capacitor', 'Inductor', 'Diode', 'Zener', 'Transistor'\n"
            "- **Project:** 'What does this dashboard do?', 'How does the graph work?', 'What happens when duty cycle changes?'"
        )
    
    st.success(f"**🤖 AI Assistant:** {response}")
