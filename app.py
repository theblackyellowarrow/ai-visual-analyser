import streamlit as st
# Set page configuration as the first command
st.set_page_config(page_title="📷 AI Ingredient Analyzer", layout="wide")

from PIL import Image
import os
from dotenv import load_dotenv
import tempfile
import re
import matplotlib.pyplot as plt
import time
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Premium UI Imports
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.badges import badge
from streamlit_extras.stylable_container import stylable_container
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.tavily import TavilyTools
from constants import SYSTEM_PROMPT, INSTRUCTIONS

# Load env
load_dotenv()

# Create session state for background processing
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result' not in st.session_state:
    st.session_state.result = None
if 'image_path' not in st.session_state:
    st.session_state.image_path = None

# Initialize Agent with faster model
agent = Agent(
    model=Claude(id="claude-3-5-haiku-20241022", api_key=st.secrets["ANTHROPIC_API_KEY"]),
    tools=[TavilyTools()],
    markdown=True,
    description=SYSTEM_PROMPT,
    instructions=INSTRUCTIONS
)

# Dark Theme CSS
st.markdown("""
<style>
    /* Dark background */
    .stApp {
        background-color: #0e1117;
        color: white;
    }
    
    /* Card styling */
    .card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        border-left: 4px solid #6c5ce7;
    }
    
    /* Text colors */
    .stMarkdown, .stHeader, .stSubheader, .stText {
        color: white !important;
    }
    
    /* Title styling */
    .title-text {
        color: white;
        font-weight: 700;
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* Divider styling */
    .divider {
        border-top: 2px solid #333;
        margin: 15px 0;
    }
    
    /* Input field styling */
    .stFileUploader>div>div {
        background-color: #2d2d2d !important;
        border-color: #444 !important;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #6c5ce7 !important;
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #5649c0 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(108, 92, 231, 0.4);
    }
    
    /* Parameter score bars */
    .param-bar {
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(90deg, #6c5ce7, #a29bfe);
        margin-top: 5px;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e1e1e;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #6c5ce7;
        border-radius: 4px;
    }
    
    /* Plot background */
    .stPlotlyChart, .stPyplot {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.markdown("<h1 class='title-text'>🔍 AI Ingredient Analyzer</h1>", unsafe_allow_html=True)

# Layout columns
left_col, right_col = st.columns([1, 2])

# Function to optimize image size
def optimize_image(image, max_size=800):
    # Resize image while maintaining aspect ratio
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

# Function to analyze image in background
def analyze_in_background(image_path):
    try:
        response = agent.run("Analyze the product image", images=[{"filepath": image_path}])
        st.session_state.result = response.content
    except Exception as e:
        st.session_state.result = f"Error during analysis: {str(e)}"
    
    st.session_state.processing = False
    # Remove temporary file
    if os.path.exists(image_path):
        os.remove(image_path)
    # Trigger rerun to refresh UI with results
    st.rerun()

# Cache for analysis results
@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_cached_analysis(image_hash):
    # This function would normally do the analysis
    # But since it's cached, it will only run once for similar images
    return st.session_state.result

def render_stars(rating_text):
    return "⭐️" * rating_text.count("⭐️")

def extract_scores(breakdown_text):
    params = {}
    matches = re.findall(r'- (.*?): (\d)', breakdown_text)
    for param, score in matches:
        params[param.strip()] = int(score)
    return params

def plot_parameter_scores(scores):
    # Set dark background for the plot
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8,4), facecolor='#1e1e1e')
    
    colors = ['#6c5ce7', '#a29bfe', '#74b9ff', '#55efc4', '#ffeaa7']
    bars = ax.barh(list(scores.keys()), list(scores.values()), color=colors)
    
    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{width}',
                va='center', ha='left', color='white')
    
    ax.set_xlim(0,5)
    ax.set_xlabel('Score (1-5)', color='white')
    ax.set_title('Parameter Scores', color='white', pad=20)
    
    # Customize spines and ticks
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#6c5ce7')
    ax.spines['left'].set_color('#6c5ce7')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    plt.tight_layout()
    return fig

def extract_risks(text_block, risk_type):
    pattern = rf"{risk_type} (.*)"
    match = re.search(pattern, text_block)
    if match:
        risks = [risk.strip() for risk in match.group(1).split(',')]
        return risks
    return []

# Upload section in left column
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
        analyze_button = st.button("🔍 Analyze Ingredients", 
                                 use_container_width=True,
                                 type="primary")

# # Main logic
# if analyze_button:
#     if uploaded_image:
#         if not st.session_state.processing:
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
#                 # Optimize image
#                 image = optimize_image(Image.open(uploaded_image))
                
#                 # Convert image to RGB if it has an alpha channel
#                 if image.mode == 'RGBA':
#                     image = image.convert('RGB')
                
#                 image.save(tmp_file.name, format='JPEG')
#                 st.session_state.image_path = tmp_file.name

# Main logic
if analyze_button and uploaded_image:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        # Optimize and save image
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
            # Remove temporary file
            if os.path.exists(st.session_state.image_path):
                os.remove(st.session_state.image_path)
            
           

# Display loading state or results
with right_col:
    if st.session_state.processing:
        # Show progressive loading feedback
        st.markdown("""
        <div class="card">
            <h3 style="color: #a29bfe;">🔄 Analysis in progress...</h3>
        """, unsafe_allow_html=True)
        
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # Simulate progress updates
        for i in range(10):
            progress_placeholder.progress((i + 1) * 10)
            if i == 2:
                status_placeholder.markdown("🔍 **Detecting product type...**")
            elif i == 5:
                status_placeholder.markdown("📝 **Analyzing ingredients...**")
            elif i == 8:
                status_placeholder.markdown("💡 **Generating recommendations...**")
            time.sleep(0.2)  # Short delay for visual feedback
            
        st.markdown("</div>", unsafe_allow_html=True)
        
    elif st.session_state.result:
        content = st.session_state.result
        
        # Main Analysis Card
        with stylable_container(
            key="analysis-card",
            css_styles="""
            background-color: #1e1e1e;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            border-left: 4px solid #6c5ce7;
            """
        ):
            st.header("🧪 Analysis Results", divider="rainbow")
            
            # Product Info Section
            detected = re.search(r'📸 Detected: (.+)', content)
            if detected:
                st.markdown(f"""
                <div class="card">
                    <h3 style="color: #a29bfe;">🔍 Product Identification</h3>
                    <p style="font-size: 1.1em; color: white;">Detected: <strong style="color: #6c5ce7;">{detected.group(1)}</strong></p>
                </div>
                """, unsafe_allow_html=True)
            
            # Overall Rating Section
            overall_rating = re.search(r'⭐️(.*?)Overall Rating', content)
            if overall_rating:
                stars_display = render_stars(overall_rating.group(1))
                st.markdown(f"""
                <div class="card">
                    <h3 style="color: #a29bfe;">⭐️ Overall Rating</h3>
                    <div style="font-size: 2em; text-align: center; margin: 15px 0; color: #ffeaa7;">
                        {stars_display}
                    </div>
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
                
                # Display parameter scores as progress bars
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
                
                # Add the plot
                st.markdown("""
                <div class="card">
                    <h3 style="color: #a29bfe;">📈 Visual Breakdown</h3>
                """, unsafe_allow_html=True)
                fig = plot_parameter_scores(scores)
                st.pyplot(fig)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Risk Analysis Section
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

        # Full Report Section
        st.markdown("---")
        st.header("📝 View Full Analysis Report")
        st.markdown(content, unsafe_allow_html=True)
    
    elif uploaded_image and not st.session_state.processing:
        st.info("Click 'Analyze Ingredients' to start the analysis.")
    
    elif not uploaded_image:
        st.info("Please upload an image to begin analysis.")