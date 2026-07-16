import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile
import requests
import os

# --- إعدادات الخطوط ---
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

def make_black_transparent(img_pil):
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # تحويل الأسود (أقل من 50) لشفاف
        if item[0] < 50 and item[1] < 50 and item[2] < 50:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img

# --- تهيئة الـ Session State ---
if 'cert_pdf' not in st.session_state: st.session_state.cert_pdf = None
if 'cert_zip' not in st.session_state: st.session_state.cert_zip = None

st.set_page_config(page_title="EPS Smart System", layout="wide", page_icon="🎓")
st.title("🎓 نظام EPS الذكي (إصدار 2.0)")

tab1, tab2 = st.tabs(["📜 إصدار الشهادات", "🖼️ برواز صور الحفلات"])

# --- TAB 1: الشهادات ---
with tab1:
    st.header("إعدادات الشهادات المجمعة")
    c_col1, c_col2 = st.columns([1, 2])
    
    with c_col1:
        cert_tpl = st.file_uploader("1. ارفع تيمبلت الشهادة", type=['png', 'jpg', 'jpeg'], key="c1")
        cert_data = st.file_uploader("2. شيت الأسماء (Excel/CSV)", type=['xlsx', 'csv'], key="c2")
        font_choice = st.selectbox("3. نوع الخط العربي:", list(FONTS_URLS.keys()), index=0)
        fnt_bytes = download_font(FONTS_URLS[font_choice])

        if cert_tpl and cert_data and fnt_bytes:
            df = pd.read_excel(cert_data) if cert_data.name.endswith('.xlsx') else pd.read_csv(cert_data)
            name_col = st.selectbox("عمود الأسماء", df.columns)
            n_x = st.number_input("مكان الاسم أفقي (X)", value=500)
            n_y = st.number_input("مكان الاسم رأسي (Y)", value=350)
            n_size = st.slider("حجم الخط", 10, 400, 80)
            n_clr = st.color_picker("لون الخط", "#002d56")

            if st.button("🚀 معالجة وإصدار الملفات"):
                pdf_list = []
                zip_certs_io = io.BytesIO()
                with zipfile.ZipFile(zip_certs_io, "w") as z_certs:
                    font_n = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
                    bar = st.progress(0)
                    for i, row in df.iterrows():
                        img = Image.open(cert_tpl).convert("RGB")
                        d = ImageDraw.Draw(img)
                        d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_clr), font=font_n, anchor="mm")
                        pdf_list.append(img)
                        img_byte = io.BytesIO()
                        img.save(img_byte, format="JPEG", quality=95)
                        z_certs.writestr(f"{str(row[name_col])}.jpg", img_byte.getvalue())
                        bar.progress((i+1)/len(df))
                
                pdf_io = io.BytesIO()
                pdf_list[0].save(pdf_io, format="PDF", save_all=True, append_images=pdf_list[1:])
                st.session_state.cert_pdf = pdf_io.getvalue()
                st.session_state.cert_zip = zip_certs_io.getvalue()
                st.success("✅ تم توليد الملفات بنجاح!")

    with c_col2:
        if cert_tpl and cert_data and fnt_bytes:
            p_img = Image.open(cert_tpl).convert("RGB")
            draw = ImageDraw.Draw(p_img)
            f_n_p = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_clr), font=f_n_p, anchor="mm")
            st.image(p_img, caption="معاينة مكان الاسم (أول اسم في الشيت)", use_container_width=True)

        if st.session_state.cert_pdf and st.session_state.cert_zip:
            st.divider()
            d1, d2 = st.columns(2)
            with d1: st.download_button("📥 تحميل PDF مجمع", st.session_state.cert_pdf, "Certificates.pdf", mime="application/pdf")
            with d2: st.download_button("📥 تحميل الصور ZIP", st.session_state.cert_zip, "Certs_Images.zip", mime="application/zip")

# --- TAB 2: برواز الصور ---
with tab2:
    st.header("إضافة برواز EPS التلقائي")
    st.sidebar.subheader("🖼️ إعدادات الفريمات الديفولت")
    
    # محاولة تحميل الفريمات من الفولدر تلقائياً
    def_l_path = "frame_land.png"
    def_p_path = "frame_port.png"
    
    # اختيار فريم يدوي لو عاوز يغير الديفولت
    custom_l = st.sidebar.file_uploader("تغيير فريم العرض (Landscape)", type=['png','jpg'])
    custom_p = st.sidebar.file_uploader("تغيير فريم الطول (Portrait)", type=['png','jpg'])
    override = st.sidebar.file_uploader("🚀 فريم موحد لكل الصور (Override)", type=['png','jpg'])

    photos = st.file_uploader("ارفع صور الحفلة", type=['jpg','png','jpeg'], accept_multiple_files=True)

    if photos:
        st.subheader("👁️ معاينة الفريم")
        
        def get_frame_image(p_img):
            # 1. لو فيه Override استخدمه فوراً
            if override: return make_black_transparent(Image.open(override))
            
            is_land = p_img.width > p_img.height
            
            # 2. لو فيه رفع يدوي للفريم المعين استخدمه
            if is_land and custom_l: return make_black_transparent(Image.open(custom_l))
            if not is_land and custom_p: return make_black_transparent(Image.open(custom_p))
            
            # 3. لو مفيش، دور في الفولدر على الديفولت
            try:
                if is_land and os.path.exists(def_l_path): return make_black_transparent(Image.open(def_l_path))
                if not is_land and os.path.exists(def_p_path): return make_black_transparent(Image.open(def_p_path))
            except: pass
            
            return None

        test_img = Image.open(photos[0]).convert("RGBA")
        f_to_use = get_frame_image(test_img)
        
        if f_to_use:
            res_f = f_to_use.resize(test_img.size, Image.Resampling.LANCZOS)
            test_img.alpha_composite(res_f)
            st.image(test_img.convert("RGB"), caption="معاينة الفريم على أول صورة", width=600)

            if st.button("🚀 ابدأ معالجة الصور الآن"):
                zip_p_io = io.BytesIO()
                with zipfile.ZipFile(zip_p_io, "w", zipfile.ZIP_DEFLATED) as z:
                    p_bar = st.progress(0)
                    for i, p_file in enumerate(photos):
                        p_img = Image.open(p_file).convert("RGBA")
                        curr_f = get_frame_image(p_img)
                        if curr_f:
                            curr_f_res = curr_f.resize(p_img.size, Image.Resampling.LANCZOS)
                            p_img.alpha_composite(curr_f_res)
                        
                        img_io = io.BytesIO()
                        p_img.convert("RGB").save(img_io, format="JPEG", quality=90)
                        z.writestr(p_file.name, img_io.getvalue())
                        p_bar.progress((i+1)/len(photos))
                st.success("✅ تمت المعالجة!")
                st.download_button("📥 تحميل الصور المبروزة (ZIP)", zip_p_io.getvalue(), "EPS_Photos.zip")
        else:
            st.error("⚠️ لم يتم العثور على فريمات! يرجى التأكد من وجود frame_land.png و frame_port.png في الفولدر أو ارفعهم يدوياً.")