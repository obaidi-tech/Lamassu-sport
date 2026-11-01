"""Offline stand-in for the AI writer, used only for tests and the demo site.
Returns Arabic text for the FICTIONAL test headlines in make_fixtures.py. Not real news."""
import json
import re

AR = {
    "Arsenal confirm Saka fitness ahead of Brighton trip": "أرسنال يؤكد جاهزية ساكا قبل مواجهة برايتون",
    "Liverpool beat Aston Villa 3-1 to stay top of Premier League": "ليفربول يهزم أستون فيلا 3-1 ويحافظ على صدارة الدوري الإنجليزي",
    "Manchester City name new sporting director": "مانشستر سيتي يعيّن مديراً رياضياً جديداً",
    "Chelsea manager says squad needs time after Newcastle draw": "مدرب تشيلسي يطلب الصبر بعد التعادل مع نيوكاسل",
    "Real Madrid edge Sevilla 2-1 at the Bernabeu": "ريال مدريد يتجاوز إشبيلية 2-1 في البرنابيو",
    "Atletico Madrid extend Simeone contract to 2028": "أتلتيكو مدريد يمدد عقد سيميوني حتى 2028",
    "Villarreal striker ruled out for six weeks with hamstring injury": "مهاجم فياريال يغيب ستة أسابيع بسبب إصابة عضلية",
    "Bayern Munich thrash Stuttgart 5-0 in Bundesliga": "بايرن ميونخ يكتسح شتوتغارت 5-0 في الدوري الألماني",
    "Dortmund appoint former academy coach as assistant": "دورتموند يرقّي مدرب أكاديميته إلى الجهاز الفني",
    "Leverkusen captain signs new deal until 2030": "قائد ليفركوزن يوقّع عقداً جديداً حتى 2030",
    "Inter Milan go top of Serie A after win over Lazio": "إنتر ميلان يعتلي صدارة الدوري الإيطالي بعد الفوز على لاتسيو",
    "Juventus confirm knee surgery for defender": "يوفنتوس يعلن خضوع مدافعه لجراحة في الركبة",
    "Napoli and AC Milan share points in 1-1 draw": "نابولي وميلان يتقاسمان النقاط بتعادل 1-1",
    "PSG beat Marseille 3-0 in Le Classique": "باريس سان جيرمان يهزم مارسيليا 3-0 في الكلاسيكو الفرنسي",
    "Monaco unveil new training centre investment": "موناكو يعلن استثماراً جديداً في مركز التدريب",
    "Lyon sack coach after five straight Ligue 1 defeats": "ليون يقيل مدربه بعد خمس هزائم متتالية",
    "FIFA publishes revised calendar for international windows": "الفيفا يعتمد روزنامة جديدة للفترات الدولية",
    "UEFA opens disciplinary case after Europa League match": "اليويفا يفتح تحقيقاً انضباطياً بعد مباراة في الدوري الأوروبي",
    "IOC confirms host selection timeline for 2036 Olympics": "اللجنة الأولمبية الدولية تحدد مراحل اختيار مستضيف أولمبياد 2036",
    "Asian Football Confederation announces Champions League draw date": "الاتحاد الآسيوي يحدد موعد قرعة دوري الأبطال",
    "CONMEBOL sets dates for Copa Libertadores final": "كونميبول يحدد موعد نهائي كأس ليبرتادوريس",
    "World Athletics approves new competition rules": "الاتحاد الدولي لألعاب القوى يعتمد قواعد منافسة جديدة",
    "FIBA unveils qualifying format for basketball World Cup": "فيبا يكشف نظام تصفيات كأس العالم لكرة السلة",
    "Lakers beat Celtics 118-112 behind LeBron James": "ليكرز يتفوق على سلتيكس 118-112 بقيادة ليبرون جيمس",
    "Wembanyama posts triple-double in Spurs win": "ويمبانياما يسجل ثلاثية مزدوجة في فوز سبيرز",
    "Nuggets sign veteran guard to two-year deal": "ناغتس يتعاقد مع لاعب خبير لموسمين",
    "Knicks extend winning streak to seven games": "نيكس يرفع سلسلة انتصاراته إلى سبع مباريات",
    "Sinner wins Paris Masters title": "سينر يتوج بلقب دورة باريس للأساتذة",
    "Sabalenka withdraws from WTA event with illness": "سابالينكا تنسحب من بطولة للمحترفات بسبب المرض",
    "Verstappen takes pole for Brazilian Grand Prix": "فيرستابن ينطلق أولاً في سباق جائزة البرازيل الكبرى",
    "Norris says McLaren upgrades are working": "نوريس: تحديثات ماكلارين تؤتي ثمارها",
    "Kenyan runner breaks course record at marathon": "عداء كيني يحطم الرقم القياسي لمسار الماراثون",
    "Diamond League final schedule announced": "الإعلان عن جدول نهائي الدوري الماسي لألعاب القوى",
    "Usyk to defend heavyweight titles in Riyadh": "أوسيك يدافع عن ألقاب الوزن الثقيل في الرياض",
    "UFC confirms main event for December card": "يو إف سي يؤكد النزال الرئيسي لأمسية ديسمبر",
    "Ryder Cup captains named for next edition": "تسمية قائدي فريقي كأس رايدر للنسخة المقبلة",
    "India beat Australia in first Test match": "الهند تهزم أستراليا في أول اختبار للكريكيت",
    "Six Nations fixtures released for 2027": "نشر جدول بطولة الأمم الست للرغبي 2027",
    "Pogacar confirms Tour de France participation": "بوغاتشار يؤكد مشاركته في طواف فرنسا",
    "Swimming world record falls in short course meet": "تحطيم رقم عالمي في السباحة بالحوض القصير",
    "MotoGP champion signs contract extension": "بطل موتو جي بي يمدد عقده",
    "Chiefs beat Bills in NFL thriller": "تشيفس يتفوق على بيلز في مباراة مثيرة بدوري كرة القدم الأمريكية",
    "Al-Hilal win Saudi Pro League derby against Al-Nassr": "الهلال يفوز على النصر في ديربي الدوري السعودي",
    "Inter Miami reach MLS conference final": "إنتر ميامي يبلغ نهائي المنطقة في الدوري الأمريكي",
    "Flamengo clinch Brasileirao lead with win over Palmeiras": "فلامنغو يتصدر الدوري البرازيلي بالفوز على بالميراس",
    "Boca Juniors appoint new coach": "بوكا جونيورز يعيّن مدرباً جديداً",
    "Benfica beat Porto in Portuguese top-of-table clash": "بنفيكا يهزم بورتو في قمة الدوري البرتغالي",
    "Galatasaray extend lead in Turkey after derby win": "غلطة سراي يوسع الفارق في صدارة الدوري التركي",
    "Celtic and Rangers draw Old Firm derby": "سلتيك ورينجرز يتعادلان في ديربي غلاسكو",
    "Ajax hire new technical director": "أياكس يعيّن مديراً فنياً جديداً",
    "Al Ahly win Egyptian league clash against Zamalek": "الأهلي يفوز على الزمالك في الدوري المصري",
    "Wydad name new coach before African season": "الوداد يعيّن مدرباً جديداً قبل الموسم الأفريقي",
    "Liga MX final set after semi-final second legs": "اكتمال طرفي نهائي الدوري المكسيكي",
    "Al Sadd top Qatar Stars League after victory": "السد يتصدر دوري نجوم قطر",
    "Japan J-League title race goes to final day": "حسم لقب الدوري الياباني يتأجل إلى الجولة الأخيرة",
    "Former striker dies aged 71": "وفاة مهاجم دولي سابق عن 71 عاماً",
    "Study finds heading training linked to concussion risk in youth players": "دراسة تربط تدريبات ضرب الكرة بالرأس بخطر الارتجاج لدى الناشئين",
    "Athletes mental health programme launched by players union": "رابطة اللاعبين تطلق برنامجاً لدعم الصحة النفسية",
    "WADA publishes updated prohibited list": "الوكالة العالمية لمكافحة المنشطات تنشر قائمة المحظورات المحدثة",
    "Fact check: viral transfer video is fake, club says": "تحقق: نادٍ ينفي صحة فيديو متداول عن صفقة انتقال",
    "The Premier League's fixture pile-up is a warning nobody is heeding": "تكدس المباريات في الدوري الإنجليزي إنذار يتجاهله الجميع",
    "Why LaLiga's spending rules are reshaping Spanish football": "كيف تعيد قواعد الإنفاق تشكيل الكرة الإسبانية",
    "Women's football needs better grassroots pitches, not slogans": "كرة القدم النسائية تحتاج ملاعب لا شعارات",
    "The NBA's load management debate misses the point": "جدل إراحة اللاعبين في NBA يخطئ الهدف",
    "Olympic host cities need a new model": "المدن المستضيفة للأولمبياد تحتاج نموذجاً جديداً",
}


def fake_claude(system, prompt, cfg):
    if "duplicates" in prompt:
        rows = re.findall(r"^(\d+)\. \[\w+\] (.*)$", prompt, re.M)
        grp = [int(i) for i, t in rows if "Al-Hilal" in t or "الهلال" in t]
        return json.dumps({"duplicates": [grp] if len(grp) > 1 else []})
    head = re.search(r"العنوان: (.+)", prompt).group(1).strip()
    title = AR.get(head, head)
    pubs = re.findall(r"الناشر: ([^(|]+?) \(", prompt)
    who = "، ".join(dict.fromkeys(p.strip() for p in pubs[:3])) or "المصادر"
    if "مقالة رأي" in prompt:
        body = [f"يرى الكاتب أن {title} مسألة تستحق نقاشاً أوسع، ويعرض في مقاله أسباب ذلك وما يقترحه من حلول، "
                "مستنداً إلى ما شهده الموسم الحالي من تجارب. ويخلص إلى أن الاستمرار على النهج نفسه سيزيد المشكلة تعقيداً، "
                "داعياً الجهات المسؤولة إلى مراجعة سياساتها قبل الموسم المقبل."]
    else:
        invented = " وأشارت التقارير إلى فوز بنتيجة 4-0." if "Liverpool" in prompt else ""
        body = [f"{title}، بحسب ما أوردته {who}.{invented}",
                "وتناولت مصادر عدة الحدث خلال الساعات الماضية، واتفقت على تفاصيله الأساسية، فيما لم تصدر تفاصيل إضافية حتى الآن. "
                "ويأتي ذلك في توقيت حساس من الموسم، إذ تتقارب المنافسة وتزداد أهمية كل نتيجة وكل قرار.",
                "ويُنتظر أن تتضح الصورة أكثر خلال الأيام المقبلة مع صدور البيانات الرسمية من الجهات المعنية."]
    return json.dumps({"title": title, "excerpt": body[0][:160], "body": body, "tags": [],
                       "confidence": "high", "needs_review": False}, ensure_ascii=False)
