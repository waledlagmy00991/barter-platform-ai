# -*- coding: utf-8 -*-
"""
Generate 2000+ Egyptian-dialect trader ads with gold NER annotations.

Entities: MATERIAL (الخامة), QUANTITY (الكمية), LOCATION (المكان).

Data provenance (مصادر الداتا):
- The sentences are synthetic: written to mimic real Egyptian trader ads
  (OLX / Facebook trade groups / WhatsApp dealer groups style), with the
  spelling mistakes Egyptians actually type (ى/ي, ة/ه, hamza dropped or
  moved, doubled letters), market shorthand (شيكارة, سن, مجروش, سكراب,
  خرازة, أبلكاش), Arabic-Indic (٥٠) and Western (50) digits, decimals,
  and number words (خمسين, تلتمية).
- Entity offsets are computed programmatically at generation time, so the
  annotation is exact (a Label-Studio-format export of the same data is in
  data/labelstudio_tasks.json).
- ~10% of sentences have no LOCATION and ~5% have no QUANTITY on purpose,
  so the model learns that fields can be absent.

Output: data/{train,dev,test}.jsonl + data/labelstudio_tasks.json
"""
import json
import random
from pathlib import Path

random.seed(42)

OUT = Path(__file__).parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- vocab
MATERIALS = {
    "حديد": ["حديد", "الحديد", "حديد تسليح", "حديد مسلح", "حدبد",
             "حديد عز", "حديد المصريين"],
    "حديد خردة": ["حديد خردة", "خردة حديد", "حديد سكراب", "سكراب حديد",
                  "حديد خرده", "خرده حديد", "خردة", "خرده"],
    "صاج": ["صاج", "الصاج", "ألواح صاج", "الواح صاج", "صاج مجلفن",
            "صاج معرج"],
    "استانلس ستيل": ["استانلس", "استانلس ستيل", "ستانلس ستيل",
                     "استانلس ستيل 304"],
    "خشب": ["خشب", "الخشب", "خشب زان", "خشب سويد", "خشب موسكي",
            "خشب أبيض", "خشب ابيض", "خشب أرز", "خشب ارز", "خشب أرو",
            "خشب ارو"],
    "أبلكاش": ["أبلكاش", "ابليكاش", "البلكاش", "خشب أبلكاش",
               "خشب ابلكاش"],
    "MDF": ["MDF", "mdf", "ام دي اف", "أم دي أف", "خشب MDF",
            "الواح MDF", "الواح ام دي اف"],
    "بلاستيك": ["بلاستيك", "البلاستيك", "بلاستيك مجروش", "مجروش بلاستيك",
                "بلاستيك مستعمل", "بلاستك", "بلاستيك خرازة", "خرازة",
                "بلاستيك PET", "بلاستيك pet", "PET مجروش"],
    "ألومنيوم": ["ألومنيوم", "الومنيوم", "ألمونيوم", "المونيوم",
                 "الألومنيوم", "المونيا", "ألومنيوم خردة", "الومنيوم خرده"],
    "نحاس": ["نحاس", "النحاس", "نحاس أحمر", "نحاس احمر", "كابلات نحاس",
             "نحاس خردة", "نحاس خرده", "سلك نحاس"],
    "رصاص": ["رصاص", "الرصاص", "رصاص خردة", "رصاص سكراب"],
    "أسمنت": ["أسمنت", "اسمنت", "الأسمنت", "الاسمنت", "أسمنت مقاوم",
              "اسمنت مقاوم", "أسمنت أسود", "اسمنت اسود", "أسمنت أبيض",
              "اسمنت ابيض", "شيكارة أسمنت", "شكارة اسمنت"],
    "جبس": ["جبس", "الجبس", "جبس بورد", "جبسوم بورد"],
    "رمل": ["رمل", "الرمل", "رملة", "رمل ناعم", "رمل خشن", "رمل زلط"],
    "زلط": ["زلط", "الزلط", "سن", "سن واحد", "سن 1", "زلط كسر",
            "سن رقم 1"],
    "طوب": ["طوب", "الطوب", "طوب أحمر", "طوب احمر", "طوب طفلي",
            "طوب أبيض", "طوب ابيض", "طوب خرساني", "بلوكات"],
}

UNITS_WEIGHT = {
    "طن": ["حديد", "حديد خردة", "صاج", "استانلس ستيل", "بلاستيك",
           "ألومنيوم", "نحاس", "رصاص", "أسمنت", "جبس"],
    "كيلو": ["بلاستيك", "ألومنيوم", "نحاس", "رصاص", "حديد خردة"],
    "كيلو جرام": ["بلاستيك", "نحاس"],
    "كجم": ["بلاستيك", "نحاس", "ألومنيوم"],
    "متر مكعب": ["خشب", "رمل", "زلط"],
    "متر مكعب ": [],
    "متر": ["خشب", "صاج"],
    "متر طولي": ["خشب", "صاج"],
    "لوح": ["أبلكاش", "MDF", "صاج"],
    "شيكارة": ["أسمنت", "رمل", "جبس"],
    "شكارة": ["أسمنت", "جبس"],
    "شكاير": ["أسمنت"],
    "ألف": ["طوب"],
    "الف": ["طوب"],
}

NUM_WORDS = {
    1: "واحد", 2: "اتنين", 3: "تلاتة", 4: "أربعة", 5: "خمسة",
    6: "ستة", 7: "سبعة", 8: "تمانية", 9: "تسعة", 10: "عشرة",
    11: "حداشر", 12: "اتناشر", 13: "تلاتاشر", 14: "أربعتاشر",
    15: "خمستاشر", 16: "ستاشر", 17: "سبعتاشر", 18: "تمنتاشر",
    19: "تسعتاشر", 20: "عشرين", 25: "خمسة وعشرين", 30: "تلاتين",
    35: "خمسة وتلاتين", 40: "أربعين", 45: "خمسة وأربعين", 50: "خمسين",
    55: "خمسة وخمسين", 60: "ستين", 65: "خمسة وستين", 70: "سبعين",
    75: "خمسة وسبعين", 80: "تمانين", 85: "خمسة وتمانين", 90: "تسعين",
    95: "خمسة وتسعين", 100: "مية", 120: "مية وعشرين", 125: "مية وخمسة وعشرين",
    150: "مية وخمسين", 175: "مية وخمسة وسبعين", 200: "ميتين",
    250: "متين وخمسين", 300: "تلتمية", 350: "تلتمية وخمسين",
    400: "ربعمية", 450: "ربعمية وخمسين", 500: "خمسمية",
    600: "ستمية", 700: "سبعمية", 750: "سبعمية وخمسين", 800: "تمنمية",
    900: "تسعمية", 1000: "ألف", 1500: "ألف وخمسمية", 2000: "ألفين",
}

AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

LOCATIONS = [
    ["القاهرة", "القاهره"],
    ["القاهرة الجديدة", "القاهره الجديده", "التجمع", "التجمع الخامس"],
    ["الجيزة", "الجيزه"],
    ["الإسكندرية", "الاسكندرية", "اسكندريه", "الإسكندريه", "اسكندرية"],
    ["برج العرب", "برج العرب الجديدة"],
    ["المنصورة", "المنصوره"],
    ["المنصورة الجديدة", "المنصوره الجديده"],
    ["طنطا"],
    ["الزقازيق"],
    ["السويس"],
    ["بورسعيد", "بور سعيد"],
    ["الإسماعيلية", "الاسماعيلية", "الإسماعيليه"],
    ["أسيوط", "اسيوط"],
    ["المنيا"],
    ["بنها"],
    ["دمياط"],
    ["دمياط الجديدة", "دمياط الجديده"],
    ["المحلة", "المحله", "المحلة الكبرى"],
    ["شبرا الخيمة", "شبرا الخيمه"],
    ["العاشر من رمضان", "العاشر", "العاشر من رمضان منطقة الصناعات"],
    ["6 أكتوبر", "٦ أكتوبر", "اكتوبر", "السادس من أكتوبر"],
    ["مدينة نصر"],
    ["المهندسين"],
    ["فيصل"],
    ["حلوان"],
    ["المعادي"],
    ["العبور"],
    ["بدر"],
    ["مدينة السادات", "السادات"],
    ["الفيوم"],
    ["بني سويف", "بنى سويف"],
    ["سوهاج"],
    ["قنا"],
    ["أسوان", "اسوان"],
    ["الأقصر", "الاقصر"],
    ["كفر الشيخ"],
    ["شبين الكوم"],
    ["دمنهور"],
    ["الزقازيق الجديدة"],
    ["الشرقية"],
    ["الغربية"],
    ["مصر الجديدة", "هليوبوليس"],
    ["عين شمس"],
    ["المرج"],
    ["شبين القناطر"],
    ["العباسية", "العباسيه"],
    ["15 مايو"],
    ["الصف"],
    ["ميت غمر"],
    ["السنبلاوين"],
    ["كفر الدوار"],
]

CONDITIONS = ["جديد", "جداد", "جديدة", "مستعمل", "مستعملة", "مستعمله",
              "نضيف", "نظيف", "نضيفة", "حالته كويسة", "حالتها كويسة جدا",
              "حالته ممتازة", "صدأ", "فيه صدأ بسيط", "عليه صدأ خفيف",
              "هالك", "زيرو", "استعمال خفيف", "شبه جديد", "شبه جديدة",
              "بضاعة رجيع", "مخزون قديم", "مخزون"]

PRICES = ["بسعر ٣٨ ألف للطن", "بسعر 38500 جنيه", "والسعر قابل للتفاوض",
          "بسعر مغري", "ب ٤٠ ألف", "بسعر ٢٥ جنيه للكيلو",
          "بسعر الجملة", "سعر خاص للكميات", "ب ٢٧٠٠ للألف",
          "بسعر ٢٢٠٠ للطن", ""]


def pick_qty(material):
    cands = [u for u, mats in UNITS_WEIGHT.items()
             if u.strip() and material in mats]
    if not cands:
        cands = ["طن"]
    unit = random.choice(cands)
    n = random.choice(list(NUM_WORDS.keys()))
    style = random.random()
    if style < 0.40:
        num = str(n)
    elif style < 0.72:
        num = str(n).translate(AR_DIGITS)
    elif style < 0.92:
        num = NUM_WORDS[n]
    else:
        # decimal form: 2.5 / ٢٫٥ / اتنين ونص
        base = random.choice([1, 2, 3, 5, 7, 10])
        num = random.choice([f"{base}.5", f"{base}.5".translate(AR_DIGITS),
                             NUM_WORDS[base] + " ونص"])
    if random.random() < 0.12:
        num += " ونص"
    if unit in ("ألف", "الف") and random.random() < 0.5:
        unit = random.choice(["ألف", "الف", "آلاف", "الاف"])
    return f"{num} {unit}"


TEMPLATES = [
    "أنا عندي {qty} {mat} في {loc}",
    "عندي {mat} حوالي {qty} موجود في {loc}",
    "عايز أبيع {qty} {mat} ب{loc}",
    "عاوز ابيع {mat} كمية {qty} المكان {loc}",
    "للبيع {qty} {mat} في {loc} {price}",
    "متوفر {mat} {qty} في {loc}",
    "متوفر عندنا {qty} {mat} {cond} في {loc}",
    "محتاج {qty} {mat} ضروري في {loc}",
    "عايز {qty} {mat} يكونوا في {loc}",
    "مطلوب {mat} {qty} للشراء في {loc}",
    "عندي {qty} {mat} {cond} في {loc}",
    "فيه {qty} {mat} عندي في {loc} عايز أتخلص منهم",
    "ببيع {mat} {qty} مكانهم {loc}",
    "وصلني {qty} {mat} {cond} في {loc}",
    "تاجر محتاج {qty} {mat} ب{loc} بسرعة",
    "يا جماعة مين عنده {mat} {qty} في {loc}",
    "عندي {qty} {mat} في {loc} {price}",
    "للجادين {qty} {mat} {cond} المكان {loc}",
    "عاوز {qty} {mat} في {loc} ومستعد أستلم فورا",
    "معايا {qty} {mat} في {loc} للي عايز",
    "عندي {qty} {mat} في مدينة {loc}",
    "مطلوب {mat} {qty} بمدينة {loc}",
    "عايز {qty} {mat} في مدينة {loc} ضروري",
    "للبيع {qty} {mat} بمنطقة {loc}",
    "عندي {qty} {mat} ب{loc} {cond}",
    "محتاج {qty} {mat} في مدينة {loc} بسرعة",
    "لو حد عنده {mat} {qty} في {loc} يكلمني",
    "مين يقدر يوفرلي {qty} {mat} في {loc}",
    "شحنة {mat} {qty} {cond} واصلة {loc}",
    "عندنا بالمخزن {qty} {mat} في {loc}",
    "توريد {qty} {mat} لأي مكان في {loc}",
    "استلام {qty} {mat} من {loc}",
    "عايز أشتري {qty} {mat} {cond} من {loc}",
    "بضاعة {mat} {qty} {cond} موجودة في {loc}",
    "للبيع كمية {qty} {mat} في {loc} {price}",
    "عندي {mat} {cond} كمية {qty} في {loc}",
    "فيه عندي {mat} {qty} في {loc} واللي عايز يجي يشوف",
    "بعرض {qty} {mat} {cond} في {loc}",
    "مين محتاج {mat} {qty} في {loc}",
    "أنا بتعامل في {mat} وعندي {qty} في {loc}",
    "خردة للبيع {qty} {mat} في {loc}",
    "عندي {qty} {mat} {cond} استلام من {loc}",
    "نشتري {mat} {qty} في {loc} كاش",
    "شركة تطلب {qty} {mat} للتوريد في {loc}",
]


def build_sentence():
    material = random.choice(list(MATERIALS.keys()))
    mat = random.choice(MATERIALS[material])
    qty = pick_qty(material)
    loc = random.choice(random.choice(LOCATIONS))
    cond = random.choice(CONDITIONS)
    price = random.choice(PRICES)
    tmpl = random.choice(TEMPLATES)

    # deliberate absences: 10% no location, 5% no quantity
    drop_loc = random.random() < 0.10
    drop_qty = random.random() < 0.05

    entities = []
    out = []
    cursor = 0
    i = 0
    while i < len(tmpl):
        if tmpl.startswith("{qty}", i):
            if not drop_qty:
                entities.append((cursor, cursor + len(qty), "QUANTITY"))
                out.append(qty); cursor += len(qty)
            i += 5
        elif tmpl.startswith("{mat}", i):
            entities.append((cursor, cursor + len(mat), "MATERIAL"))
            out.append(mat); cursor += len(mat); i += 5
        elif tmpl.startswith("{loc}", i):
            if not drop_loc:
                entities.append((cursor, cursor + len(loc), "LOCATION"))
                out.append(loc); cursor += len(loc)
            i += 5
        elif tmpl.startswith("{cond}", i):
            out.append(cond); cursor += len(cond); i += 6
        elif tmpl.startswith("{price}", i):
            if price:
                out.append(price); cursor += len(price)
            i += 7
        else:
            out.append(tmpl[i]); cursor += 1; i += 1
    text = " ".join("".join(out).split())
    return text, entities


def main(n_total=2100):
    seen = set()
    rows = []
    tries = 0
    while len(rows) < n_total and tries < n_total * 60:
        tries += 1
        text, ents = build_sentence()
        if text in seen:
            continue
        seen.add(text)
        rows.append({"text": text,
                     "entities": [[s, e, l] for s, e, l in ents]})
    random.shuffle(rows)
    n_train = int(len(rows) * 0.80)
    n_dev = int(len(rows) * 0.10)
    splits = {
        "train": rows[:n_train],
        "dev": rows[n_train:n_train + n_dev],
        "test": rows[n_train + n_dev:],
    }
    for name, split in splits.items():
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in split:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ls_tasks = []
    for idx, r in enumerate(rows):
        ls_tasks.append({
            "id": idx + 1,
            "data": {"text": r["text"]},
            "annotations": [{
                "result": [{
                    "value": {"start": s, "end": e, "text": r["text"][s:e],
                              "labels": [l]},
                    "from_name": "label", "to_name": "text", "type": "labels",
                } for s, e, l in r["entities"]],
            }],
        })
    with open(OUT / "labelstudio_tasks.json", "w", encoding="utf-8") as f:
        json.dump(ls_tasks, f, ensure_ascii=False, indent=1)

    print({k: len(v) for k, v in splits.items()})
    for r in rows[:5]:
        print(r["text"], "->", [(r["text"][s:e], l) for s, e, l in r["entities"]])


if __name__ == "__main__":
    main()
