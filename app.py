import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile
import requests

# --- وظائف المعالجة ---
def fix_arabic(text):
    if pd.isna(text) or str(text).strip() == "": return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False, 'support_ligatures': True, 'arabic': True})
    return get_display(reshaper.reshape(str(text)))

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

@st.cache_data
def download_font(url):
    try:
        r = requests.get(url, timeout=10)
        return r.content if r.status_code == 200 else None
    except: return None

def smart_transparent(img_pil, threshold=230):
    """إزالة الخلفية البيضاء مع الحفاظ على جودة اللوجو"""
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # مسح الأبيض (المساحة الكبيرة) مع الحفاظ على الألوان التانية
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img

# --- إعدادات الصفحة ---
st.set_page_config(page_title="EPS Production System", layout="wide")
st.title("🛡️ نظام EPS للإنتاج المتكامل")

tab1, tab2 = st.tabs(["📜 إصدار الشهادات المطور", "🖼️ معالج براويز الصور الذكي"])

# --- TAB 1: الشهادات ---
with tab1:
    st.subheader("إعدادات الشهادة (الاسم + التقدير)")
    
    col_input, col_preview = st.columns([1, 2])
    
    with col_input:
        tpl_file = st.file_uploader("1. ارفع تيمبلت الشهادة", type=['png', 'jpg', 'jpeg'], key="cert_tpl")
        data_file = st.file_uploader("2. شيت البيانات (Excel/CSV)", type=['xlsx', 'csv'], key="cert_data")
        font_url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf"
        fnt_bytes = download_font(font_url)
        
        if tpl_file and data_file and fnt_bytes:
            df = pd.read_excel(data_file) if data_file.name.endswith('.xlsx') else pd.read_csv(data_file)
            cols = df.columns.tolist()
            
            st.markdown("### 👤 تنسيق الاسم")
            name_col = st.selectbox("عمود الأسماء", cols)
            n_x = st.slider("الاسم - X (أفقي)", 0, 2000, 500)
            n_y = st.slider("الاسم - Y (رأسي)", 0, 2000, 400)
            n_size = st.number_input("حجم خط الاسم", 10, 500, 80)
            n_color = st.color_picker("لون الاسم", "#002d56")
            
            st.markdown("### 🎓 تنسيق التقدير")
            show_grade = st.checkbox("تفعيل إضافة التقدير")
            if show_grade:
                grade_col = st.selectbox("عمود التقدير", cols)
                g_x = st.slider("التقدير - X", 0, 2000, 500)
                g_y = st.slider("التقدير - Y", 0, 2000, 550)
                g_size = st.number_input("حجم خط التقدير", 10, 500, 50)
                g_color = st.color_picker("لون التقدير", "#333333")

    with col_preview:
        if tpl_file and data_file and fnt_bytes:
            # معاينة حية
            main_img = Image.open(tpl_file).convert("RGB")
            draw = ImageDraw.Draw(main_img)
            f_name = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_color), font=f_name, anchor="mm")
            
            if show_grade:
                f_grade = ImageFont.truetype(io.BytesIO(fnt_bytes), g_size)
                draw.text((g_x, g_y), fix_arabic(df.iloc[0][grade_col]), fill=hex_to_rgb(g_color), font=f_grade, anchor="mm")
            
            st.image(main_img, caption="معاينة حية للمكان والخط", use_container_width=True)
            
            if st.button("🚀 إصدار الشهادات"):
                pdf_list = []
                zip_io = io.BytesIO()
                with zipfile.ZipFile(zip_io, "w") as z:
                    for i, row in df.iterrows():
                        img = Image.open(tpl_file).convert("RGB")
                        d = ImageDraw.Draw(img)
                        d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_color), font=f_name, anchor="mm")
                        if show_grade:
                            d.text((g_x, g_y), fix_arabic(row[grade_col]), fill=hex_to_rgb(g_color), font=f_grade, anchor="mm")
                        
                        img_byte = io.BytesIO()
                        img.save(img_byte, format="JPEG", quality=95)
                        z.writestr(f"{row[name_col]}.jpg", img_byte.getvalue())
                        pdf_list.append(img)
                
                pdf_io = io.BytesIO()
                pdf_list[0].save(pdf_io, format="PDF", save_all=True, append_images=pdf_list[1:])
                
                st.success("✅ تم الإنتاج!")
                c1, c2 = st.columns(2)
                c1.download_button("📥 تحميل PDF المجمع", pdf_io.getvalue(), "Certificates.pdf")
                c2.download_button("📥 تحميل الصور ZIP", zip_io.getvalue(), "Images.zip")

# --- TAB 2: براويز الصور ---
with tab2:
    st.subheader("إضافة برواز اللوجو (Landscape / Portrait)")
    
    col_f_input, col_f_preview = st.columns([1, 2])
    
    with col_f_input:
        f_land = st.file_uploader("1. فريم العرض (Landscape)", type=['png', 'jpg'], key="f_l")
        f_port = st.file_uploader("2. فريم الطول (Portrait)", type=['png', 'jpg'], key="f_p")
        photos = st.file_uploader("3. ارفع صور الحفلة (Batch)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)
        sens = st.slider("حساسية مسح الخلفية (الافتراضي 230)", 150, 255, 230)

    with col_f_preview:
        if (f_land or f_port) and photos:
            test_img = Image.open(photos[0]).convert("RGBA")
            is_land = test_img.width > test_img.height
            
            frame_source = f_land if is_land else f_port
            if frame_source:
                with st.spinner("جاري معالجة الفريم..."):
                    frame_raw = Image.open(frame_source)
                    frame_clean = smart_transparent(frame_raw, threshold=sens)
                    
                    # دمج
                    res_f = frame_clean.resize(test_img.size, Image.Resampling.LANCZOS)
                    test_img.alpha_composite(res_f)
                    
                    st.image(test_img.convert("RGB"), caption="معاينة دمج البرواز", use_container_width=True)
            
            if st.button("🚀 ابدأ بروزة كل الصور"):
                zip_p = io.BytesIO()
                with zipfile.ZipFile(zip_p, "w", zipfile.ZIP_DEFLATED) as z:
                    bar = st.progress(0)
                    for i, p_file in enumerate(photos):
                        p_img = Image.open(p_file).convert("RGBA")
                        # اختيار الفريم المناسب للصورة الحالية
                        f_src = f_land if p_img.width > p_img.height else f_port
                        if f_src:
                            f_clean = smart_transparent(Image.open(f_src), threshold=sens)
                            f_res = f_clean.resize(p_img.size, Image.Resampling.LANCZOS)
                            p_img.alpha_composite(f_res)
                        
                        img_io = io.BytesIO()
                        p_img.convert("RGB").save(img_io, format="JPEG", quality=90)
                        z.writestr(p_file.name, img_io.getvalue())
                        bar.progress((i+1)/len(photos))
                
                st.download_button("📥 تحميل الصور المبروزة (ZIP)", zip_p.getvalue(), "EPS_Photos.zip")