import os
import re
from flask import Flask, request, jsonify, make_response
from github import Github
from github import InputGitAuthor
import base64
import requests

# --- 1. الإعدادات الأساسية (قائمة المفاتيح الآمنة/الوهمية) ---
app = Flask(__name__)

# *** هذا هو مفتاح API للحساب الوهمي الذي سينشر المواقع ***
GITHUB_PATS_LIST = [
    "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" 
]

# --- نهاية الإعدادات ---

# 2. قالب موقع العميل (مُضمَّن) - يطابق المدخلات الجديدة
CUSTOMER_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{SITE_NAME}} | {{SITE_TYPE}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* تم دمج الألوان الرئيسية من الواجهة الأمامية هنا */
        :root {
            --primary-blue: #3B82F6; 
            --secondary-purple: #9333EA;
        }
        body { font-family: 'Inter', sans-serif; background-color: #f8f8f8; color: #1F2937; }
        .product-card { box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1); }
        .cta-button { background-image: linear-gradient(to right, var(--primary-blue), var(--secondary-purple)); }
    </style>
</head>
<body class="antialiased">
    <main class="max-w-xl mx-auto p-4 md:p-8 space-y-8">
        <header class="text-center pt-8 pb-4">
            <h1 class="text-4xl font-extrabold text-gray-900">{{SITE_NAME}}</h1>
            <p class="text-lg text-gray-500 mt-2">وجهتك الأولى لـ {{PRODUCT_CATEGORY}}</p>
        </header>

        <section class="product-card bg-white rounded-xl overflow-hidden">
            <img src="{{PRODUCT_IMAGE_URL_1}}" alt="{{PRODUCT_TITLE_1}}" class="w-full h-80 object-cover">
            <div class="p-6 space-y-4">
                <h2 class="text-3xl font-bold text-gray-800">{{PRODUCT_TITLE_1}}</h2>
                <span class="inline-block px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-700">متاح للبيع الآن!</span>
                <p class="text-gray-600 leading-relaxed border-t pt-4">{{PRODUCT_DESC_1}}</p>
                <div class="flex items-center justify-between pt-4">
                    <span class="text-3xl font-extrabold text-indigo-600">{{PRODUCT_PRICE_1}}</span>
                    
                    {{BUY_BUTTON_HTML}}
                    
                </div>
                {{WHATSAPP_BUTTON_HTML}}
            </div>
        </section>

        <footer class="text-center pt-4 border-t border-gray-300">
            <p class="text-sm text-gray-500 mb-2">تابعنا على:</p>
            <div class="flex justify-center space-x-4 space-x-reverse">
                {{INSTAGRAM_LINK_HTML}}
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
    # إعداد CORS
    response = make_response(jsonify({}))
    response.headers['Access-Control-Allow-Origin'] = '*' 

    data = request.get_json()
    if not data:
        response.set_data(jsonify({"status": "error", "message": "No data received."}).get_data())
        return response

    # --- 3.1. تجهيز البيانات وتوليد اسم المستودع ---
    site_name_raw = data.get('site_name', 'UnnamedSite')
    repo_name = re.sub(r'[^a-zA-Z0-9-]', '-', site_name_raw.strip()).lower()
    if not repo_name or len(repo_name) < 4:
        repo_name = "webgen-site-" + str(os.urandom(4).hex()) 
    
    # --- 3.2. بناء أزرار وروابط التواصل بشكل ديناميكي ---
    
    # زر رابط الشراء المباشر
    buy_link = data.get('buy_link', '#')
    buy_button_html = ''
    if buy_link and buy_link != '#':
         buy_button_html = f'''
             <a href="{buy_link}" target="_blank" class="w-1/2 text-center py-3 text-white font-bold rounded-lg cta-button hover:bg-indigo-700 transition shadow-lg">
                 اشترِ الآن
             </a>
         '''
    
    # زر الواتساب
    whatsapp_link = data.get('whatsapp_link')
    whatsapp_button_html = ''
    if whatsapp_link:
        whatsapp_button_html = f'''
            <a href="{whatsapp_link}" target="_blank" class="block w-full text-center py-3 text-white font-bold rounded-lg bg-green-500 hover:bg-green-600 transition">
                تواصل عبر واتساب
            </a>
        '''

    # رابط انستغرام في الفوتر
    instagram_link = data.get('instagram_link')
    instagram_link_html = ''
    if instagram_link:
        instagram_link_html = f'''
            <a href="{instagram_link}" target="_blank" class="text-gray-500 hover:text-pink-500">Instagram</a>
        '''

    # --- 3.3. تخصيص قالب HTML ---
    final_html = CUSTOMER_TEMPLATE
    final_html = final_html.replace('{{SITE_NAME}}', site_name_raw)
    final_html = final_html.replace('{{SITE_TYPE}}', data.get('site_type', 'متجر إلكتروني'))
    final_html = final_html.replace('{{PRODUCT_CATEGORY}}', data.get('product_category', 'منتجات رائعة'))
    final_html = final_html.replace('{{PRODUCT_TITLE_1}}', data.get('product_title', 'منتج رائع'))
    final_html = final_html.replace('{{PRODUCT_DESC_1}}', data.get('product_desc', 'وصف حصري ومميز.'))
    final_html = final_html.replace('{{PRODUCT_PRICE_1}}', data.get('product_price', '50 SAR'))
    final_html = final_html.replace('{{PRODUCT_IMAGE_URL_1}}', data.get('product_image_url', "https://via.placeholder.com/600x400.png?text=Product+Image"))
    
    # استبدال الأزرار الديناميكية
    final_html = final_html.replace('{{BUY_BUTTON_HTML}}', buy_button_html)
    final_html = final_html.replace('{{WHATSAPP_BUTTON_HTML}}', whatsapp_button_html)
    final_html = final_html.replace('{{INSTAGRAM_LINK_HTML}}', instagram_link_html)
    
    
    # --- 3.4. حلقة تبديل المفاتيح والمحاولة (لدينا مفتاح واحد الآن) ---
    last_error = None
    
    for pat in GITHUB_PATS_LIST:
        try:
            # الاتصال بـ GitHub باستخدام المفتاح الحالي
            g = Github(pat)
            user = g.get_user()
            
            # 1. إنشاء المستودع (Repository)
            repo = user.create_repo(repo_name, private=False, auto_init=False)
            
            # 2. رفع ملف index.html
            commit_message = f"Initial commit for {site_name_raw} by WebGen AI"
            repo.create_file("index.html", commit_message, final_html.encode('utf-8'))
            
            # 3. بناء رابط الموقع باستخدام اسم المستخدم الناجح
            final_url = f"https://{user.login}.github.io/{repo_name}/"
            
            # النجاح! الخروج من الدالة بعد الرفع
            print(f"SUCCESS: Site published using PAT ending in '...{pat[-4:]}'")
            response.set_data(jsonify({"status": "success", "url": final_url}).get_data())
            return response 

        except Exception as e:
            # فشل المفتاح الحالي
            last_error = str(e)
            print(f"FAILED: PAT ending in '...{pat[-4:]}' failed. Retrying. Error: {last_error}")
            continue 

    # إذا خرجنا من الحلقة دون نجاح (فشلت جميع المفاتيح)
    print(f"FATAL: All API keys failed. Last error: {last_error}")
    response.set_data(jsonify({"status": "error", "message": f"خطأ: فشلت جميع مفاتيح الـ API في النشر. {last_error}"}).get_data())
    return response

# 4. تشغيل الخادم
if __name__ == '__main__':
    print(f"API Server running at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
