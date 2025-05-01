import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv
import tempfile
import re
import matplotlib.pyplot as plt
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.badges import badge
from streamlit_extras.stylable_container import stylable_container
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.tavily import TavilyTools
from constants import SYSTEM_PROMPT, INSTRUCTIONS

# Load environment
load_dotenv()

# Initialize session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result' not in st.session_state:
    st.session_state.result = None
if 'image_path' not in st.session_state:
    st.session_state.image_path = None

# Setup agent
agent = Agent(
    model=Claude(id="claude-3-5-haiku-20241022", api_key=st.secrets["ANTHROPIC_API_KEY"]),
    tools=[TavilyTools()],
    markdown=True,
    description=SYSTEM_PROMPT,
    instructions=INSTRUCTIONS
)

# Page config
st.set_page_config(page_title="📷 AI Ingredient Analyzer", layout="wide")

# Custom CSS styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .card { background-color: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #6c5ce7; }
    .title-text { color: white; font-weight: 700; text-align: center; margin-bottom: 30px; }
    .divider { border-top: 2px solid #333; margin: 15px 0; }
    .stButton>button { background-color: #6c5ce7 !important; color: white !important; border: none; border-radius: 8px; transition: all 0.3s; }
    .param-bar { height: 8px; border-radius: 4px; background: linear-gradient(90deg, #6c5ce7, #a29bfe); margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# App Title
st.markdown("<h1 class='title-text'>🔍 AI Ingredient Analyzer</h1>", unsafe_allow_html=True)

# Layout columns
left_col, right_col = st.columns([1, 2])

# Optimize image function
def optimize_image(image, max_size=800):
    width, height = image.size
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * max_size / width)
        else:
            new_height = max_size
            new_width = int(width * max_size / height)
        return image.resize((new_width, new_height), Image.LANCZOS)
    return image

# Extract scores for parameter breakdown
def extract_scores(breakdown_text):
    params = {}
    matches = re.findall(r'- (.*?): (\d)', breakdown_text)
    for param, score in matches:
        params[param.strip()] = int(score)
    return params

# Plotting function
def plot_parameter_scores(scores):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8,4), facecolor='#1e1e1e')
    colors = ['#6c5ce7', '#a29bfe', '#74b9ff', '#55efc4', '#ffeaa7']
    bars = ax.barh(list(scores.keys()), list(scores.values()), color=colors)
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{width}', va='center', ha='left', color='white')
    ax.set_xlim(0,5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#6c5ce7')
    ax.spines['left'].set_color('#6c5ce7')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    plt.tight_layout()
    return fig

# Risk extractor
def extract_risks(text_block, risk_type):
    pattern = rf"{risk_type} (.*)"
    match = re.search(pattern, text_block)
    if match:
        risks = [risk.strip() for risk in match.group(1).split(',')]
        return risks
    return []

# Upload section
with left_col:
    with stylable_container(
        key="upload-box",
        css_styles="""
        border: 2px dashed #6c5ce7;
        padding: 2rem;
        border-radius: 20px;
        background-color: #1e1e1e;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        """
    ):
        st.header("📤 Upload Image", divider="rainbow")
        uploaded_image = st.file_uploader("", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        analyze_button = st.button("🔍 Analyze Ingredients", use_container_width=True, type="primary")

# Main Logic
if analyze_button and uploaded_image:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        image = optimize_image(Image.open(uploaded_image))
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image.save(tmp_file.name, format='JPEG')
        st.session_state.image_path = tmp_file.name

    with st.spinner("🔍 Analyzing ingredients, please wait..."):
        try:
            response = agent.run("Analyze the product image", images=[{"filepath": st.session_state.image_path}])
            st.session_state.result = response.content
        except Exception as e:
            st.session_state.result = f"❌ Error during analysis: {str(e)}"
        finally:
            if os.path.exists(st.session_state.image_path):
                os.remove(st.session_state.image_path)

# Right side display
with right_col:
    content = st.session_state.result

    if st.session_state.processing:
        st.markdown("""
        <div class="card">
            <h3 style="color: #a29bfe;">🔄 Analysis in progress...</h3>
        </div>
        """, unsafe_allow_html=True)
    
    elif content:
        detected = re.search(r'📸 Detected: (.+)', content)
        if detected:
            st.markdown(f"""
            <div class="card">
                <h3 style="color: #a29bfe;">🔍 Product Identification</h3>
                <p style="font-size: 1.1em; color: white;">Detected: <strong style="color: #6c5ce7;">{detected.group(1)}</strong></p>
            </div>
            """, unsafe_allow_html=True)

        # Parameter Breakdown Section
        breakdown_text = re.search(r'🔍 Breakdown:(.+?)🚨', content, re.DOTALL)
        if breakdown_text:
            scores = extract_scores(breakdown_text.group(1))
            st.markdown("""
            <div class="card">
                <h3 style="color: #a29bfe;">📊 Ingredient Analysis</h3>
            """, unsafe_allow_html=True)
            for param, score in scores.items():
                st.markdown(f"""
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <span style="color: white;">{param}</span>
                        <span style="color: #a29bfe;">{score}/5</span>
                    </div>
                    <div class="param-bar" style="width: {score*20}%;"></div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            fig = plot_parameter_scores(scores)
            st.pyplot(fig)

        # Risk Assessment Section
        st.markdown("""
        <div class="card">
            <h3 style="color: #a29bfe;">⚠️ Safety Assessment</h3>
        """, unsafe_allow_html=True)
        high_risks = extract_risks(content, "🚨 High-Risk:")
        moderate_risks = extract_risks(content, "⚠️ Moderate Risk:")
        low_risks = extract_risks(content, "✅ Low Risk:")
        if high_risks:
            st.error(f"**🚨 High-Risk Ingredients:** {', '.join(high_risks)}")
        if moderate_risks:
            st.warning(f"**⚠️ Moderate Risk Ingredients:** {', '.join(moderate_risks)}")
        if low_risks:
            st.success(f"**✅ Safe Ingredients:** {', '.join(low_risks)}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Full Report
        st.markdown("---")
        st.header("📝 View Full Analysis Report")
        st.markdown(content, unsafe_allow_html=True)

    elif uploaded_image and not st.session_state.processing:
        st.info("Click 'Analyze Ingredients' to start the analysis.")
    elif not uploaded_image:
        st.info("Please upload an image to begin analysis.")