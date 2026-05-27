# =============================================================================
# PWM SIGNAL SIMULATOR DASHBOARD (CORE ENGINE - PART 1)
# =============================================================================

# ==============================
# Imports
# ==============================
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import base64
import json
from io import StringIO
from datetime import datetime
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception:
    SentenceTransformer = None
    _HAS_SENTENCE_TRANSFORMERS = False
from sklearn.metrics.pairwise import cosine_similarity

# Optional external config (must exist)
import config


# ==============================
# App Configuration
# ==============================
st.set_page_config(
    page_title="PWM Simulator",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ PWM Signal Simulator")
st.markdown("Real-time PWM simulation with device-level response modeling.")


# =============================================================================
# PWM GENERATION MODULE
# =============================================================================

def _sanitize_time_steps(frequency, time_duration_s, samples_per_cycle=200):
    if frequency <= 0:
        raise ValueError("Frequency must be > 0")

    period = 1.0 / frequency
    dt = period / samples_per_cycle
    t = np.arange(0, time_duration_s, dt)

    return t, dt


def generate_pwm_signal(duty_cycle, frequency, time_duration_s):
    duty = np.clip(duty_cycle / 100.0, 0.0, 1.0)

    t, dt = _sanitize_time_steps(frequency, time_duration_s)
    period = 1.0 / frequency

    phase = np.mod(t, period)
    pwm = np.where(phase < duty * period, config.VMAX, 0.0)

    return t, pwm, dt


# =============================================================================
# DEVICE PHYSICS MODULE
# =============================================================================

def first_order_system(vin, dt, tau):
    y = np.zeros_like(vin)

    for i in range(1, len(vin)):
        y[i] = y[i-1] + (vin[i] - y[i-1]) * (dt / tau)

    return y


def simulate_rc(vin, dt, R=1000, C=1e-6):
    return first_order_system(vin, dt, R * C)


def simulate_rl(vin, dt, R=100, L=1e-3):
    i = np.zeros_like(vin)

    for k in range(1, len(vin)):
        i[k] = i[k-1] + (vin[k] - i[k-1] * R) * (dt / L)

    return i 


def simulate_led(vin, Vf=2.0, R=220):
    return np.where(vin > Vf, 1.0, 0.0)


def simulate_diode(vin, Vf=0.7):
    return np.where(vin > Vf, vin - Vf, 0.0)


def simulate_zener(vin, Vz=3.3):
    return np.where(vin > Vz, Vz, vin)

def simulate_transistor(vin, Vth=1.0):
    return np.where(vin > Vth, vin, 0.0)


def simulate_motor(vin, dt, tau=0.05):
    return first_order_system(vin, dt, tau)


def simulate_heater(vin, dt, tau=0.5):
    return first_order_system(vin, dt, tau)


def simulate_buzzer(vin, threshold=2.5):
    return (vin > threshold).astype(float) * vin


def get_device_response(device, vin, dt):
    if device == "capacitor":
        return simulate_rc(vin, dt)
    elif device == "inductor":
        return simulate_rl(vin, dt)
    elif device == "led":
        return simulate_led(vin)
    elif device == "diode":
        return simulate_diode(vin)
    elif device == "zener":
        return simulate_zener(vin)
    elif device == "transistor":
        return simulate_transistor(vin)
    elif device == "motor":
        return simulate_motor(vin, dt)
    elif device == "heater":
        return simulate_heater(vin, dt)
    elif device == "buzzer":
        return simulate_buzzer(vin)
    else:
        raise ValueError("Unknown device")


# =============================================================================
# SIGNAL UTILITIES
# =============================================================================

def compute_metrics(signal):
    return {
        "mean": float(np.mean(signal)),
        "rms": float(np.sqrt(np.mean(signal**2))),
        "min": float(np.min(signal)),
        "max": float(np.max(signal))
    }


def downsample(t, y, max_points=5000):
    if len(y) <= max_points:
        return t, y
    step = len(y) // max_points
    return t[::step], y[::step]


# =============================================================================
# EXPORT UTILITIES
# =============================================================================

def export_csv(t, y, filename="pwm.csv"):
    buffer = StringIO()
    buffer.write("time,signal\n")

    for ti, yi in zip(t, y):
        buffer.write(f"{ti},{yi}\n")

    b64 = base64.b64encode(buffer.getvalue().encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'


# =============================================================================
# ARDUINO CODE GENERATOR
# =============================================================================

def duty_to_8bit(duty):
    return int(np.clip(duty, 0, 100) / 100 * 255)


def generate_arduino_code(frequency, duty_cycle, device="led", pin=9):

    duty8 = duty_to_8bit(duty_cycle)

    return f"""
int pwmPin = {pin};

void setup() {{
    pinMode(pwmPin, OUTPUT);
}}

void loop() {{
    analogWrite(pwmPin, {duty8});
}}
"""


# =============================================================================
# SMART INSIGHTS ENGINE
# =============================================================================

def generate_insights(device, frequency, duty_cycle, metrics):

    insights = []

    if duty_cycle < 10:
        insights.append("Low duty cycle → device mostly OFF.")
    elif duty_cycle > 90:
        insights.append("High duty cycle → near DC behavior.")

    if frequency < 50:
        insights.append("Low frequency → flicker/jerk likely.")
    elif frequency > 20000:
        insights.append("High frequency → smooth response.")

    if device == "led":
        insights.append("Brightness proportional to duty cycle.")

    elif device == "motor":
        insights.append("Speed depends on average voltage.")

    elif device == "capacitor":
        insights.append("Acts as low-pass filter.")

    elif device == "inductor":
        insights.append("Current ramps smoothly (triangular tendency).")

    insights.append(f"Mean: {metrics['mean']:.2f}")
    insights.append(f"RMS: {metrics['rms']:.2f}")

    return insights


# =============================================================================
# VISUALIZATION
# =============================================================================

def plot_comparison(t, pwm, output):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, pwm, "--", label="PWM Input")
    ax.plot(t, output, label="Device Output")
    ax.set_title("PWM vs Device Response")
    ax.grid(True)
    ax.legend()
    return fig


# =============================================================================
# STREAMLIT UI (CORE FLOW)
# =============================================================================

st.sidebar.header("PWM Controls")

frequency = st.sidebar.slider("Frequency (Hz)", 1, 20000, config.DEFAULT_FREQUENCY)
duty_cycle = st.sidebar.slider("Duty Cycle (%)", 0, 100, config.DEFAULT_DUTY_CYCLE)
time_window = st.sidebar.slider("Time Window (s)", 0.001, 0.1, config.DEFAULT_TIME_WINDOW)

device = st.sidebar.selectbox(
    "Device",
    ["capacitor", "inductor", "led", "diode", "zener", "transistor", "motor", "heater", "buzzer"]
)

pin = st.sidebar.selectbox("PWM Pin", [3, 5, 6, 9, 10, 11])

# ==============================
# Input Validation
# ==============================

if duty_cycle < 0 or duty_cycle > 100:
    st.error("Invalid duty cycle")
    st.stop()

if frequency <= 0:
    st.error("Frequency must be greater than 0")
    st.stop()

if time_window <= 0:
    st.error("Time window must be greater than 0")
    st.stop()
# ==============================
# Simulation Pipeline
# ==============================
t, pwm, dt = generate_pwm_signal(duty_cycle, frequency, time_window)
output = get_device_response(device, pwm, dt)

metrics = compute_metrics(output)
t_plot, pwm_plot = downsample(t, pwm)
_, out_plot = downsample(t, output)

# ==============================
# Output Display
# ==============================
st.subheader("Waveform Output")
st.pyplot(plot_comparison(t_plot, pwm_plot, out_plot))

st.markdown(export_csv(t, output), unsafe_allow_html=True)

st.subheader("Arduino Code")
st.code(generate_arduino_code(frequency, duty_cycle, device, pin), language="cpp")

st.subheader("Smart Insights")
for i in generate_insights(device, frequency, duty_cycle, metrics):
    st.write("•", i)

# =============================================================================
# PWM KNOWLEDGE BASE (DOMAIN LAYER)
# =============================================================================

KNOWLEDGE_BASE = [
    {"topic": "pwm", "text": "PWM controls power by switching ON/OFF rapidly. Duty cycle defines average output voltage."},
    {"topic": "duty cycle", "text": "Duty cycle is percentage of ON time in a PWM cycle. Higher duty increases average power."},
    {"topic": "frequency", "text": "PWM frequency is switching speed. High frequency reduces ripple and flicker."},
    {"topic": "led", "text": "LED brightness depends on duty cycle. PWM controls brightness via average current."},
    {"topic": "motor", "text": "Motor speed depends on average voltage. Low frequency may cause jerky motion."},
    {"topic": "capacitor", "text": "Capacitors smooth PWM signals by charging and discharging (low-pass filtering)."},
    {"topic": "inductor", "text": "Inductors resist sudden current change and create smoother current ramps."},
    {"topic": "diode", "text": "Diodes allow current flow in one direction only."},
    {"topic": "zener", "text": "Zener diodes clamp voltage at breakdown level."},
    {"topic": "transistor", "text": "Transistors act as PWM-controlled electronic switches."},
    {"topic": "heater", "text": "Heaters integrate PWM over time due to thermal inertia."},
    {"topic": "buzzer", "text": "Buzzers convert PWM into audible sound depending on frequency."}
]

# =============================================================================
# SEMANTIC CHATBOT ENGINE
# =============================================================================

_kb_texts = [item["text"] for item in KNOWLEDGE_BASE]

@st.cache_resource
def load_model():
    if not _HAS_SENTENCE_TRANSFORMERS or SentenceTransformer is None:
        raise RuntimeError(
            "sentence_transformers is not available. Install the package or run without the semantic chatbot features."
        )
    return SentenceTransformer("all-MiniLM-L6-v2")

if _HAS_SENTENCE_TRANSFORMERS:
    _model = load_model()
else:
    _model = None
_kb_texts = [x["text"] for x in KNOWLEDGE_BASE]

@st.cache_resource
def load_embeddings():
    return _model.encode(_kb_texts, normalize_embeddings=True)

if _model is not None:
    _kb_embeddings = load_embeddings()
else:
    _kb_embeddings = None

def get_chat_response(query, context=None):
    """
    Semantic retrieval-based chatbot for PWM domain.
    """

    # Safety fallback
    if _model is None or _kb_embeddings is None:
        return (
            "Semantic AI features are unavailable because "
            "sentence_transformers is not installed."
        )

    q_emb = _model.encode([query], normalize_embeddings=True)
    scores = cosine_similarity(q_emb, _kb_embeddings)[0]
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    answer = KNOWLEDGE_BASE[best_idx]["text"]

    # Context injection (device awareness)
    if context:
        device = context.get("device")
        if device:
            answer += f"\n\n(Device context: {device})"

        freq = context.get("frequency")
        duty = context.get("duty_cycle")

        if freq:
            answer += f"\nFrequency: {freq} Hz"
        if duty:
            answer += f", Duty Cycle: {duty}%"

    # fallback confidence handling
    if best_score < 0.35:
        return (
            "PWM relates to switching signals, duty cycle, and energy delivery. "
            "Try asking about LED, motor, capacitor, or frequency effects."
        )

    return answer


# =============================================================================
# STREAMLIT CHAT INTERFACE
# =============================================================================

st.subheader("🤖 PWM Smart AI Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_query = st.text_input("Ask about PWM, devices, or waveforms:")

if user_query:

    context = {
        "device": device,
        "frequency": frequency,
        "duty_cycle": duty_cycle
    }

    response = get_chat_response(user_query, context)

    st.session_state.chat_history.append(("You", user_query))
    st.session_state.chat_history.append(("AI", response))


# Render chat history (latest first)
for role, msg in st.session_state.chat_history[::-1]:
    if role == "You":
        st.markdown(f"**🧑 You:** {msg}")
    else:
        st.markdown(f"**🤖 AI:** {msg}")


# =============================================================================
# DEVICE ANIMATION ENGINE
# =============================================================================

import time

def animate_device(device_name, signal, speed=0.002):

    placeholder = st.empty()

    # Normalize signal
    norm = (signal - np.min(signal)) / (
        np.max(signal) - np.min(signal) + 1e-9
    )

    max_frames = 100
    step = max(1, len(norm) // max_frames)

    for v in norm[::step]:

        if device_name == "led":
            intensity = int(v * 255)

            html = f"""
            <div style="
                width:120px;
                height:120px;
                border-radius:50%;
                margin:auto;
                background-color: rgb({intensity},{intensity},0);
            "></div>
            """

            placeholder.markdown(html, unsafe_allow_html=True)

        elif device_name == "motor":
            placeholder.metric("Motor Speed (%)", int(v * 100))

        elif device_name == "heater":
            placeholder.metric(
                "Temperature Level",
                f"{int(v * 100)} °C"
            )

        elif device_name == "buzzer":
            state = "ON 🔊" if v > 0.5 else "OFF 🔇"
            placeholder.metric("Buzzer State", state)

        elif device_name == "capacitor":
            placeholder.progress(float(v))

        elif device_name == "inductor":
            placeholder.metric(
                "Inductor Current",
                int(v * 100)
            )

        elif device_name == "diode":
            state = "Conducting" if v > 0.1 else "Blocking"
            placeholder.metric("Diode State", state)

        elif device_name == "zener":
            state = "Clamped" if v > 0.8 else "Normal"
            placeholder.metric("Zener State", state)

        elif device_name == "transistor":
            state = "ON" if v > 0.5 else "OFF"
            placeholder.metric("Transistor", state)

        time.sleep(0.005)

# =============================================================================
# OPTIONAL: RUN ANIMATION BUTTON
# =============================================================================

st.subheader("🎞 Device Animation (Optional)")

if st.button("Run Animation"):

    animate_device(device, output)
