import streamlit as st
from PIL import Image
import os
from dotenv import load_dotenv
import tempfile
import re
import matplotlib.pyplot as plt

# Load environment
load_dotenv()

# Initialise session state
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'result' not in st.session_state:
    st.session_state.result = None
if 'image_path' not in st.session_state:
    st.session_state.image_path = None

# Placeholder for agent logic due to missing dependencies
def dummy_agent_run(prompt, images):
    return {
        "content": (
            "Formalist Analysis: Use of line and form is confident, yet restrained.\n"
            "Iconographical Analysis: The image references classical motifs subtly.\n"
            "Iconological Analysis: A meditation on memory and decay emerges.\n"
            "Semiotic Analysis: Visual codes hint at rupture, cultural slippage.\n"
            "Semantic Analysis: The meaning resists singular interpretation.\n"
            "Critical Summary: While fragmentary, the image constructs a slow, reflective politics of seeing."
        )
    }

# Page config
st.set_page_config(page_title="📷 AI Visual Analyser", layout="wide")

# Custom CSS styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .card { background-color: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #6c5ce7; }
    .title-text { color: white; font-weight: 700; text-align: center; margin-bottom: 10px; }
    .subtitle-text { color: #a29bfe; text-align: center; margin-bottom: 30px; font-size: 0.9em; }
    .divider { border-top: 2px solid #333; margin: 15px 0; }
    .stButton>button { background-color: #6c5ce7 !important; color: white !important; border: none; border-radius: 8px; transition: all 0.3s; }
    .param-bar { height: 8px; border-radius: 4px; background: linear-gradient(90deg, #6c5ce7, #a29bfe); margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# App Title
st.markdown("<h1 class='title-text'>📷 AI Visual Analyser</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle-text'>Forked and developed by Rahul Bhattacharya as a part of dotai + theblackyellowarrow experiments to make AI contextual</div>", unsafe_allow_html=True)

# Layout columns
left_col, right_col = st.columns([1, 2])

# Image optimiser
def optimise_image(image, max_size=800):
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

# Score extractor
def extract_scores(text):
    analysis = {}
    for category in ["Formalist", "Iconographical", "Iconological", "Semiotic", "Semantic"]:
        match = re.search(rf"{category} Analysis:\s*(.*?)(?:\n|$)", text, re.DOTALL)
        if match:
            analysis[category + " Analysis"] = match.group(1).strip()
        else:
            analysis[category + " Analysis"] = "No analysis found."
    summary_match = re.search(r"Critical Summary:\s*(.*)", text, re.DOTALL)
    if summary_match:
        analysis["Critical Summary"] = summary_match.group(1).strip()
    else:
        analysis["Critical Summary"] = "No summary provided."
    return analysis

# Upload section
with left_col:
    st.markdown("""
        <div style='border: 2px dashed #6c5ce7; padding: 2rem; border-radius: 20px; background-color: #1e1e1e; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.3);'>
    """, unsafe_allow_html=True)
    st.header("📤 Upload Image", divider="rainbow")
    uploaded_image = st.file_uploader("", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    analyze_button = st.button("🔍 Analyse Your Image", use_container_width=True, type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

# Main logic
if analyze_button and uploaded_image:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        image = optimise_image(Image.open(uploaded_image))
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image.save(tmp_file.name, format='JPEG')
        st.session_state.image_path = tmp_file.name

    with st.spinner("🔍 Analysing visual content, please wait..."):
        try:
            prompt = (
                "Please perform a detailed visual analysis in British English under the following five categories: "
                "Formalist Analysis, Iconographical Analysis, Iconological Analysis, Semiotic Analysis, and Semantic Analysis. "
                "Conclude with a Critical Summary that synthesises the insights."
            )
            response = dummy_agent_run(prompt, images=[{"filepath": st.session_state.image_path}])
            st.session_state.result = response["content"]
        except Exception as e:
            st.session_state.result = f"❌ Error during analysis: {str(e)}"
        finally:
            if os.path.exists(st.session_state.image_path):
                os.remove(st.session_state.image_path)

# Display results
with right_col:
    if st.session_state.result:
        analysis = extract_scores(st.session_state.result)
        for title, insight in analysis.items():
            st.markdown(f"""
            <div class="card">
                <h3 style="color: #a29bfe;">🔍 {title}</h3>
                <p style="font-size: 1.1em; color: white;">{insight}</p>
            </div>
            """, unsafe_allow_html=True)
    elif uploaded_image:
        st.info("Click 'Analyse Your Image' to begin.")
    else:
        st.info("Please upload an image to start.")
