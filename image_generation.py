import tk as tk
import customtkinter as ctk  # type: ignore
import torch
from torch import autocast
from diffusers import StableDiffusionPipeline
from PIL import ImageTk
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import random

# Hugging Face Token (replace with your own token)
from authtoken import auth_token # type: ignore

# Load Stable Diffusion model from Hugging Face
pipe = StableDiffusionPipeline.from_pretrained(
    "CompVis/stable-diffusion-v1-4", 
    use_auth_token=auth_token
)
pipe.to("cuda" if torch.cuda.is_available() else "cpu")


# ----------- Option 1: Tkinter GUI for Text-to-Image Generation -----------

def generate_image_tkinter():
    """Function to generate an image from the Tkinter GUI text input"""
    with autocast("cuda" if torch.cuda.is_available() else "cpu"):
        image = pipe(prompt.get()).images[0]
    
    # Save the generated image
    image.save('generated_image.png')

    # Display the image on the Tkinter GUI
    img = ImageTk.PhotoImage(image)
    img_placeholder.configure(image=img)
    img_placeholder.image = img  # Keep reference to prevent garbage collection


# Initialize the Tkinter app window
def start_tkinter_gui():
    app = tk.Tk()
    app.geometry("532x632")
    app.title("Text to Image app")
    app.configure(bg='black')
    ctk.set_appearance_mode("dark")

    # Create input field for the text prompt
    global prompt
    prompt = ctk.CTkEntry(height=40, width=512, text_font=("Arial", 15), text_color="white", fg_color="black") 
    prompt.place(x=10, y=10)

    # Placeholder for displaying the generated image
    global img_placeholder
    img_placeholder = ctk.CTkLabel(height=512, width=512, text="")
    img_placeholder.place(x=10, y=110)

    # Button to trigger image generation
    trigger = ctk.CTkButton(height=40, width=120, text_font=("Arial", 15), text_color="black", fg_color="white", command=generate_image_tkinter)
    trigger.place(x=206, y=60)

    # Start the Tkinter event loop
    app.mainloop()


# ----------- Option 2: Streamlit Web App for Text-to-Image Generation -----------

def generate_image_streamlit():
    """Function to generate an image in Streamlit"""
    prompt = st.text_input("Enter a text prompt:")
    
    if prompt:
        with st.spinner("Generating image..."):
            image = pipe(prompt).images[0]
            
            # Display the generated image
            st.image(image, caption=f"Generated Image for: {prompt}")
            
            # Optionally save the image
            image.save("generated_image.png")
            st.success("Image saved as 'generated_image.png'.")


# ----------- Option 3: Custom Sunset Image Generator -----------

def generate_sunset_image(description):
    """Function to generate a simple sunset image"""
    width, height = 512, 512
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Background (sunset colors)
    sunset_colors = [(255, 204, 0), (255, 153, 51), (204, 102, 0), (102, 51, 0)]
    draw.rectangle([0, 0, width, height], fill=random.choice(sunset_colors))

    # Draw a sun (simple circle)
    sun_color = (255, 204, 0)
    sun_radius = 50
    draw.ellipse([width//2 - sun_radius, height//2 - sun_radius, width//2 + sun_radius, height//2 + sun_radius], fill=sun_color)

    # Add text description (optional)
    font = ImageFont.load_default()
    draw.text((10, 10), description, fill=(255, 255, 255), font=font)

    return img


# Example usage: Generate and save a sunset image
def generate_sunset_example():
    description = "A beautiful sunset over the ocean."
    image = generate_sunset_image(description)
    image.show()
    image.save("sunset_image.png")


# ----------- Main Execution -----------

if __name__ == "__main__":
    # Uncomment the desired option for running:
    
    # Option 1: Start Tkinter GUI
    # start_tkinter_gui()

    # Option 2: Start Streamlit Web App
    generate_image_streamlit()

    # Option 3: Run sunset image generator (optional for example)
    # generate_sunset_example()

