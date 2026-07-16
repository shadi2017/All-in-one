import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import io
import zipfile
import os

# --- وظائف المعالجة الأساسية ---

def fix_arabic(text):
    """تصحيح اللغة العربية لتظهر متصلة ومن اليمين للشمال"""
    if pd.isna(text) or str(text).strip() == "": return ""
    reshaper = arabic_reshaper.ArabicReshaper(configuration={
        'delete_harakat': False, 'support_ligatures': True, 'arabic': True
    })
    return get_display(reshaper.reshape(str(text)))

def make_black_transparent(img_pil):
    """تحويل المساحات السوداء في الفريم لشفافة للحفاظ على صورة الحفلة"""
    img = img_pil.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # إذا كان اللون أسود أو قريب جداً منه (RGB < 45)، نجعله شفافاً
        if item[0] < 45 and item[1] < 45 and item[2] < 45:
            new_data.append((0, 0, 0, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img

def hex_to_rgb(h):
    """تحويل كود اللون من الويب لـ RGB"""
    return tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

# --- إعدادات واجهة المستخدم ---
st.set_page_config(page_title="المساعد الذكي للميديا", layout="wide", page_icon="🚀")

st.title("🚀 المساعد الذكي: شهادات + برواز حفلات")
st.markdown("سكريبت واحد لكل المهام - يدعم اللغة العربية وجودة عالية")

# إنشاء التبويبات (Tabs)
tab1, tab2 = st.tabs(["🎓 صانع الشهادات الذكي", "📸 برواز الصور المجمع"])

# --- TAB 1: صانع الشهادات ---
with tab1:
    st.header("إصدار شهادات مجمع (PDF)")
    c_col1, c_col2 = st.columns([1, 2])
    
    with c_col1:
        st.subheader("📁 رفع الملفات")
        cert_tpl = st.file_uploader("1. صورة الشهادة (Template)", type=['png', 'jpg', 'jpeg'], key="cert_tpl")
        cert_data = st.file_uploader("2. شيت البيانات (Excel/CSV)", type=['xlsx', 'csv'], key="cert_data")
        cert_font = st.file_uploader("3. ملف الخط العربي (TTF)", type=['ttf'], key="cert_font")
        
        if cert_tpl and cert_data and cert_font:
            df = pd.read_excel(cert_data) if cert_data.name.endswith('.xlsx') else pd.read_csv(cert_data)
            fnt_bytes = cert_font.read()
            
            st.divider()
            st.subheader("📍 إعدادات النصوص")
            name_col = st.selectbox("اختر عمود الأسماء", df.columns)
            n_x = st.number_input("الاسم - أفقي X", value=500)
            n_y = st.number_input("الاسم - رأسي Y", value=350)
            n_size = st.slider("حجم خط الاسم", 10, 300, 70)
            n_clr = st.color_picker("لون خط الاسم", "#000000")
            
            st.divider()
            use_grade = st.checkbox("إضافة تقدير/درجة؟")
            g_col, g_x, g_y, g_size, g_clr = None, 0, 0, 40, "#000000"
            if use_grade:
                g_col = st.selectbox("اختر عمود التقدير", df.columns)
                g_x = st.number_input("التقدير - أفقي X", value=500)
                g_y = st.number_input("التقدير - رأسي Y", value=450)
                g_size = st.slider("حجم خط التقدير", 10, 200, 50)
                g_clr = st.color_picker("لون التقدير", "#333333")

    with c_col2:
        if cert_tpl and cert_data and cert_font:
            st.subheader("👁️ معاينة حية")
            # تجهيز المعاينة
            p_img = Image.open(cert_tpl).convert("RGB")
            draw = ImageDraw.Draw(p_img)
            f_n = ImageFont.truetype(io.BytesIO(fnt_bytes), n_size)
            
            # رسم الاسم
            draw.text((n_x, n_y), fix_arabic(df.iloc[0][name_col]), fill=hex_to_rgb(n_clr), font=f_n, anchor="mm")
            
            # رسم التقدير
            if use_grade:
                f_g = ImageFont.truetype(io.BytesIO(fnt_bytes), g_size)
                draw.text((g_x, g_y), fix_arabic(df.iloc[0][g_col]), fill=hex_to_rgb(g_clr), font=f_g, anchor="mm")
            
            st.image(p_img, use_container_width=True, caption="شكل الشهادة النهائي")
            
            if st.button("🚀 إصدار كل الشهادات الآن"):
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
                
                pdf_buf = io.BytesIO()
                pdf_list[0].save(pdf_buf, format="PDF", save_all=True, append_images=pdf_list[1:])
                st.success("✅ تم التجهيز بنجاح!")
                st.download_button("📥 تحميل ملف الـ PDF المجمع", pdf_buf.getvalue(), "Certificates.pdf")

# --- TAB 2: برواز الحفلات ---
with tab2:
    st.header("إضافة برواز اللوجو للصور (Batch Processing)")
    st.info("البرنامج سيقوم بمط الفريم ليناسب كل صورة (طولاً أو عرضاً) أوتوماتيكياً مع الحفاظ على أعلى جودة.")
    
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        st.subheader("📁 الملفات")
        frame_file = st.file_uploader("1. ارفع صورة الفريم", type=['png', 'jpg', 'jpeg'], key="frame_file")
        photos = st.file_uploader("2. ارفع صور الحفلة (يمكن رفع عدد كبير)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="photos")
        quality = st.slider("جودة الصور الناتجة (تأثير على المساحة)", 50, 100, 90)

    with f_col2:
        if frame_file and photos:
            # معالجة الفريم (تحويل الأسود لشفاف)
            with st.spinner("جاري تجهيز الفريم..."):
                raw_f = Image.open(frame_file)
                processed_f = make_black_transparent(raw_f)
            
            st.subheader("👁️ معاينة")
            # فتح أول صورة للمعاينة
            sample_p = Image.open(photos[0]).convert("RGBA")
            # تغيير مقاس الفريم ليناسب مقاس الصورة بدقة عالية
            res_f = processed_f.resize(sample_p.size, Image.Resampling.LANCZOS)
            sample_p.alpha_composite(res_f)
            st.image(sample_p.convert("RGB"), caption="شكل الصورة بعد البروزة", use_container_width=True)

            if st.button("🚀 ابدأ معالجة الصور وعمل ملف ZIP"):
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    f_bar = st.progress(0)
                    status_txt = st.empty()
                    for i, p_file in enumerate(photos):
                        status_txt.text(f"جاري معالجة: {p_file.name}")
                        p_img = Image.open(p_file).convert("RGBA")
                        # مط الفريم ليناسب مقاس كل صورة (سواء Portrait أو Landscape)
                        f_res = processed_f.resize(p_img.size, Image.Resampling.LANCZOS)
                        p_img.alpha_composite(f_res)
                        
                        final = p_img.convert("RGB")
                        img_io = io.BytesIO()
                        # حفظ بأعلى جودة لتقليل البكسلة
                        final.save(img_io, format="JPEG", quality=quality, subsampling=0)
                        zip_file.writestr(p_file.name, img_io.getvalue())
                        f_bar.progress((i+1)/len(photos))
                
                st.success("✅ تمت المعالجة بنجاح!")
                st.download_button("📥 تحميل كل الصور المبروزة (ZIP)", zip_buf.getvalue(), "Branded_Photos.zip")