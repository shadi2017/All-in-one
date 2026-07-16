import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile
import requests

# --- قائمة الخطوط العربية الأونلاين ---
FONTS_URLS = {
    "Cairo (Bold)": "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bwght%5D.ttf",
    "Almarai (Regular)": "https://github.com/google/fonts/raw/main/ofl/almarai/Almarai-Regular.ttf",
    "Tajawal (Medium)": "https://github.com/google/fonts/raw/main/ofl/tajawal/Tajawal-Medium.ttf",
    "Amiri (Regular)": "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf",
    "Simplified Arabic": "https://github.com/Nordin-Nabil/fonts/raw/master/simplified-arabic.ttf"
}

# وظيفة لتحميل الخط من الإنترنت وعمل Cache له عشان السرعة
@st.cache_data
def download_font(url):
    response = requests.get(url)
    return response.content

# وظيفة معالجة العربي
def fix_arabic(text):
    if pd.isna(text) or str(text).strip() == "": return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False, 'support_ligatures': True, 'arabic': True})
    return get_display(reshaper.reshape(str(text)))

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def make_black_transparent(img_pil):
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if item[0] < 45 and item[1] < 45 and item[2] < 45: new_data.append((0, 0, 0, 0))
        else: new_data.append(item)
    img.putdata(new_data)
    return img

# --- إعدادات الصفحة ---
st.set_page_config(page_title="المساعد الذكي للميديا", layout="wide")
st.title("🚀 المساعد الذكي المطور (خطوط أونلاين)")

tab1, tab2 = st.tabs(["🎓 صانع الشهادات", "📸 برواز الصور"])

# --- TAB 1: صانع الشهادات ---
with tab1:
    st.header("إصدار شهادات مجمع")
    c_col1, c_col2 = st.columns([1, 2])
    
    with c_col1:
        st.subheader("📁 1. الملفات")
        cert_tpl = st.file_uploader("ارفع صورة الشهادة", type=['png', 'jpg', 'jpeg'], key="c1")
        cert_data = st.file_uploader("ارفع شيت البيانات", type=['xlsx', 'csv'], key="c2")
        
        st.subheader("✒️ 2. الخط العربي")
        font_mode = st.radio("مصدر الخط:", ["اختيار خط أونلاين", "رفع خط من جهازي"])
        
        fnt_bytes = None
        if font_mode == "اختيار خط أونلاين":
            font_choice = st.selectbox("اختر الخط المفضل:", list(FONTS_URLS.keys()))
            fnt_bytes = download_font(FONTS_URLS[font_choice])
        else:
            uploaded_fnt = st.file_uploader("ارفع ملف الخط (TTF)", type=['ttf'], key="c3")
            if uploaded_fnt: fnt_bytes = uploaded_fnt.read()

        if cert_tpl and cert_data and fnt_bytes:
            df = pd.read_excel(cert_data) if cert_data.name.endswith('.xlsx') else pd.read_csv(cert_data)
            
            st.divider()
            name_col = st.selectbox("عمود الأسماء", df.columns)
            n_x = st.number_input("الاسم X", value=500)
            n_y = st.number_input("الاسم Y", value=350)
            n_size = st.slider("حجم الخط", 10, 300, 70)
            n_clr = st.color_picker("لون الخط", "#000000")
            
            use_grade = st.checkbox("إضافة تقدير؟")
            g_col, g_x, g_y, g_size, g_clr = None, 0, 0, 40, "#000000"
            if use_grade:
                g_col = st.selectbox("عمود التقدير", df.columns)
                g_x = st.number_input("التقدير X", value=500)
                g_y = st.number_input("التقدير Y", value=450)
                g_size = st.slider("حجم التقدير", 10, 200, 50)
                g_clr = st.color_picker("لون التقدير", "#333333")

    with c_col2:
        if cert_tpl and cert_data and fnt_bytes:
            p_img = Image.open(cert_tpl).convert("RGB")
            draw = ImageDraw.Draw(p_img)
            f_n = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_clr), font=f_n, anchor="mm")
            if use_grade:
                f_g = ImageFont.truetype(io.BytesIO(fnt_bytes), g_size)
                draw.text((g_x, g_y), fix_arabic(df.iloc[0][g_col]), fill=hex_to_rgb(g_clr), font=f_g, anchor="mm")
            st.image(p_img, caption="معاينة حية")
            
            if st.button("🚀 إصدار الشهادات (PDF)"):
                pdf_list = []
                p_bar = st.progress(0)
                for i, row in df.iterrows():
                    img = Image.open(cert_tpl).convert("RGB")
                    d = ImageDraw.Draw(img)
                    d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_clr), font=f_n, anchor="mm")
                    if use_grade:
                        d.text((g_x, g_y), fix_arabic(row[g_col]), fill=hex_to_rgb(g_clr), font=f_g, anchor="mm")
                    pdf_list.append(img)
                    p_bar.progress((i+1)/len(df))
                out = io.BytesIO()
                pdf_list[0].save(out, format="PDF", save_all=True, append_images=pdf_list[1:])
                st.download_button("📥 تحميل الـ PDF", out.getvalue(), "Certificates.pdf")

# --- TAB 2: برواز الصور ---
with tab2:
    st.header("إضافة برواز اللوجو للصور")
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        f_file = st.file_uploader("1. ارفع الفريم", type=['png', 'jpg', 'jpeg'], key="f1")
        photos = st.file_uploader("2. ارفع الصور", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="f2")
    with f_col2:
        if f_file and photos:
            raw_f = Image.open(f_file)
            proc_f = make_black_transparent(raw_f)
            sample_p = Image.open(photos[0]).convert("RGBA")
            res_f = proc_f.resize(sample_p.size, Image.Resampling.LANCZOS)
            sample_p.alpha_composite(res_f)
            st.image(sample_p.convert("RGB"), caption="معاينة")
            
            if st.button("🚀 معالجة الصور (ZIP)"):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buffer := io.BytesIO(), "w", zipfile.ZIP_DEFLATED) as z:
                    bar = st.progress(0)
                    for i, pf in enumerate(photos):
                        p_img = Image.open(pf).convert("RGBA")
                        fr = proc_f.resize(p_img.size, Image.Resampling.LANCZOS)
                        p_img.alpha_composite(fr)
                        img_io = io.BytesIO()
                        p_img.convert("RGB").save(img_io, format="JPEG", quality=90)
                        z.writestr(pf.name, img_io.getvalue())
                        bar.progress((i+1)/len(photos))
                st.download_button("📥 تحميل الـ ZIP", zip_buffer.getvalue(), "Photos.zip")