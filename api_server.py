import os
import re
from flask import Flask, request, jsonify, make_response
from github import Github
from github import InputGitAuthor
import base64
import requests

# --- 1. الإعدادات الأساسية والأمان ---
app = Flask(__name__)

# *** الأمان: يتم قراءة المفتاح من متغير البيئة المخفي في Termux ***
GITHUB_PAT = os.environ.get('GITHUB_PAT') 

# اسم المستخدم الذي سيظهر في رابط GitHub Pages 
GITHUB_USERNAME = "Rxwab" 

if not GITHUB_PAT:
    print("FATAL ERROR: مفتاح GITHUB_PAT مفقود. يرجى مراجعة إعداد .bashrc")
    exit()
# --- نهاية الإعدادات ---

# 2. قالب موقع العميل (مُضمَّن)
CUSTOMER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{SITE_NAME}} | متجر {{SITE_TYPE}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8f8f8; color: #1F2937; }
        .product-card { box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1); }
    </style>
</head>
<body class="antialiased">
    <main class="max-w-xl mx-auto p-4 md:p-8 space-y-8">
        <header class="text-center pt-8 pb-4">
            <h1 class="text-4xl font-extrabold text-gray-900">{{SITE_NAME}}</h1>
            <p class="text-lg text-gray-500 mt-2">وجهتك الأولى لـ {{SITE_TYPE}}</p>
        </header>

        <section class="product-card bg-white rounded-xl overflow-hidden">
            <img src="{{PRODUCT_IMAGE_URL_1}}" alt="{{PRODUCT_TITLE_1}}" class="w-full h-80 object-cover">
            <div class="p-6 space-y-4">
                <h2 class="text-3xl font-bold text-gray-800">{{PRODUCT_TITLE_1}}</h2>
                <span class="inline-block px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-700">متاح للبيع الآن!</span>
                <p class="text-gray-600 leading-relaxed border-t pt-4">{{PRODUCT_DESC_1}}</p>
                <div class="flex items-center justify-between pt-4">
                    <span class="text-3xl font-extrabold text-indigo-600">{{PRODUCT_PRICE_1}}</span>
                    <a href="{{BUY_LINK_1}}" target="_blank" class="w-1/2 text-center py-3 text-white font-bold rounded-lg bg-indigo-600 hover:bg-indigo-700 transition shadow-lg">
                        اشترِ الآن
                    </a>
                </div>
                <a href="{{WHATSAPP_LINK}}" target="_blank" class="block w-full text-center py-3 text-white font-bold rounded-lg bg-green-500 hover:bg-green-600 transition">
                    تواصل عبر واتساب
                </a>
            </div>
        </section>

        <footer class="text-center pt-4 border-t border-gray-300">
            <p class="text-sm text-gray-500 mb-2">تابعنا على:</p>
            <div class="flex justify-center space-x-4 space-x-reverse">
                <a href="{{INSTAGRAM_LINK}}" target="_blank" class="text-gray-500 hover:text-pink-500">Instagram</a>
            </div>
            <p class="text-xs text-gray-400 mt-4">تم الإنشاء بواسطة WebGen AI | 2025</p>
        </footer>
    </main>
</body>
</html>
"""

# 3. دالة النشر الرئيسية
@app.route('/api/publish', methods=['POST'])
def publish_site():
    # إعداد CORS للسماح لملف index.html بالوصول إلى هذا الخادم
    response = make_response(jsonify({}))
    response.headers['Access-Control-Allow-Origin'] = '*' 

    data = request.get_json()
    if not data:
        response.set_data(jsonify({"status": "error", "message": "No data received."}).get_data())
        return response

    try:
        # 3.1. تجهيز البيانات وتوليد اسم المستودع
        site_name_raw = data.get('site_name', 'UnnamedSite')
        repo_name = re.sub(r'[^a-zA-Z0-9-]', '-', site_name_raw.strip()).lower()
        if not repo_name or len(repo_name) < 4:
             repo_name = "webgen-site-" + str(os.urandom(4).hex()) 
        
        # 3.2. معالجة الصور (Placeholder)
        image_url = "https://via.placeholder.com/600x400.png?text=Product+Image"
        
        # 3.3. تخصيص قالب HTML
        final_html = CUSTOMER_TEMPLATE
        final_html = final_html.replace('{{SITE_NAME}}', site_name_raw)
        final_html = final_html.replace('{{SITE_TYPE}}', data.get('site_type', 'متجر إلكتروني'))
        final_html = final_html.replace('{{PRODUCT_TITLE_1}}', data.get('product_title', 'منتج رائع'))
        final_html = final_html.replace('{{PRODUCT_DESC_1}}', data.get('product_desc', 'وصف حصري ومميز.'))
        final_html = final_html.replace('{{PRODUCT_PRICE_1}}', data.get('product_price', '50 SAR'))
        final_html = final_html.replace('{{PRODUCT_IMAGE_URL_1}}', image_url)
        final_html = final_html.replace('{{WHATSAPP_LINK}}', data.get('whatsapp_link', '#'))
        final_html = final_html.replace('{{INSTAGRAM_LINK}}', data.get('instagram_link', '#'))
        final_html = final_html.replace('{{BUY_LINK_1}}', "#") 

        # 3.4. الاتصال بـ GitHub
        g = Github(GITHUB_PAT)
        user = g.get_user()

        # 3.5. إنشاء المستودع (Repository)
        repo = user.create_repo(repo_name, private=False, auto_init=False)
        
        # 3.6. رفع ملف index.html
        commit_message = "Initial commit by WebGen AI Builder"
        repo.create_file("index.html", commit_message, final_html.encode('utf-8'))
        
        # 3.7. بناء رابط الموقع
        final_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
        
        # الرد بالرابط
        response.set_data(jsonify({"status": "success", "url": final_url}).get_data())
        return response

    except Exception as e:
        print(f"An error occurred during GitHub operation: {e}")
        response.set_data(jsonify({"status": "error", "message": f"خطأ في عملية النشر: {str(e)}"}).get_data())
        return response

# 4. تشغيل الخادم
if __name__ == '__main__':
    print(f"API Server running at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
