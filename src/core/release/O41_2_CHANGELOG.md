# O41.2 — Semantic Hardening + Egypt-First Decision Surface

## لماذا الإصدار
يعالج O41.2 العيوب التي ظهرت في Golden Run الحقيقي: ضعف local market evidence، product identity = Unspecified، malformed content topics، generic offer/sales naming، وصعوبة قراءة النتيجة الخام للمستخدم.

## التغييرات
- Egypt-first market research planning مع local evidence policy.
- تصنيف relevance للمصادر والأدلة (`local`, `regional`, `global_context`).
- قياس `local_source_count` و`local_evidence_count` وحدّ evidence boundary.
- تمرير local evidence boundary إلى Opportunity Candidates.
- Product Identity مشتق من نموذج الاستراتيجية؛ يمنع `Unspecified` في المسار الحقيقي.
- Product → Brand handoff يمرر `product_type` و`positioning_link`.
- تحسين توليد Content Topics لمنع الجمل المركبة/الملخبطه.
- Offer/Marketing/Sales تستخدم اسم المنتج/العرض بدل `Core Offer` العام.
- إضافة Arabic Decision Summary لنتيجة التشغيل.
- دعم `language=ar|en` عبر service/API/CLI/runtime.
- UI Console v1.6.0 يتيح اختيار لغة النتيجة ويعرض الملخص العربي أولًا.
- دليل عربي يوضح كيف تُقرأ النتائج وكيف تتحول إلى validation loop.

## حدود مهمة
- لا يوجد ادعاء بأن أي opportunity أصبحت مثبتة بمجرد حصولها على score.
- global signals تظل بحاجة إلى local validation عندما لا يكفي الدليل المصري.
- JSON الكامل يظل طبقة audit/debug وليس واجهة القرار الأولى.
