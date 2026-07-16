import streamlit as st
from PIL import Image
import io
import zipfile

# إعدادات الصفحة
st.set_page_config(page_title="برواز الصور - نسخة الويب", layout="wide")

st.title("📸 إضافة برواز اللوجو للصور (Batch Version)")
st.info("ملاحظة: هذه النسخة تعمل على الويب. يتم رفع الصور ومعالجتها ثم تحميلها كملف ZIP.")

# --- الوظائف ---
def make_black_transparent(frame_img):
    """تحويل اللون الأسود في الفريم لشفاف عشان الصور تبان"""
    img = frame_img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # إذا كان اللون أسود أو قريب منه (R,G,B < 45)
        if item[0] < 45 and item[1] < 45 and item[2] < 45:
            new_data.append((0, 0, 0, 0)) # شفاف
        else:
            new_data.append(item)
    img.putdata(new_data)
    return img

# --- واجهة المستخدم ---
st.sidebar.header("📁 الملفات")
frame_file = st.sidebar.file_uploader("1. ارفع الفريم (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
uploaded_photos = st.sidebar.file_uploader("2. ارفع الصور المراد بروزتها", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if frame_file and uploaded_photos:
    st.write(f"✅ تم رفع {len(uploaded_photos)} صورة.")
    
    # معالجة الفريم مرة واحدة
    raw_frame = Image.open(frame_file)
    processed_frame = make_black_transparent(raw_frame)
    
    # معاينة أول صورة
    st.divider()
    st.subheader("👁️ معاينة النتيجة")
    sample_photo = Image.open(uploaded_photos[0]).convert("RGBA")
    sample_frame = processed_frame.resize(sample_photo.size, Image.Resampling.LANCZOS)
    sample_photo.alpha_composite(sample_frame)
    st.image(sample_photo, caption="شكل أول صورة بعد البروزة", width=600)

    if st.button("🚀 ابدأ معالجة الصور وتحميل ملف ZIP"):
        zip_buffer = io.BytesIO()
        
        # إنشاء ملف ZIP في الذاكرة
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            bar = st.progress(0)
            status = st.empty()
            
            for i, photo_file in enumerate(uploaded_photos):
                # فتح ومعالجة كل صورة
                photo = Image.open(photo_file).convert("RGBA")
                # تغيير مقاس الفريم ليناسب الصورة
                resized_frame = processed_frame.resize(photo.size, Image.Resampling.LANCZOS)
                photo.alpha_composite(resized_frame)
                
                # تحويل لـ RGB وحفظ في الـ ZIP
                final_img = photo.convert("RGB")
                img_byte_arr = io.BytesIO()
                final_img.save(img_byte_arr, format='JPEG', quality=85)
                
                zip_file.writestr(photo_file.name, img_byte_arr.getvalue())
                
                # تحديث الـ UI
                bar.progress((i + 1) / len(uploaded_photos))
                status.text(f"جاري معالجة: {photo_file.name}")

        st.success("✨ تم الانتهاء من جميع الصور!")
        st.download_button(
            label="📥 تحميل كل الصور المبروزة (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="Branded_Photos.zip",
            mime="application/zip"
        )
else:
    st.warning("يرجى رفع الفريم والصور للبدء.")