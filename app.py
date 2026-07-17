import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile
import requests
import os
import re

# --- Constants & Helpers ---
AMIRI_FONT_URL = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"

@st.cache_data
def download_font(url):
    try:
        r = requests.get(url, timeout=15)
        return r.content if r.status_code == 200 else None
    except:
        return None

def fix_arabic(text):
    if pd.isna(text) or str(text).strip() == "":
        return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={
        'delete_harakat': False, 
        'support_ligatures': True, 
        'arabic': True
    })
    return get_display(reshaper.reshape(str(text)))

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def smart_transparent(img_pil, mode="Black", threshold=50):
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if mode == "Black":
            if item[0] < threshold and item[1] < threshold and item[2] < threshold:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)
        else: # White mode
            if item[0] > (255-threshold) and item[1] > (255-threshold) and item[2] > (255-threshold):
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)
    img.putdata(new_data)
    return img

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

# --- Page Setup & Sidebar Navigation ---
st.set_page_config(page_title="EPS Production Suite", layout="wide", page_icon="🛡️")

# Sidebar Menu to switch between apps
st.sidebar.title("🛡️ EPS System")
app_mode = st.sidebar.radio("Navigation Menu:", ["📜 Certificate Generator", "📸 Event Photo Framer"])

# Download Font once
fnt_bytes = download_font(AMIRI_FONT_URL)

# --- APP MODE 1: Certificate Generator ---
if app_mode == "📜 Certificate Generator":
    st.title("📜 Certificate Generator")
    
    # Context-specific Sidebar for Certificates
    st.sidebar.divider()
    st.sidebar.subheader("📁 Upload Files")
    tpl_file = st.sidebar.file_uploader("1. Template Image", type=['png', 'jpg', 'jpeg'])
    data_file = st.sidebar.file_uploader("2. Data Sheet", type=['xlsx', 'csv'])
    
    if tpl_file and data_file and fnt_bytes:
        img_info = Image.open(tpl_file)
        W, H = img_info.size
        df = pd.read_excel(data_file) if data_file.name.endswith('.xlsx') else pd.read_csv(data_file)
        cols = df.columns.tolist()

        st.sidebar.divider()
        st.sidebar.subheader("👤 Name Position")
        name_col = st.sidebar.selectbox("Select Name Column", cols)
        n_x = st.sidebar.slider("Name - X", 0, W, W // 2)
        n_y = st.sidebar.slider("Name - Y", 0, H, H // 2)
        n_size = st.sidebar.number_input("Name Font Size", 10, 1000, 100)
        n_color = st.sidebar.color_picker("Name Color", "#002d56")

        st.sidebar.divider()
        show_grade = st.sidebar.checkbox("Add Grade/Rating?")
        if show_grade:
            st.sidebar.subheader("🎓 Grade Position")
            grade_col = st.sidebar.selectbox("Select Grade Column", cols)
            g_x = st.sidebar.slider("Grade - X", 0, W, W // 2)
            g_y = st.sidebar.slider("Grade - Y", 0, H, H // 2 + 150)
            g_size = st.sidebar.number_input("Grade Font Size", 10, 1000, 60)
            g_color = st.sidebar.color_picker("Grade Color", "#333333")

        # Main View
        main_img = Image.open(tpl_file).convert("RGB")
        draw = ImageDraw.Draw(main_img)
        f_name = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
        draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_color), font=f_name, anchor="mm")
        
        if show_grade:
            f_grade = ImageFont.truetype(io.BytesIO(fnt_bytes), g_size)
            draw.text((g_x, g_y), fix_arabic(df.iloc[0][grade_col]), fill=hex_to_rgb(g_color), font=f_grade, anchor="mm")
        
        st.image(main_img, caption="Live Preview - Use the sidebar to adjust", use_container_width=True)
        
        if st.button("🚀 Generate All Certificates"):
            zip_io = io.BytesIO()
            pdf_list = []
            with zipfile.ZipFile(zip_io, "w") as z:
                bar = st.progress(0)
                total = len(df)
                for i, row in df.iterrows():
                    img = Image.open(tpl_file).convert("RGB")
                    d = ImageDraw.Draw(img)
                    d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_color), font=f_name, anchor="mm")
                    if show_grade:
                        d.text((g_x, g_y), fix_arabic(row[grade_col]), fill=hex_to_rgb(g_color), font=f_grade, anchor="mm")
                    
                    img_byte = io.BytesIO()
                    img.save(img_byte, format="JPEG", quality=95)
                    z.writestr(f"Images/{clean_filename(row[name_col])}.jpg", img_byte.getvalue())
                    pdf_list.append(img)
                    bar.progress((i+1)/total)
                
                pdf_io = io.BytesIO()
                pdf_list[0].save(pdf_io, format="PDF", save_all=True, append_images=pdf_list[1:])
                z.writestr("Combined_Certificates.pdf", pdf_io.getvalue())
            
            st.success("✅ Success! Download your package below.")
            st.download_button("📥 Download Package (ZIP)", zip_io.getvalue(), "EPS_Certificates.zip")
    else:
        st.info("👈 Please upload your Template and Data Sheet in the sidebar.")

# --- APP MODE 2: Photo Framer ---
elif app_mode == "📸 Event Photo Framer":
    st.title("📸 Event Photo Framer")
    
    # Context-specific Sidebar for Photo Framer
    st.sidebar.divider()
    st.sidebar.subheader("🖼️ Frame Settings")
    bg_mode = st.sidebar.radio("Color to remove from frame:", ["Black", "White"])
    sens = st.sidebar.slider("Removal Sensitivity", 0, 255, 50 if bg_mode == "Black" else 230)
    
    st.sidebar.divider()
    st.sidebar.subheader("Manual Uploads")
    f_land_file = st.sidebar.file_uploader("Upload Landscape Frame", type=['png', 'jpg'])
    f_port_file = st.sidebar.file_uploader("Upload Portrait Frame", type=['png', 'jpg'])

    photos = st.file_uploader("Upload Event Photos (Batch)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

    if photos:
        test_img = Image.open(photos[0]).convert("RGBA")
        
        def get_frame(p_img):
            is_land = p_img.width > p_img.height
            src = f_land_file if is_land and f_land_file else (f_port_file if not is_land and f_port_file else None)
            if not src:
                def_path = "frame_land.png" if is_land else "frame_port.png"
                src = def_path if os.path.exists(def_path) else None
            
            if src:
                f_img = Image.open(src)
                return smart_transparent(f_img, mode=bg_mode, threshold=sens)
            return None

        frame_to_use = get_frame(test_img)
        if frame_to_use:
            res_f = frame_to_use.resize(test_img.size, Image.Resampling.LANCZOS)
            test_img.alpha_composite(res_f)
            st.image(test_img.convert("RGB"), caption="Auto-Frame Preview", use_container_width=True)
            
            if st.button("🚀 Start Batch Processing"):
                zip_p = io.BytesIO()
                with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as z:
                    bar_p = st.progress(0)
                    for i, p_file in enumerate(photos):
                        p_img = Image.open(p_file).convert("RGBA")
                        active_f = get_frame(p_img)
                        if active_f:
                            f_res = active_f.resize(p_img.size, Image.Resampling.LANCZOS)
                            p_img.alpha_composite(f_res)
                        img_io = io.BytesIO()
                        p_img.convert("RGB").save(img_io, format="JPEG", quality=90)
                        z.writestr(p_file.name, img_io.getvalue())
                        bar_p.progress((i+1)/len(photos))
                st.download_button("📥 Download Branded Photos (ZIP)", zip_p.getvalue(), "EPS_Photos.zip")
        else:
            st.error("⚠️ No default frames found (`frame_land.png` / `frame_port.png`). Please upload manually.")
    else:
        st.info("Upload your photos to see the live preview.")