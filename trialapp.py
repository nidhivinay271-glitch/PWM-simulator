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


def simulate_heater(vin, dt):

    heater = np.zeros_like(vin)

    alpha_heat = 0.03
    alpha_cool = 0.01

    for i in range(1, len(vin)):

        if vin[i] > 0:

            # Heat rises slowly
            heater[i] = heater[i - 1] + (
                80 - heater[i - 1]
            ) * alpha_heat

        else:

            # Cool slowly
            heater[i] = heater[i - 1] - (
                heater[i - 1] - 25
            ) * alpha_cool

    return heater

def simulate_buzzer(vin, dt, threshold=2.5):

    # Digital buzzer behavior
    tone = np.where(
        vin > threshold,
        1.0,
        0.0
    )

    # Add slight ringing effect
    out = np.zeros_like(vin)

    for i in range(1, len(vin)):

        out[i] = out[i - 1] + (
            tone[i] - out[i - 1]
        ) * 0.4

    return out


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
        return simulate_buzzer(vin, dt)

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

def generate_insights(device, frequency, duty_cycle, metrics):

    insights = []
    recommendations = []

    # =========================================================
    # DUTY CYCLE STATUS
    # =========================================================

    if duty_cycle < 30:
        level = "🟢 LOW"
    elif duty_cycle < 70:
        level = "🟡 MEDIUM"
    else:
        level = "🔴 HIGH"

    insights.append(f"Duty Cycle Level: {level}")
    insights.append(f"Operating Frequency: {frequency} Hz")

    # =========================================================
    # DEVICE SPECIFIC INSIGHTS
    # =========================================================

    if device == "led":

        brightness = duty_cycle

        insights.append(
            f"LED Brightness ≈ {brightness:.0f}%"
        )

        if duty_cycle < 20:
            recommendations.append("🟢 Dim LED operation")
        elif duty_cycle < 80:
            recommendations.append("🟡 Normal brightness")
        else:
            recommendations.append("🔴 Very high brightness → heating possible")

        if frequency < 100:
            recommendations.append("🔴 Visible LED flicker likely")
        else:
            recommendations.append("🟢 Smooth LED brightness")

    # =========================================================

    elif device == "motor":

        speed = duty_cycle

        insights.append(
            f"Estimated Motor Speed ≈ {speed:.0f}%"
        )

        if duty_cycle < 25:
            recommendations.append("🟢 Low speed operation")
        elif duty_cycle < 75:
            recommendations.append("🟡 Moderate motor speed")
        else:
            recommendations.append("🔴 High speed → increased current draw")

        if frequency < 50:
            recommendations.append("🔴 Motor may jerk or vibrate")
        else:
            recommendations.append("🟢 Smooth motor rotation expected")

    # =========================================================

    elif device == "heater":

        heat = duty_cycle

        insights.append(
            f"Estimated Heating Power ≈ {heat:.0f}%"
        )

        if duty_cycle < 30:
            recommendations.append("🟢 Low heating")
        elif duty_cycle < 70:
            recommendations.append("🟡 Moderate heating")
        else:
            recommendations.append("🔴 High temperature operation")

        recommendations.append(
            "🟡 Heater response is slow due to thermal inertia"
        )

    # =========================================================

    elif device == "capacitor":

        insights.append(
            "Capacitor smooths PWM into analog-like voltage"
        )

        if frequency < 100:
            recommendations.append("🔴 Ripple voltage may be high")
        elif frequency < 1000:
            recommendations.append("🟡 Moderate filtering")
        else:
            recommendations.append("🟢 Strong smoothing effect")

    # =========================================================

    elif device == "inductor":

        insights.append(
            "Inductor resists sudden current changes"
        )

        if frequency < 100:
            recommendations.append("🔴 Current ripple may be large")
        elif frequency < 1000:
            recommendations.append("🟡 Moderate ripple current")
        else:
            recommendations.append("🟢 Smooth inductor current")

    # =========================================================

    elif device == "diode":

        insights.append(
            "Diode allows one-direction current flow"
        )

        if duty_cycle < 20:
            recommendations.append("🟢 Low conduction interval")
        elif duty_cycle < 80:
            recommendations.append("🟡 Normal rectification")
        else:
            recommendations.append("🔴 High average diode current")

    # =========================================================

    elif device == "zener":

        insights.append(
            "Zener regulates voltage near breakdown level"
        )

        if duty_cycle < 30:
            recommendations.append("🟢 Light regulation load")
        elif duty_cycle < 70:
            recommendations.append("🟡 Stable regulation")
        else:
            recommendations.append("🔴 High zener power dissipation")

    # =========================================================

    elif device == "transistor":

        insights.append(
            "Transistor operates as PWM electronic switch"
        )

        if duty_cycle < 20:
            recommendations.append("🟢 Low switching activity")
        elif duty_cycle < 80:
            recommendations.append("🟡 Efficient switching region")
        else:
            recommendations.append("🔴 High conduction time → heating possible")

        if frequency > 10000:
            recommendations.append("🟡 Switching losses may increase")

    # =========================================================

    elif device == "buzzer":

        insights.append(
            "Buzzer converts PWM into audible sound"
        )

        if frequency < 100:
            recommendations.append("🔴 Clicking sound likely")
        elif frequency < 5000:
            recommendations.append("🟢 Audible tone region")
        else:
            recommendations.append("🟡 Frequency may exceed hearing range")

        if duty_cycle < 20:
            recommendations.append("🟢 Low sound intensity")
        elif duty_cycle < 80:
            recommendations.append("🟡 Moderate sound level")
        else:
            recommendations.append("🔴 Very loud buzzer operation")

    # =========================================================
    # COMMON METRICS
    # =========================================================

    insights.append(f"Mean Output: {metrics['mean']:.2f}")
    insights.append(f"RMS Output: {metrics['rms']:.2f}")

    # =========================================================
    # FINAL FORMAT
    # =========================================================

    final_output = []

    final_output.append("📊 SMART INSIGHTS")
    final_output.extend(insights)

    final_output.append("")
    final_output.append("⚡ RECOMMENDATIONS")
    final_output.extend(recommendations)

    return final_output


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

# =============================================================================
# DEVICE ANIMATION
# =============================================================================

st.subheader("🎞 Device Animation")

if st.button(
    "Run Animation",
    key="run_animation_button"
):

    placeholder = st.empty()

    norm = (
        output - np.min(output)
    ) / (
        np.max(output) - np.min(output) + 1e-9
    )

    max_frames = 120

    step = max(
        1,
        len(norm) // max_frames
    )

    for v in norm[::step]:

        # =========================================================
        # LED
        # =========================================================

        if device == "led":

            glow = int(50 + v * 205)

            size = 80 + int(v * 40)

            html = f"""
            <div style="
                text-align:center;
                font-size:{size}px;
                filter: drop-shadow(
                    0 0 {20*v}px
                    rgb(255,255,0)
                );
            ">
                💡
            </div>

            <h3 style="
                text-align:center;
                color:rgb({glow},{glow},0);
            ">
                Brightness: {int(v*100)}%
            </h3>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # MOTOR
        # =========================================================

        elif device == "motor":

            bars = int(v * 10)

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*40)}px;
                transform: rotate({v*360}deg);
                transition: 0.05s linear;
            ">
                ⚙️
            </div>

            
            <p>{int(v*100)} % RPM</p>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # HEATER
        # =========================================================

        elif device == "heater":

            red = int(100 + v * 155)

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*20)}px;
            ">
                🔥
            </div>

            <h2 style="
                color:rgb({red},50,0);
            ">
                Temperature
            </h2>

            <h3>
                {int(v*300)} °C
            </h3>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # BUZZER
        # =========================================================

        elif device == "buzzer":

            state = "🔊" if v > 0.5 else "🔈"

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*30)}px;
            ">
                {state}
            </div>

            <h2>
                Sound Level
            </h2>

            <h3>
                {int(v*100)} %
            </h3>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # CAPACITOR
        # =========================================================

        elif device == "capacitor":

            fill = int(v * 100)

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{70 + int(v*20)}px;
            ">
                🔋
            </div>

            <h2>
                Charge Level
            </h2>

            <div style="
                width:300px;
                height:30px;
                margin:auto;
                border:2px solid white;
                border-radius:10px;
            ">

            <div style="
                width:{fill}%;
                height:100%;
                background:lime;
                border-radius:8px;
            "></div>

            </div>

            <h3>{fill}%</h3>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # INDUCTOR
        # =========================================================

        elif device == "inductor":

            waves = int(v * 8)

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*20)}px;
            ">
                🌀
            </div>

            <h2>
                Magnetic Field
            </h2>

            <h3>
                {'➰'*waves}
            </h3>

            <p>
                Current: {int(v*100)}%
            </p>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # DIODE
        # =========================================================

        elif device == "diode":

            state = (
                "Conducting ✅"
                if v > 0.2
                else "Blocking ❌"
            )

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:90px;
            ">
                ➡️
            </div>

            <h2>{state}</h2>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # ZENER
        # =========================================================

        elif device == "zener":

            state = (
                "Voltage Clamped ⚡"
                if v > 0.7
                else "Normal"
            )

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*20)}px;
            ">
                ⚡
            </div>

            <h2>{state}</h2>

            <p>
                Regulation: {int(v*100)}%
            </p>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        # =========================================================
        # TRANSISTOR
        # =========================================================

        elif device == "transistor":

            state = (
                "ON 🟢"
                if v > 0.5
                else "OFF 🔴"
            )

            html = f"""
            <div style="text-align:center;">

            <div style="
                font-size:{80 + int(v*15)}px;
            ">
                🔀
            </div>

            <h2>{state}</h2>

            <p>
                Switching Level:
                {int(v*100)}%
            </p>

            </div>
            """

            placeholder.markdown(
                html,
                unsafe_allow_html=True
            )

        time.sleep(0.02)
