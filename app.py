import streamlit as st
from PIL import Image
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.tavily import TavilyTools
from constants import SYSTEM_PROMPT, INSTRUCTIONS
import os
from dotenv import load_dotenv
import tempfile
import requests
from io import BytesIO

# Load environment variables
load_dotenv()

# Initialize Agno Agent
agent = Agent(
    model=Gemini(id="gemini-2.0-flash-exp", api_key=st.secrets["GEMINI_API_KEY"]),
    tools=[TavilyTools()],
    markdown=True,
    description=SYSTEM_PROMPT,
    instructions=INSTRUCTIONS
)

# Streamlit App UI
st.set_page_config(page_title="AI Image Ingredient Analyzer", layout="centered")
st.title("📷 AI Image Ingredient Analyzer")
st.markdown("Upload an image or enter an image URL to analyze it using AI.")

# Inputs
uploaded_image = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
image_url = st.text_input("Or enter Image URL")

# Button to trigger analysis
if st.button("Analyze Image"):
    if uploaded_image:
        # Save uploaded image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            image = Image.open(uploaded_image)
            image.save(tmp_file.name)
            tmp_path = tmp_file.name

        # Analyze image
        response = agent.run("Analyze the product image", images=[{"filepath": tmp_path}])
        os.remove(tmp_path)

        st.markdown("### 🧠 Analysis Result")
        st.write(response.content)

    elif image_url:
        try:
            # Test if URL is reachable and is an image
            response = requests.get(image_url)
            if response.status_code == 200:
                img_bytes = BytesIO(response.content)
                image = Image.open(img_bytes)
                st.image(image, caption="Image from URL", use_column_width=True)

                response = agent.run("Analyze the product image", images=[{"url": image_url}])
                st.markdown("### 🧠 Analysis Result")
                st.write(response.content)
            else:
                st.error("Could not retrieve image from URL. Please check the link.")
        except Exception as e:
            st.error(f"Error fetching image: {e}")

    else:
        st.warning("Please upload an image or provide an image URL.")
