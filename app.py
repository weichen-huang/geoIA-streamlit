import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import cv2
import hashlib
import time
import os

# Function to convert the canvas drawing to a binary mask
def canvas_to_mask(canvas_result, img_shape):
    if canvas_result is not None and canvas_result.image_data is not None:
        canvas_image_data = np.array(canvas_result.image_data)
        mask = cv2.cvtColor(canvas_image_data, cv2.COLOR_RGBA2GRAY)
        mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.resize(mask, (img_shape[1], img_shape[0]))
        return mask
    else:
        return None

# Function to fill enclosed areas in the binary mask
def fill_enclosed_areas(mask):
    filled_mask = mask.copy()
    h, w = filled_mask.shape[:2]
    flood_fill_mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(filled_mask, flood_fill_mask, (0, 0), 255)
    filled_mask_inv = cv2.bitwise_not(filled_mask)
    filled_foreground = mask | filled_mask_inv
    return filled_foreground

def generate_short_hash():
    current_time = str(time.time())
    sha256_hash = hashlib.sha256(current_time.encode()).hexdigest()
    short_hash = sha256_hash[:6]

    return short_hash

# Function to calculate the mean mask from all masks in the data folder
def calculate_mean_mask(mask_folder):
    mask_list = []
    for filename in os.listdir(mask_folder):
        if filename.endswith('.png'):
            mask_path = os.path.join(mask_folder, filename)
            mask_image = Image.open(mask_path).convert('L')  # convert to grayscale
            mask_array = np.array(mask_image)
            mask_list.append(mask_array)
    if mask_list:
        # Stack mask arrays and calculate the mean along the stack
        mean_mask = np.mean(np.stack(mask_list), axis=0).astype(np.uint8)
        return mean_mask
    else:
        return None

# Function to overlay the mean mask onto the base image
def overlay_mask(base_image_path, mean_mask):
    base_image = Image.open(base_image_path).convert('RGBA')
    mean_mask_image = Image.fromarray(mean_mask)
    mean_mask_image = mean_mask_image.resize(base_image.size, resample=Image.BILINEAR)
    mask_rgba = Image.merge('RGBA', (mean_mask_image, mean_mask_image, mean_mask_image, mean_mask_image))
    final_image = Image.composite(mask_rgba, base_image, mean_mask_image)
    return final_image

st.title("IB Geo IA Survey")

# Upload an image


image = Image.open("img/map.png").convert("RGB")
img_array = np.array(image)
width = st.slider('Stroke width', 0, 20, 5)

# Create a canvas for drawing
st.subheader("Highlight the central business district area:")
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.7)",  # Use an orange, semi-transparent fill
    stroke_width=width,
    stroke_color="rgba(255, 165, 0, 0.7)",
    background_image=Image.open("img/map.png"),
    update_streamlit=True,
    height=img_array.shape[0],
    width=img_array.shape[1],
    drawing_mode="freedraw",
    key="canvas",
)

if st.button("Save"):

    mask = canvas_to_mask(canvas_result, img_array.shape)
    if mask is not None:
        mask = fill_enclosed_areas(mask)
        cv2.imwrite(f"data/{generate_short_hash()}.png", mask)
    else:
        st.warning("Please draw on the image.")

if st.button("Aggregate data"):

    mean_mask = calculate_mean_mask("data")

    if mean_mask is not None:
        final_image = overlay_mask("img/map.png", mean_mask)

        st.image(final_image, caption='Where most people think the CBD is', use_column_width=True)

        st.download_button(
            label="Download Image",
            data=final_image.tobytes(),
            file_name="final_overlay.png",
            mime="image/png"
        )
    else:
        st.warning("No saved data found in the data folder.")