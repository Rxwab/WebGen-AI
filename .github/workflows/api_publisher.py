import os
import json
import requests
import re
import time

# --- 1. الإعدادات الأساسية ---

# قراءة المتغيرات من بيئة GitHub Actions
GITHUB_PAT = os.environ.get('DUMMY_GITHUB_PAT')
REPO_OWNER = os.environ.get('REPO_OWNER') # يجب أن يكون اسم المستخدم الخاص بك (Rxwab)

# مسار الملفات
JSON_FILE_PATH = '.github/workflows/publish_request.json'
TEMPLATE_FILE_PATH = '.github/workflows/template.html'

# --- 2. وظائف مساعدة ---

def slugify(text):
    """تحويل النص العربي إلى رابط إنجليزي مقبول (Slug)"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text) # إزالة الأحرف غير المسموح بها
    text = re.sub(r'[\s]+', '-', text)       # استبدال المسافات بـ '-'
    # يمكنك إضافة مكتبة خارجية مثل python-slugify لدعم أفضل للعربية إذا لزم الأمر
    return text.strip('-')

def create_github_repo(repo_name, description):
    """إنشاء مستودع جديد باستخدام GitHub API"""
    url = "https://api.github.com/user/repos"
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
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        print(f"✅ تم إنشاء المستودع بنجاح: {repo_name}")
        return True
    elif response.status_code == 422 and "name already exists" in response.text:
        print(f"⚠️ المستودع {repo_name} موجود بالفعل. سنستخدمه.")
        return True
    else:
        print(f"❌ فشل إنشاء المستودع {repo_name}. الحالة: {response.status_code}")
        print("الاستجابة:", response.json())
        raise Exception(f"فشل إنشاء المستودع: {response.text}")


def upload_file_to_repo(repo_name, file_path, file_content, commit_message):
    """رفع محتوى الملف إلى المستودع"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{repo_name}/contents/{file_path}"
    
    # GitHub API يتطلب Base64 للمحتوى
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
    """تفعيل GitHub Pages على المستودع المنشور"""
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
    
    # محاولة تفعيل الصفحات
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 201:
        print("✅ تم تفعيل GitHub Pages بنجاح.")
        return True
    elif response.status_code == 409: # يحدث إذا كانت الصفحات مفعلة بالفعل
        print("⚠️ GitHub Pages مفعلة بالفعل أو في طور التفعيل.")
        return True
    else:
        print(f"❌ فشل تفعيل GitHub Pages. الحالة: {response.status_code}")
        print("الاستجابة:", response.json())
        # قد لا نحتاج لرفع خطأ هنا لأن الرفع سيتم لاحقا، لكن الأفضل المحاولة.
        return False
        
# --- 3. المنطق الرئيسي ---

def main():
    import base64

    print("--- WebGen AI Publisher Started ---")

    if not GITHUB_PAT or not REPO_OWNER:
        print("❌ خطأ: لم يتم تحميل مفتاح DUMMY_GITHUB_PAT أو REPO_OWNER من البيئة.")
        print("الرجاء التحقق من إعدادات Secrets في GitHub Actions.")
        return

    # قراءة بيانات طلب النشر من ملف JSON
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ خطأ: ملف الطلب {JSON_FILE_PATH} غير موجود.")
        return
    except json.JSONDecodeError:
        print(f"❌ خطأ: ملف الطلب {JSON_FILE_PATH} فارغ أو غير صالح.")
        return

    # استخراج البيانات
    site_name = data.get('site_name', 'Default Site')
    product_title = data.get('product_title', 'منتج فريد')
    product_price = data.get('product_price', '100 SAR')
    product_image_url = data.get('product_image_url', 'https://via.placeholder.com/600x800.png?text=Product+Image')
    product_desc = data.get('product_desc', 'وصف قصير للمنتج المميز الذي تقدمه.')
    buy_link = data.get('buy_link', '#')
    whatsapp_link = data.get('whatsapp_link', '#')

    # توليد اسم المستودع (Slug)
    repo_slug = slugify(site_name)
    NEW_REPO_NAME = repo_slug if repo_slug else 'webgen-site-' + str(int(time.time()))

    # 1. إنشاء المستودع الجديد
    print(f"\n--- 1. إنشاء المستودع '{NEW_REPO_NAME}' ---")
    if not create_github_repo(NEW_REPO_NAME, f"موقع لمنتج: {product_title}"):
        return

    # 2. قراءة قالب HTML
    try:
        # نحن الآن في مسار .github/workflows. يجب أن نقرأ القالب من هذا المجلد.
        # لغرض التجربة، سنفترض وجود ملف template.html في نفس المجلد
        # يمكنك استبدال هذا برابط أو جلب القالب من ملف آخر
        
        # --- هذا هو محتوى قالب HTML الذي يجب أن تضعه في ملف template.html بنفس المجلد ---
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
        # --- نهاية محتوى قالب HTML ---

    except Exception as e:
        print(f"❌ خطأ في تجهيز قالب HTML: {e}")
        return

    # 3. رفع ملف index.html إلى المستودع الجديد
    print("\n--- 3. رفع ملف index.html ---")
    upload_file_to_repo(
        repo_name=NEW_REPO_NAME,
        file_path="index.html",
        file_content=html_template,
        commit_message=f"WebGen: Initial commit for {product_title}"
    )

    # 4. تفعيل GitHub Pages
    print("\n--- 4. تفعيل GitHub Pages ---")
    # ننتظر قليلاً لإعطاء GitHub وقتاً لمعالجة الرفع
    time.sleep(5) 
    enable_github_pages(NEW_REPO_NAME)
    
    # 5. تنظيف ملف الطلب (لإيقاف الـ Action من التكرار)
    print("\n--- 5. تنظيف ملف الطلب ---")
    upload_file_to_repo(
        repo_name=REPO_OWNER, 
        file_path=JSON_FILE_PATH,
        file_content="{}", 
        commit_message="WebGen: Cleared publish request"
    )
    
    final_url = f"https://{REPO_OWNER}.github.io/{NEW_REPO_NAME}/"
    print("\n==============================================")
    print(f"✅ تم النشر بنجاح! رابط موقع العميل: {final_url}")
    print("==============================================")


if __name__ == "__main__":
    main()
