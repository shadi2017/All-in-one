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

# --- إعدادات الخطوط (Amiri هو الأساسي) ---
FONTS_URLS = {
    "Amiri (Regular)": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf",
    "Cairo (Bold)": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cairo/static/Cairo-Bold.ttf",
    "Almarai (Bold)": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/almarai/Almarai-Bold.ttf"
}

@st.cache_data
def download_font(url):
    try:
        response = requests.get(url, timeout=15)
        return response.content if response.status_code == 200 else None
    except: return None

def fix_arabic(text):
    if pd.isna(text) or str(text).strip() == "": return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False, 'support_ligatures': True, 'arabic': True})
    return get_display(reshaper.reshape(str(text)))

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

# وظيفة سحرية لإزالة الخلفية البيضاء أو السوداء من الفريم
def process_frame_transparency(img_pil, mode="White"):
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if mode == "White":
            # لو اللون أبيض (RGB > 230) خليه شفاف
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)
        else: # الأسود
            if item[0] < 50 and item[1] < 50 and item[2] < 50:
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)
    img.putdata(new_data)
    return img

# --- تهيئة الـ Session State لحفظ الملفات ---
if 'cert_pdf' not in st.session_state: st.session_state.cert_pdf = None
if 'cert_zip' not in st.session_state: st.session_state.cert_zip = None

st.set_page_config(page_title="EPS Master System", layout="wide", page_icon="🎓")
st.title("🛡️ نظام EPS الاحترافي الموحد")

tab1, tab2 = st.tabs(["📜 إصدار الشهادات الذكي", "📸 معالج صور الحفلات الضخم"])

# --- TAB 1: الشهادات ---
with tab1:
    st.header("إعدادات الشهادات")
    c_col1, c_col2 = st.columns([1, 2])
    
    with c_col1:
        cert_tpl = st.file_uploader("1. تيمبلت الشهادة", type=['png', 'jpg', 'jpeg'], key="cert_tpl")
        cert_data = st.file_uploader("2. شيت الأسماء", type=['xlsx', 'csv'], key="cert_data")
        font_choice = st.selectbox("3. الخط العربي (Amiri ينصح به):", list(FONTS_URLS.keys()), index=0)
        fnt_bytes = download_font(FONTS_URLS[font_choice])

        if cert_tpl and cert_data and fnt_bytes:
            df = pd.read_excel(cert_data) if cert_data.name.endswith('.xlsx') else pd.read_csv(cert_data)
            name_col = st.selectbox("اختر عمود الأسماء", df.columns)
            n_x = st.number_input("مكان الاسم X (أفقي)", value=500)
            n_y = st.number_input("مكان الاسم Y (رأسي)", value=350)
            n_size = st.slider("حجم الخط", 10, 400, 80)
            n_clr = st.color_picker("لون الخط", "#002d56")

            if st.button("🚀 إصدار كل الشهادات"):
                pdf_list = []
                zip_io = io.BytesIO()
                with zipfile.ZipFile(zip_io, "w") as z:
                    font_obj = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
                    bar = st.progress(0)
                    for i, row in df.iterrows():
                        img = Image.open(cert_tpl).convert("RGB")
                        d = ImageDraw.Draw(img)
                        d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_clr), font=font_obj, anchor="mm")
                        pdf_list.append(img)
                        img_byte = io.BytesIO()
                        img.save(img_byte, format="JPEG", quality=95)
                        z.writestr(f"{str(row[name_col])}.jpg", img_byte.getvalue())
                        bar.progress((i+1)/len(df))
                
                pdf_io = io.BytesIO()
                pdf_list[0].save(pdf_io, format="PDF", save_all=True, append_images=pdf_list[1:])
                st.session_state.cert_pdf = pdf_io.getvalue()
                st.session_state.cert_zip = zip_io.getvalue()
                st.success("✅ تم الإنتاج بنجاح!")

    with c_col2:
        if cert_tpl and cert_data and fnt_bytes:
            p_img = Image.open(cert_tpl).convert("RGB")
            draw = ImageDraw.Draw(p_img)
            f_prev = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_clr), font=f_prev, anchor="mm")
            st.image(p_img, caption="معاينة مكان الاسم", use_container_width=True)
            
            if st.session_state.cert_pdf and st.session_state.cert_zip:
                st.divider()
                st.download_button("📥 تحميل PDF مجمع", st.session_state.cert_pdf, "Certificates.pdf")
                st.download_button("📥 تحميل الصور ZIP", st.session_state.cert_zip, "Certs_Images.zip")

# --- TAB 2: برواز الصور ---
with tab2:
    st.header("معالج صور الحفلات (تلقائي بالكامل)")
    st.sidebar.subheader("🖼️ إعدادات البرواز")
    
    # محاولة جلب الديفولت من الفولدر
    def_land = "frame_land.jpg" if os.path.exists("frame_land.jpg") else "frame_land.png"
    def_port = "frame_port.jpg" if os.path.exists("frame_port.jpg") else "frame_port.png"
    
    f_mode = st.sidebar.radio("لون خلفية الفريم اللي عاوز تشيله:", ["White", "Black"])
    
    # اختيار فريمات يدوية (لو حابب يغير الديفولت)
    custom_land = st.sidebar.file_uploader("تغيير فريم العرض", type=['png','jpg','jpeg'])
    custom_port = st.sidebar.file_uploader("تغيير فريم الطول", type=['png','jpg','jpeg'])
    
    photos = st.file_uploader("ارفع صور الحفلة (Batch)", type=['jpg','png','jpeg'], accept_multiple_files=True)

    if photos:
        st.subheader("👁️ معاينة الفريم التلقائي")
        
        def get_best_frame(p_pil):
            is_land = p_pil.width > p_pil.height
            # تحديد أي فريم هيستخدم
            if is_land:
                f_source = custom_land if custom_land else (def_land if os.path.exists(def_land) else None)
            else:
                f_source = custom_port if custom_port else (def_port if os.path.exists(def_port) else None)
            
            if f_source:
                raw = Image.open(f_source)
                return process_frame_transparency(raw, mode=f_mode)
            return None

        # معاينة أول صورة
        test_img = Image.open(photos[0]).convert("RGBA")
        f_to_use = get_best_frame(test_img)
        
        if f_to_use:
            res_f = f_to_use.resize(test_img.size, Image.Resampling.LANCZOS)
            test_img.alpha_composite(res_f)
            st.image(test_img.convert("RGB"), caption="معاينة (تم إزالة الخلفية لتظهر الصورة)", width=700)

            if st.button("🚀 ابدأ معالجة الـ Batch"):
                zip_p = io.BytesIO()
                with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as z:
                    p_bar = st.progress(0)
                    for i, p_file in enumerate(photos):
                        img = Image.open(p_file).convert("RGBA")
                        curr_f = get_best_frame(img)
                        if curr_f:
                            curr_f_res = curr_f.resize(img.size, Image.Resampling.LANCZOS)
                            img.alpha_composite(curr_f_res)
                        
                        img_io = io.BytesIO()
                        img.convert("RGB").save(img_io, format="JPEG", quality=90)
                        z.writestr(p_file.name, img_io.getvalue())
                        p_bar.progress((i+1)/len(photos))
                
                st.success("✅ تمت معالجة كل الصور!")
                st.download_button("📥 تحميل الكل (ZIP)", zip_p.getvalue(), "EPS_Photos.zip")
        else:
            st.error("⚠️ لم يتم العثور على فريمات! تأكد من وجود ملفات frame_land و frame_port في الفولدر.")