// Translate the site's interface while leaving user-entered transaction data untouched.
(function () {
    const translations = {
        'Scout Sandou2': ['Scout Sandou2', 'كشافة صندوق 2'],
        '| صندوق الكشاف': '| Scout Treasury', '| Scout Treasury': '| صندوق الكشاف',
        'Toggle navigation': ['Toggle navigation', 'تبديل القائمة'],
        'Dashboard': ['Dashboard', 'لوحة التحكم'],
        'This Month': ['This Month', 'هذا الشهر'],
        '+ Income (وارد)': ['+ Income', '+ إيراد'],
        '- Expense (مصروف)': ['- Expense', '- مصروف'],
        'Income (وارد)': ['Income', 'إيراد'],
        'Expense (مصروف)': ['Expense', 'مصروف'],
        'Sign Out': ['Sign Out', 'تسجيل الخروج'],
        '⚜️ Scout Sandou2 Finance Manager • Designed for Troop Administration • 2026':
            ['⚜️ Scout Sandou2 Finance Manager • Designed for Troop Administration • 2026', '⚜️ مدير الشؤون المالية لصندوق الكشافة • لإدارة المجموعة الكشفية • 2026'],
        'Language': ['Language', 'اللغة'],
        'Close': ['Close', 'إغلاق'],
        'Scout Treasury - Sandou2': ['Scout Treasury - Sandou2', 'خزينة الكشافة - صندوق 2'],
        'Dashboard • Scout Sandou2 Finance': ['Dashboard • Scout Sandou2 Finance', 'لوحة التحكم • الشؤون المالية لصندوق الكشافة'],
        'Sign In - Scout Sandou2 Finance': ['Sign In - Scout Sandou2 Finance', 'تسجيل الدخول - الشؤون المالية لصندوق الكشافة'],
        'صندوق الكشاف • Money Management': ['Scout Treasury • Money Management', 'صندوق الكشاف • إدارة الأموال'],
        '⚜️ Scout Treasury Overview': ['⚜️ Scout Treasury Overview', '⚜️ نظرة عامة على خزينة الكشافة'],
        'Track income (من مين), manage expenses (لشو), and monitor real-time $ & ل.ل cash box balances.':
            ['Track income by source, manage expenses by purpose, and monitor real-time USD and LBP cash balances.',
                'تابع الإيرادات ومصادرها، وأدر المصروفات وأغراضها، وراقب أرصدة الدولار والليرة في الصندوق مباشرة.'],
        '📅 This Month (هذا الشهر)': ['📅 This Month', '📅 هذا الشهر'],
        '+ Add Income (وارد)': ['+ Add Income', '+ أضف إيراداً'],
        '- Add Expense (مصروف)': ['- Add Expense', '- أضف مصروفاً'],
        '$ Wallet / صندوق الدولار': ['Dollar Wallet', 'محفظة الدولار'],
        'ل.ل Wallet / صندوق الليرة': ['LBP Wallet', 'محفظة الليرة اللبنانية'],
        'Current Total Balance in Cash Box': ['Current cash balance', 'الرصيد النقدي الحالي'],
        'Total $ Incomes': ['Total USD income', 'إجمالي الإيرادات بالدولار'],
        'Total $ Expenses': ['Total USD expenses', 'إجمالي المصروفات بالدولار'],
        'Total ل.ل Incomes': ['Total LBP income', 'إجمالي الإيرادات بالليرة'],
        'Total ل.ل Expenses': ['Total LBP expenses', 'إجمالي المصروفات بالليرة'],
        'Date Range & Filter Transactions': ['Date range and transaction filters', 'نطاق التاريخ وتصفية المعاملات'],
        'Select dates or quick presets to inspect specific transaction periods':
            ['Choose dates or a preset to view transactions for a specific period', 'اختر التواريخ أو فترة جاهزة لعرض المعاملات خلالها'],
        'All Time': ['All Time', 'كل الفترات'],
        'Today': ['Today', 'اليوم'],
        'This Year': ['This Year', 'هذه السنة'],
        'From Date (من تاريخ)': ['From date', 'من تاريخ'],
        'To Date (إلى تاريخ)': ['To date', 'إلى تاريخ'],
        'Currency': ['Currency', 'العملة'],
        'All Currencies': ['All Currencies', 'كل العملات'],
        'Type': ['Type', 'النوع'],
        'All Types': ['All Types', 'كل الأنواع'],
        'Income (واردات)': ['Income', 'إيراد'],
        'Expense (مصاريف)': ['Expense', 'مصروف'],
        'Filter': ['Filter', 'تصفية'],
        'Reset Filters': ['Reset filters', 'إعادة ضبط عوامل التصفية'],
        'Summary for Selected Period': ['Summary for selected period', 'ملخص الفترة المحددة'],
        'From': ['From', 'من'],
        'to': ['to', 'إلى'],
        'Starting from': ['Starting from', 'ابتداءً من'],
        'Up to': ['Up to', 'حتى'],
        'All Time Overview': ['All-time overview', 'نظرة عامة على كل الفترات'],
        'Export CSV': ['Export CSV', 'تصدير CSV'],
        'Print Report': ['Print report', 'طباعة التقرير'],
        'Net Period Result ($):': ['Net result (USD):', 'صافي النتيجة (دولار):'],
        'Net Period Result (ل.ل):': ['Net result (LBP):', 'صافي النتيجة (ليرة):'],
        'Date': ['Date', 'التاريخ'],
        'Party / Purpose': ['Source / Purpose', 'المصدر / الغرض'],
        'Category': ['Category', 'الفئة'],
        'Amount': ['Amount', 'المبلغ'],
        'Notes': ['Notes', 'ملاحظات'],
        'Actions': ['Actions', 'الإجراءات'],
        'Income': ['Income', 'إيراد'],
        'Expense': ['Expense', 'مصروف'],
        'From who (من مين)': ['Source', 'المصدر'],
        'For what (السبب / الغاية)': ['Purpose', 'الغرض'],
        'Edit Transaction': ['Edit transaction', 'تعديل المعاملة'],
        'Delete Transaction': ['Delete transaction', 'حذف المعاملة'],
        'No transactions found for this selection': ['No transactions found for this selection', 'لا توجد معاملات ضمن التحديد'],
        'Try adjusting your date range or add your first transaction using the buttons above.':
            ['Try changing the date range or add your first transaction using the buttons above.',
                'جرّب تغيير نطاق التاريخ أو أضف أول معاملة باستخدام الأزرار أعلاه.'],
        'Incomes Breakdown ("From Who")': ['Income breakdown (source)', 'تفاصيل الإيرادات (المصدر)'],
        'From Who (من مين)': ['Source', 'المصدر'],
        'Source / Contributor': ['Source / Contributor', 'المصدر / المساهم'],
        'No income transactions found in this period': ['No income transactions found in this period', 'لا توجد إيرادات خلال هذه الفترة'],
        'Expenses Breakdown ("For What")': ['Expense breakdown (purpose)', 'تفاصيل المصروفات (الغرض)'],
        'For What (السبب / الغاية)': ['Purpose', 'الغرض'],
        'Troop Expense / Purchase': ['Troop expense / purchase', 'مصروفات المجموعة / المشتريات'],
        'No expense records found in this period': ['No expense records found in this period', 'لا توجد مصروفات خلال هذه الفترة'],
        'Add Income • وارد جديد': ['Add income', 'إضافة إيراد'],
        'Amount & Currency (المبلغ والعملة)': ['Amount and currency', 'المبلغ والعملة'],
        'From Who? (من مين / مصدر المال)': ['From whom? / Source', 'ممن؟ / مصدر الإيراد'],
        'Category (الفئة)': ['Category', 'الفئة'],
        'Date (التاريخ)': ['Date', 'التاريخ'],
        'Notes / Description (ملاحظات)': ['Notes / description', 'ملاحظات / وصف'],
        'Cancel': ['Cancel', 'إلغاء'],
        'Save Income': ['Save income', 'حفظ الإيراد'],
        'Add Expense • مصروف جديد': ['Add expense', 'إضافة مصروف'],
        'For What? (السبب / لشو اندفعت)': ['For what? / Purpose', 'لأي غرض؟ / سبب المصروف'],
        'Save Expense': ['Save expense', 'حفظ المصروف'],
        'Transaction Type': ['Transaction type', 'نوع المعاملة'],
        'Amount & Currency': ['Amount and currency', 'المبلغ والعملة'],
        'From Who / For What': ['Source / Purpose', 'المصدر / الغرض'],
        'Category': ['Category', 'الفئة'],
        'Update Record': ['Update record', 'تحديث السجل'],
        'Delete Transaction?': ['Delete transaction?', 'هل تريد حذف المعاملة؟'],
        'Are you sure you want to delete': ['Are you sure you want to delete', 'هل أنت متأكد من حذف'],
        ')? This cannot be undone.': ')? لا يمكن التراجع عن هذا الإجراء.',
        'Delete': ['Delete', 'حذف'],
        'Restricted Troop Access': ['Restricted troop access', 'دخول مخصص لقيادة المجموعة'],
        'Username': ['Username', 'اسم المستخدم'],
        'Password': ['Password', 'كلمة المرور'],
        'Show password': ['Show password', 'إظهار كلمة المرور'],
        'Hide password': ['Hide password', 'إخفاء كلمة المرور'],
        'Sign In to Sandou2': ['Sign in to Sandou2', 'تسجيل الدخول إلى صندوق 2'],
        'Troop Treasury Security • "كن مستعداً"': ['Troop treasury security • "Be Prepared"', 'أمان خزينة المجموعة • "كن مستعداً"'],
        'Please sign in to access Scout Money Management.':
            ['Please sign in to access Scout Money Management.', 'يرجى تسجيل الدخول للوصول إلى إدارة أموال الكشافة.'],
        'أهلاً وسهلاً بك في صندوق فوج الدورة': ['Welcome to the troop treasury', 'أهلاً وسهلاً بك في صندوق فوج الدورة'],
        'Invalid email or password. Access is restricted to authorized account only.':
            ['Invalid email or password. Access is restricted to the authorized account only.', 'البريد الإلكتروني أو كلمة المرور غير صحيحة. الدخول مخصص للحساب المعتمد فقط.'],
        'You have been logged out safely.': ['You have been logged out safely.', 'تم تسجيل خروجك بأمان.'],
        'Amount must be greater than zero.': ['Amount must be greater than zero.', 'يجب أن يكون المبلغ أكبر من صفر.'],
        'Invalid amount entered.': ['Invalid amount entered.', 'المبلغ المدخل غير صالح.'],
        'Please provide "From Who".': ['Please provide a source.', 'يرجى إدخال مصدر الإيراد.'],
        'Please provide "For What".': ['Please provide a purpose.', 'يرجى إدخال سبب المصروف.'],
        'Transaction not found.': ['Transaction not found.', 'لم يتم العثور على المعاملة.'],
        'Transaction updated successfully!': ['Transaction updated successfully!', 'تم تحديث المعاملة بنجاح!'],
        'Transaction deleted successfully.': ['Transaction deleted successfully.', 'تم حذف المعاملة بنجاح.'],
        'Monthly Dues (اشتراكات)': ['Monthly Dues', 'الاشتراكات الشهرية'],
        'Donation (تبرعات)': ['Donations', 'تبرعات'],
        'Fundraiser (ريع نشاط)': ['Fundraiser', 'ريع نشاط'],
        'Sponsorship (رعاية)': ['Sponsorship', 'رعاية'],
        'Camp Fees (رسوم مخيم)': ['Camp fees', 'رسوم المخيم'],
        'General (عام)': ['General', 'عام'],
        'Camping Equipment (عتاد وتجهيزات)': ['Camping equipment', 'معدات التخييم'],
        'Food & Snacks (تغذية)': ['Food & snacks', 'طعام ووجبات خفيفة'],
        'Transportation (مواصلات وبنزين)': ['Transportation', 'مواصلات ووقود'],
        'Troop Room Rent (إيجار المقر)': ['Troop room rent', 'إيجار مقر المجموعة'],
        'Printing & Badges (قرطاسية وشارات)': ['Printing & badges', 'طباعة وشارات'],
        'Uniforms (ألبسة كشفية)': ['Uniforms', 'الزي الكشفي'],
        'Maintenance (صيانة)': ['Maintenance', 'صيانة'],
        'Select or type': ['Select or type', 'اختر أو اكتب'],
        'Optional details...': ['Optional details...', 'تفاصيل اختيارية...'],
        'Optional details, receipt number...': ['Optional details, receipt number...', 'تفاصيل اختيارية، رقم الإيصال...'],
        'e.g. Leader Ahmad, Donor Name, Monthly Scout Dues':
            ['e.g. Leader Ahmad, donor name, monthly scout dues', 'مثال: القائد أحمد، اسم المتبرع، اشتراكات الكشافة الشهرية'],
        'e.g. Tent repairs, Bus transport, Food for camp, Uniforms':
            ['e.g. Tent repairs, bus transport, camp food, uniforms', 'مثال: إصلاح الخيام، نقل بالحافلة، طعام المخيم، الزي الكشفي']
    };

    const language = document.documentElement.lang === 'ar' ? 'ar' : 'en';
    const languageIndex = language === 'ar' ? 1 : 0;

    function translateText(value) {
        const trimmed = value.trim();
        if (Object.prototype.hasOwnProperty.call(translations, trimmed)) {
            const translated = translations[trimmed];
            return Array.isArray(translated) ? translated[languageIndex] : translated;
        }

        let match = trimmed.match(/^📅 This Month \((.+)\)$/);
        if (match) {
            const month = match[1].match(/^([A-Za-z]+) (\d{4})$/);
            let localizedMonth = match[1];
            if (month) {
                const parsed = new Date(`${month[1]} 1, ${month[2]}`);
                if (!Number.isNaN(parsed.getTime())) {
                    localizedMonth = `${new Intl.DateTimeFormat(language, { month: 'long' }).format(parsed)} ${month[2]}`;
                }
            }
            return language === 'ar' ? `📅 هذا الشهر (${localizedMonth})` : `📅 This Month (${localizedMonth})`;
        }

        match = trimmed.match(/^All Transactions \((\d+)\)$/);
        if (match) return language === 'ar' ? `كل المعاملات (${match[1]})` : `All Transactions (${match[1]})`;
        match = trimmed.match(/^Incomes \/ من مين \((\d+)\)$/);
        if (match) return language === 'ar' ? `الإيرادات (${match[1]})` : `Incomes (${match[1]})`;
        match = trimmed.match(/^Expenses \/ لشو \((\d+)\)$/);
        if (match) return language === 'ar' ? `المصروفات (${match[1]})` : `Expenses (${match[1]})`;
        match = trimmed.match(/^• \((\d+) transactions\)$/);
        if (match) return language === 'ar' ? `• (${match[1]} معاملة)` : `• (${match[1]} transactions)`;
        match = trimmed.match(/^(Income|Expenses) \((\$|ل\.ل)\) • (\d+) tx$/);
        if (match) {
            const kind = match[1] === 'Income' ? (language === 'ar' ? 'إيرادات' : 'Income') : (language === 'ar' ? 'مصروفات' : 'Expenses');
            const currency = match[2] === '$' ? (language === 'ar' ? 'دولار' : 'USD') : (language === 'ar' ? 'ليرة' : 'LBP');
            return `${kind} (${currency}) • ${match[3]} ${language === 'ar' ? 'معاملة' : 'tx'}`;
        }
        match = trimmed.match(/^(Income \(وارد\)|Expense \(مصروف\)) of (.+) added successfully!$/);
        if (match) {
            const income = match[1].startsWith('Income');
            if (language === 'ar') return `تمت إضافة ${income ? 'الإيراد' : 'المصروف'} بقيمة ${match[2]} بنجاح!`;
            return `${income ? 'Income' : 'Expense'} of ${match[2]} added successfully!`;
        }

        return value;
    }

    window.scoutTranslate = translateText;

    document.addEventListener('DOMContentLoaded', function () {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            const original = node.nodeValue;
            const translated = translateText(original);
            if (translated !== original) {
                const leading = original.match(/^\s*/)[0];
                const trailing = original.match(/\s*$/)[0];
                node.nodeValue = `${leading}${translated.trim()}${trailing}`;
            }
        }

        document.querySelectorAll('[placeholder], [title], [aria-label]').forEach(function (element) {
            ['placeholder', 'title', 'aria-label'].forEach(function (attribute) {
                if (element.hasAttribute(attribute)) {
                    element.setAttribute(attribute, translateText(element.getAttribute(attribute)));
                }
            });
        });

        document.querySelectorAll('datalist option').forEach(function (option) {
            option.value = translateText(option.value);
        });

        document.title = translateText(document.title);
    });
})();
