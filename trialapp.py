# =============================================================================
# PWM SIGNAL SIMULATOR DASHBOARD
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
from io import StringIO
import time

# ==============================
# OPTIONAL AI IMPORTS
# ==============================

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    _HAS_SENTENCE_TRANSFORMERS = True

except Exception:
    SentenceTransformer = None
    cosine_similarity = None
    _HAS_SENTENCE_TRANSFORMERS = False


# =============================================================================
# FALLBACK CONFIG
# =============================================================================

VMAX = 5.0
DEFAULT_FREQUENCY = 1000
DEFAULT_DUTY_CYCLE = 50
DEFAULT_TIME_WINDOW = 0.02


# =============================================================================
# APP CONFIG
# =============================================================================

st.set_page_config(
    page_title="PWM Simulator",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ PWM Signal Simulator")
st.markdown("Real-time PWM simulation with realistic device modeling.")


# =============================================================================
# PWM GENERATION
# =============================================================================

def generate_pwm_signal(duty_cycle, frequency, time_duration_s):

    duty = np.clip(duty_cycle / 100.0, 0.0, 1.0)

    period = 1.0 / frequency

    samples_per_cycle = 200

    dt = period / samples_per_cycle

    t = np.arange(0, time_duration_s, dt)

    phase = np.mod(t, period)

    pwm = np.where(
        phase < duty * period,
        VMAX,
        0.0
    )

    return t, pwm, dt


# =============================================================================
# DEVICE MODELS
# =============================================================================

def simulate_rc(vin, dt, R=1000, C=1e-6):

    tau = R * C

    vout = np.zeros_like(vin)

    for i in range(1, len(vin)):

        vout[i] = vout[i - 1] + (
            vin[i] - vout[i - 1]
        ) * (dt / tau)

    return vout


def simulate_rl(vin, dt, R=10, L=10e-3):

    current = np.zeros_like(vin)

    for i in range(1, len(vin)):

        di = (
            vin[i] - current[i - 1] * R
        ) * (dt / L)

        current[i] = current[i - 1] + di

    return current


def simulate_led(vin, Vf=2.0):

    brightness = np.where(
        vin > Vf,
        (vin - Vf) / (VMAX - Vf),
        0.0
    )

    return np.clip(brightness, 0.0, 1.0)


def simulate_diode(vin, dt, Vf=0.7, tau=0.0002):

    target = np.where(
        vin > Vf,
        vin - Vf,
        0.0
    )

    vout = np.zeros_like(vin)

    for i in range(1, len(vin)):

        vout[i] = vout[i - 1] + (
            target[i] - vout[i - 1]
        ) * (dt / tau)

    return vout


def simulate_zener(vin, dt, Vz=3.3, tau=0.0005):

    target = np.where(
        vin > Vz,
        Vz,
        vin
    )

    vout = np.zeros_like(vin)

    for i in range(1, len(vin)):

        vout[i] = vout[i - 1] + (
            target[i] - vout[i - 1]
        ) * (dt / tau)

    return vout


def simulate_transistor(vin, dt, Vth=1.2, gain=1.0, tau=0.0003):

    target = np.where(
        vin > Vth,
        (vin - Vth) * gain,
        0.0
    )

    vout = np.zeros_like(vin)

    for i in range(1, len(vin)):

        vout[i] = vout[i - 1] + (
            target[i] - vout[i - 1]
        ) * (dt / tau)

    return vout


def simulate_motor(vin, dt,
                   tau_electrical=0.002,
                   tau_mechanical=0.05):

    current = np.zeros_like(vin)

    for i in range(1, len(vin)):

        current[i] = current[i - 1] + (
            vin[i] - current[i - 1]
        ) * (dt / tau_electrical)

    speed = np.zeros_like(vin)

    for i in range(1, len(vin)):

        speed[i] = speed[i - 1] + (
            current[i] - speed[i - 1]
        ) * (dt / tau_mechanical)

    return speed


def simulate_heater(vin, dt, tau=0.05):

    temperature = np.zeros_like(vin)

    for i in range(1, len(vin)):

        temperature[i] = temperature[i - 1] + (
            vin[i] - temperature[i - 1]
        ) * (dt / tau)

    return temperature


def simulate_buzzer(vin, threshold=2.5):

    return np.where(
        vin > threshold,
        1.0,
        0.0
    )


# =============================================================================
# DEVICE RESPONSE ROUTER
# =============================================================================

def get_device_response(device, vin, dt):

    if device == "capacitor":
        return simulate_rc(vin, dt)

    elif device == "inductor":
        return simulate_rl(vin, dt)

    elif device == "led":
        return simulate_led(vin)

    elif device == "diode":
        return simulate_diode(vin, dt)

    elif device == "zener":
        return simulate_zener(vin, dt)

    elif device == "transistor":
        return simulate_transistor(vin, dt)

    elif device == "motor":
        return simulate_motor(vin, dt)

    elif device == "heater":
        return simulate_heater(vin, dt)

    elif device == "buzzer":
        return simulate_buzzer(vin)

    else:
        raise ValueError("Unknown device")


# =============================================================================
# METRICS
# =============================================================================

def compute_metrics(signal):

    return {
        "Mean": float(np.mean(signal)),
        "RMS": float(np.sqrt(np.mean(signal ** 2))),
        "Min": float(np.min(signal)),
        "Max": float(np.max(signal))
    }


# =============================================================================
# EXPORT CSV
# =============================================================================

def export_csv(t, y, filename="pwm_output.csv"):

    buffer = StringIO()

    buffer.write("time,signal\n")

    for ti, yi in zip(t, y):
        buffer.write(f"{ti},{yi}\n")

    b64 = base64.b64encode(
        buffer.getvalue().encode()
    ).decode()

    return f'''
    <a href="data:file/csv;base64,{b64}"
       download="{filename}">
       Download CSV
    </a>
    '''


# =============================================================================
# ARDUINO CODE GENERATOR
# =============================================================================

def generate_arduino_code(duty_cycle, pin):

    pwm_value = int(
        np.clip(duty_cycle, 0, 100) / 100 * 255
    )

    return f"""
int pwmPin = {pin};

void setup()
{{
    pinMode(pwmPin, OUTPUT);
}}

void loop()
{{
    analogWrite(pwmPin, {pwm_value});
}}
"""


# =============================================================================
# PLOT
# =============================================================================

def plot_waveforms(t, pwm, output):

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(t, pwm,
            linestyle="--",
            label="PWM Input")

    ax.plot(t, output,
            linewidth=2,
            label="Device Output")

    ax.set_title("PWM vs Device Response")

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage / Response")

    ax.grid(True)

    ax.legend()

    return fig


# =============================================================================
# SMART INSIGHTS
# =============================================================================

def generate_insights(device, frequency, duty_cycle):

    insights = []

    if duty_cycle < 10:
        insights.append("Very low duty cycle.")

    elif duty_cycle > 90:
        insights.append("Near DC operation.")

    if frequency < 50:
        insights.append("Low frequency may cause ripple/flicker.")

    elif frequency > 10000:
        insights.append("High frequency gives smoother response.")

    if device == "capacitor":
        insights.append("Capacitor smooths PWM waveform.")

    elif device == "inductor":
        insights.append("Inductor current ramps gradually.")

    elif device == "motor":
        insights.append("Motor inertia smooths speed changes.")

    elif device == "heater":
        insights.append("Thermal inertia causes slow response.")

    return insights


# =============================================================================
# KNOWLEDGE BASE
# =============================================================================

KNOWLEDGE_BASE = [
    {
        "topic": "pwm",
        "text": "PWM controls average power using ON/OFF switching."
    },
    {
        "topic": "motor",
        "text": "Motor speed depends on average voltage and inertia."
    },
    {
        "topic": "capacitor",
        "text": "Capacitors smooth PWM into DC-like voltage."
    },
    {
        "topic": "inductor",
        "text": "Inductors resist sudden current changes."
    },
    {
        "topic": "heater",
        "text": "Heaters respond slowly due to thermal mass."
    }
]


# =============================================================================
# AI CHATBOT
# =============================================================================

_kb_texts = [x["text"] for x in KNOWLEDGE_BASE]


@st.cache_resource
def load_model():

    if not _HAS_SENTENCE_TRANSFORMERS:
        return None

    return SentenceTransformer(
        "all-MiniLM-L6-v2"
    )


_model = load_model()


@st.cache_resource
def load_embeddings():

    if _model is None:
        return None

    return _model.encode(
        _kb_texts,
        normalize_embeddings=True
    )


_kb_embeddings = load_embeddings()


def get_chat_response(query):

    if _model is None or _kb_embeddings is None:

        return (
            "Semantic AI features are unavailable "
            "because sentence_transformers "
            "is not installed."
        )

    q_emb = _model.encode(
        [query],
        normalize_embeddings=True
    )

    scores = cosine_similarity(
        q_emb,
        _kb_embeddings
    )[0]

    idx = int(np.argmax(scores))

    return KNOWLEDGE_BASE[idx]["text"]


# =============================================================================
# SIDEBAR CONTROLS
# =============================================================================

st.sidebar.header("PWM Controls")

frequency = st.sidebar.slider(
    "Frequency (Hz)",
    1,
    20000,
    DEFAULT_FREQUENCY
)

duty_cycle = st.sidebar.slider(
    "Duty Cycle (%)",
    0,
    100,
    DEFAULT_DUTY_CYCLE
)

time_window = st.sidebar.slider(
    "Time Window (s)",
    0.001,
    0.5,
    DEFAULT_TIME_WINDOW
)

device = st.sidebar.selectbox(
    "Device",
    [
        "capacitor",
        "inductor",
        "led",
        "diode",
        "zener",
        "transistor",
        "motor",
        "heater",
        "buzzer"
    ]
)

pin = st.sidebar.selectbox(
    "PWM Pin",
    [3, 5, 6, 9, 10, 11]
)


# =============================================================================
# SIMULATION
# =============================================================================

t, pwm, dt = generate_pwm_signal(
    duty_cycle,
    frequency,
    time_window
)

output = get_device_response(
    device,
    pwm,
    dt
)

metrics = compute_metrics(output)


# =============================================================================
# OUTPUT DISPLAY
# =============================================================================

st.subheader("📈 Waveform Output")

st.pyplot(
    plot_waveforms(t, pwm, output)
)

st.markdown(
    export_csv(t, output),
    unsafe_allow_html=True
)


# =============================================================================
# METRICS DISPLAY
# =============================================================================

st.subheader("📊 Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Mean", f"{metrics['Mean']:.2f}")
col2.metric("RMS", f"{metrics['RMS']:.2f}")
col3.metric("Min", f"{metrics['Min']:.2f}")
col4.metric("Max", f"{metrics['Max']:.2f}")


# =============================================================================
# INSIGHTS
# =============================================================================

st.subheader("🧠 Smart Insights")

for insight in generate_insights(
    device,
    frequency,
    duty_cycle
):
    st.write("•", insight)


# =============================================================================
# ARDUINO CODE
# =============================================================================

st.subheader("🔌 Arduino PWM Code")

st.code(
    generate_arduino_code(
        duty_cycle,
        pin
    ),
    language="cpp"
)


# =============================================================================
# CHATBOT UI
# =============================================================================

st.subheader("🤖 PWM AI Assistant")

query = st.text_input(
    "Ask about PWM/devices:"
)

if query:

    response = get_chat_response(query)

    st.success(response)


# =============================================================================
# DEVICE ANIMATION
# =============================================================================

st.subheader("🎞 Device Animation")

if st.button("Run Animation"):

    placeholder = st.empty()

    norm = (
        output - np.min(output)
    ) / (
        np.max(output) - np.min(output) + 1e-9
    )

    for v in norm[::max(1, len(norm)//100)]:

        if device == "led":

            intensity = int(v * 255)

            placeholder.markdown(
                f"""
                <div style="
                width:120px;
                height:120px;
                border-radius:50%;
                margin:auto;
                background-color:
                rgb({intensity},{intensity},0);
                ">
                </div>
                """,
                unsafe_allow_html=True
            )

        elif device == "motor":

            placeholder.metric(
                "Motor Speed",
                f"{int(v*100)} %"
            )

        elif device == "heater":

            placeholder.metric(
                "Temperature",
                f"{int(v*100)} °C"
            )

        elif device == "buzzer":

            state = "ON 🔊" if v > 0.5 else "OFF 🔇"

            placeholder.metric(
                "Buzzer",
                state
            )

        elif device == "capacitor":

            placeholder.progress(float(v))

        elif device == "inductor":

            placeholder.metric(
                "Current",
                f"{int(v*100)} %"
            )

        elif device == "diode":

            state = (
                "Conducting"
                if v > 0.1
                else "Blocking"
            )

            placeholder.metric(
                "Diode",
                state
            )

        elif device == "zener":

            state = (
                "Clamped"
                if v > 0.8
                else "Normal"
            )

            placeholder.metric(
                "Zener",
                state
            )

        elif device == "transistor":

            state = (
                "ON"
                if v > 0.5
                else "OFF"
            )

            placeholder.metric(
                "Transistor",
                state
            )

        time.sleep(0.01)
if st.button("Run Animation"):

    animate_device(device, output)
