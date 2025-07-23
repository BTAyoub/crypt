# استخدم صورة تحتوي على Python 3.11
FROM python:3.11-slim

# إعداد مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ ملفات المشروع داخل الحاوية
COPY . .

# تثبيت الاعتماديات
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python", "main.py"]
