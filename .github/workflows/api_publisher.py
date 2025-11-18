import os
import json
import requests
import re
import time
import base64
import glob 
from urllib.parse import quote_plus

# --- 1. الإعدادات الأساسية ---
# يتم تحميل القيم من متغيرات البيئة التي حددناها في publish.yml
GITHUB_PAT = os.environ.get('DUMMY_GITHUB_PAT')
REPO_OWNER = os.environ.get('REPO_OWNER')
REQUESTS_DIR = 'requests' 

# --- 2. وظائف مساعدة ---
def slugify(text):
    """تحويل النص العربي إلى رابط إنجليزي مقبول (Slug)"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text) 
    text = re.sub(r'[\s]+', '-', text)       
    return text.strip('-')

def create_github_repo(repo_name, description):
    """إنشاء مستودع جديد باستخدام GitHub API تحت اسم المالك المحدد (REPO_OWNER)"""
    # يجب أن تتضمن هذه النقطة المالك الصحيح
    url = f"https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "has_issues": False,
        "has_projects": False,
        "has_wiki": False,
        "auto_init": False
    }
    
    # إذا كان الـ PAT ينتمي لحساب GenAI210، فستُنشأ باسمه تلقائياً.
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        print(f"✅ تم إنشاء المستودع بنجاح: {REPO_OWNER}/{repo_name}")
        return True
    elif response.status_code == 422 and "name already exists" in response.text:
        print(f"⚠️ المستودع {REPO_OWNER}/{repo_name} موجود بالفعل. سنستخدمه.")
        return True
    else:
        print(f"❌ فشل إنشاء المستودع {REPO_OWNER}/{repo_name}. الحالة: {response.status_code}")
        print("الاستجابة:", response.json())
        # هذه الرسالة ستظهر إذا كان الـ PAT غير صحيح أو لا يملك صلاحية repo
        raise Exception(f"فشل إنشاء المستودع: {response.text}")

def upload_file_to_repo(repo_name, file_path, file_content, commit_message):
    """رفع الملف إلى المستودع الجديد"""
    # نستخدم المالك الصحيح هنا لضمان رفع الملف للمكان الصحيح
    url = f"https://api.github.com/repos/{REPO_OWNER}/{repo_name}/contents/{file_path}"
    content_base64 = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": commit_message,
        "content": content_base64
    }
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f"✅ تم رفع/تحديث الملف: {file_path}")
        return True
    else:
        print(f"❌ فشل رفع الملف: {file_path}. الحالة: {response.status_code}")
        print("الاستجابة:", response.json())
        raise Exception(f"فشل رفع الملف: {response.text}")

def enable_github_pages(repo_name):
    """تفعيل GitHub Pages على المستودع الجديد"""
    # نستخدم المالك الصحيح هنا لتفعيل الصفحات
    url = f"https://api.github.com/repos/{REPO_OWNER}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("✅ تم تفعيل GitHub Pages بنجاح.")
        return True
    elif response.status_code == 409: 
        print("⚠️ GitHub Pages مفعلة بالفعل أو في طور التفعيل.")
        return True
    else:
        print(f"❌ فشل تفعيل GitHub Pages. الحالة: {response.status_code}")
        print("الاستجابة:", response.json())
        return False
        
# --- 3. المنطق الرئيسي ---

def main():

    print("--- WebGen AI Publisher Started ---")

    if not GITHUB_PAT or not REPO_OWNER:
        print("❌ خطأ: لم يتم تحميل مفتاح DUMMY_GITHUB_PAT أو REPO_OWNER من البيئة.")
        print("الرجاء التحقق من إعدادات Secrets و Environment Variables في publish.yml.")
        return

    # 1. قراءة بيانات طلب النشر
    try:
        print("\n--- 1. قراءة بيانات طلب النشر ---")
        time.sleep(2) 
        
        # البحث عن أحدث ملف JSON
        search_path = os.path.join(REQUESTS_DIR, '*.json')
        all_requests = glob.glob(search_path)
        
        if not all_requests:
            print(f"❌ خطأ: لم يتم العثور على ملفات طلب JSON في المسار '{search_path}'.")
            return

        # اختيار أحدث ملف تم رفعه بناءً على تاريخ تعديله
        newest_file_path = max(all_requests, key=os.path.getmtime) 
        
        print(f"✅ تم تحديد ملف الطلب الجديد: {newest_file_path}")

        # قراءة البيانات
        with open(newest_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    except Exception as e:
        print(f"❌ فشل قراءة ملف الطلب. الخطأ هو: {e}")
        return

    # استخراج البيانات
    site_name = data.get('site_name', 'موقع تجريبي')
    product_title = data.get('product_title', 'منتج فريد')
    product_price = data.get('product_price', '100 SAR')
    product_image_url = data.get('product_image_url', 'https://via.placeholder.com/600x800.png?text=Product+Image')
    product_desc = data.get('product_desc', 'وصف قصير للمنتج المميز الذي تقدمه.')
    buy_link = data.get('buy_link', '#')
    whatsapp_link = data.get('whatsapp_link', '#')


    # توليد اسم المستودع (Slug)
    repo_slug = slugify(site_name)
    NEW_REPO_NAME = repo_slug if repo_slug else 'webgen-site-' + str(int(time.time()))

    # 2. إنشاء المستودع الجديد
    print(f"\n--- 2. إنشاء المستودع '{NEW_REPO_NAME}' تحت المالك {REPO_OWNER} ---")
    if not create_github_repo(NEW_REPO_NAME, f"موقع لمنتج: {product_title}"):
        return

    # 3. قراءة قالب HTML وتعبئته
    print("\n--- 3. تجهيز قالب HTML ---")
    try:
        # هنا يتم استخدام قالب مُضمن داخل السكربت لتجنب تعقيد القراءة من ملف خارجي
        html_template = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{product_title} | {site_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Cairo', sans-serif;
            background-color: #f7f7f7;
        }}
        .product-image {{
            object-fit: cover;
            border-radius: 1.5rem;
        }}
        .cta-button {{
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
        }}
        .cta-button:hover {{
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.6);
            transform: translateY(-2px);
        }}
    </style>
</head>
<body class="antialiased">

    <div class="max-w-7xl mx-auto p-4 md:p-10 min-h-screen flex items-center justify-center">

        <div class="bg-white rounded-3xl shadow-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-0">
            
            <div class="relative h-96 lg:h-auto">
                <img src="{product_image_url}" alt="{product_title}" class="product-image w-full h-full">
            </div>

            <div class="p-6 md:p-12 space-y-8 flex flex-col justify-center">

                <div class="space-y-4">
                    <span class="text-sm font-semibold text-red-500 uppercase tracking-widest">عرض حصري</span>
                    <h1 class="text-4xl lg:text-5xl font-extrabold text-gray-900">{product_title}</h1>
                    <p class="text-2xl font-bold text-gray-800 border-b pb-4">{product_price}</p>
                    <p class="text-gray-600 leading-relaxed text-lg">{product_desc}</p>
                </div>

                <div class="space-y-4 pt-6">
                    
                    {f'<a href="{buy_link}" target="_blank" class="w-full inline-flex items-center justify-center bg-red-600 text-white text-xl font-bold py-4 rounded-xl cta-button">شراء المنتج الآن</a>' if buy_link and buy_link != '#' else ''}
                    
                    {f'<a href="{whatsapp_link}" target="_blank" class="w-full inline-flex items-center justify-center bg-green-500 text-white text-xl font-bold py-4 rounded-xl hover:bg-green-600 mt-2">تواصل واتساب</a>' if whatsapp_link and whatsapp_link != '#' else ''}

                    <p class="text-sm text-center text-gray-500 pt-4">الدفع آمن والتوصيل سريع. اطلب الآن قبل نفاذ الكمية.</p>
                </div>
                
                <footer class="text-center text-xs text-gray-400 pt-8 mt-auto">
                    تم إنشاء هذا الموقع بواسطة WebGen AI - {site_name}
                </footer>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
    except Exception as e:
        print(f"❌ خطأ في تجهيز قالب HTML: {e}")
        return

    # 4. رفع ملف index.html إلى المستودع الجديد
    print("\n--- 4. رفع ملف index.html ---")
    upload_file_to_repo(
        repo_name=NEW_REPO_NAME,
        file_path="index.html",
        file_content=html_template,
        commit_message=f"WebGen: Initial commit for {product_title}"
    )

    # 5. تفعيل GitHub Pages
    print("\n--- 5. تفعيل GitHub Pages ---")
    time.sleep(5) 
    enable_github_pages(NEW_REPO_NAME)
    

    final_url = f"https://{REPO_OWNER}.github.io/{NEW_REPO_NAME}/"
    print("\n==============================================")
    print(f"✅ تم النشر بنجاح! رابط موقع العميل: {final_url}")
    print("==============================================")


if __name__ == "__main__":
    main()
