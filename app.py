import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile

# --- وظائف عامة ---
def fix_arabic(text):
    if pd.isna(text) or str(text).strip() == "": return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': False, 'support_ligatures': True, 'arabic': True})
    return get_display(reshaper.reshape(str(text)))

def hex_to_rgb(h):
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

# --- إعدادات الصفحة ---
st.set_page_config(page_title="المساعد الذكي", layout="wide")
tab1, tab2 = st.tabs(["🎓 صانع الشهادات", "📸 برواز الصور المجمع"])

# --- Tab 1: صانع الشهادات ---
with tab1:
    st.header("صانع الشهادات الديناميكي")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        tpl_file = st.file_uploader("1. ارفع التيمبلت", type=['png', 'jpg', 'jpeg'], key="tpl")
        exc_file = st.file_uploader("2. ارفع الإكسيل", type=['xlsx', 'csv'], key="exc")
        fnt_file = st.file_uploader("3. ارفع الخط (TTF)", type=['ttf'], key="fnt")
        
        if tpl_file and exc_file and fnt_file:
            df = pd.read_excel(exc_file) if exc_file.name.endswith('.xlsx') else pd.read_csv(exc_file)
            fnt_bytes = fnt_file.read()
            
            st.divider()
            name_col = st.selectbox("عمود الأسماء", df.columns)
            n_x = st.number_input("الاسم X", value=500)
            n_y = st.number_input("الاسم Y", value=350)
            n_size = st.slider("حجم الاسم", 10, 200, 60)
            n_color = st.color_picker("لون الاسم", "#000000")
            
            show_g = st.checkbox("إضافة تقدير؟")
            g_col, g_x, g_y, g_size, g_color = None, 0, 0, 40, "#333333"
            if show_g:
                g_col = st.selectbox("عمود التقدير", df.columns)
                g_x = st.number_input("التقدير X", value=500)
                g_y = st.number_input("التقدير Y", value=450)
                g_size = st.slider("حجم التقدير", 10, 200, 40)
                g_color = st.color_picker("لون التقدير", "#333333")

    with col2:
        if tpl_file and exc_file and fnt_file:
            # المعاينة
            preview = Image.open(tpl_file).convert("RGB")
            draw = ImageDraw.Draw(preview)
            font_n = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_color), font=font_n, anchor="mm")
            if show_g:
                font_g = ImageFont.truetype(io.BytesIO(fnt_bytes), g_size)
                draw.text((g_x, g_y), fix_arabic(df.iloc[0][g_col]), fill=hex_to_rgb(g_color), font=font_g, anchor="mm")
            st.image(preview, caption="معاينة لأول اسم")
            
            if st.button("🚀 استخراج الكل (PDF)"):
                all_pdfs = []
                bar = st.progress(0)
                for i, row in df.iterrows():
                    img = Image.open(tpl_file).convert("RGB")
                    d = ImageDraw.Draw(img)
                    d.text((n_x, n_y), fix_arabic(row[name_col]), fill=hex_to_rgb(n_color), font=font_n, anchor="mm")
                    if show_g:
                        d.text((g_x, g_y), fix_arabic(row[g_col]), fill=hex_to_rgb(g_color), font=font_g, anchor="mm")
                    all_pdfs.append(img)
                    bar.progress((i+1)/len(df))
                
                out = io.BytesIO()
                all_pdfs[0].save(out, format="PDF", save_all=True, append_images=all_pdfs[1:])
                st.download_button("📥 تحميل الـ PDF", out.getvalue(), "Certs.pdf")

# --- Tab 2: برواز الصور ---
with tab2:
    st.header("إضافة برواز لصور الحفلة")
    f_file = st.file_uploader("1. ارفع الفريم (الأسود سيختفي)", type=['jpg', 'jpeg', 'png'], key="frm")
    photos = st.file_uploader("2. ارفع الصور (يمكنك رفع عدد كبير)", type=['jpg','png','jpeg'], accept_multiple_files=True)
    
    if f_file and photos:
        # معالجة الفريم (شفافية الأسود)
        frame_raw = Image.open(f_file).convert("RGBA")
        datas = frame_raw.getdata()
        new_data = []
        for item in datas:
            if item[0] < 45 and item[1] < 45 and item[2] < 45: new_data.append((0,0,0,0))
            else: new_data.append(item)
        frame_raw.putdata(new_data)
        
        st.image(photos[0], width=300, caption="عينة قبل")
        
        if st.button("🚀 ابدأ معالجة الصور وعمل ZIP"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
                bar = st.progress(0)
                for i, p_file in enumerate(photos):
                    p_img = Image.open(p_file).convert("RGBA")
                    f_resized = frame_raw.resize(p_img.size, Image.Resampling.LANCZOS)
                    p_img.alpha_composite(f_resized)
                    
                    final = p_img.convert("RGB")
                    img_byte = io.BytesIO()
                    final.save(img_byte, format="JPEG", quality=85)
                    zip_file.writestr(p_file.name, img_byte.getvalue())
                    bar.progress((i+1)/len(photos))
            
            st.success("تم الانتهاء!")
            st.download_button("📥 تحميل كل الصور (ZIP)", zip_buffer.getvalue(), "Branded_Photos.zip")