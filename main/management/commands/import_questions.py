from django.core.management.base import BaseCommand
from main.models import TestQuestion, TestAnswer

QUESTIONS = [
    {
        "order": 1,
        "question_text": "Qaysi avtomobil uchun bu belgilarning ta'sir oralig'ida to'xtashga ruxsat etiladi?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Qizilga", "correct": False},
            {"text": "Ikkala avtomobilga", "correct": False},
            {"text": "Hech qaysi biriga", "correct": False},
            {"text": "«Nogiron» taniqlik belgisi bo'lgan sariq avtomobilga", "correct": True},
        ],
    },
    {
        "order": 2,
        "question_text": "Qaysi yo'naltirgichlar bo'ylab harakatlanishga ruxsat etiladi?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Faqat «A» yo'nalish bo'ylab", "correct": False},
            {"text": "Faqat «Б» yo'nalish bo'ylab", "correct": False},
            {"text": "Faqat «В» yo'nalish bo'ylab", "correct": False},
            {"text": "Faqat «A» va «Г» yo'nalishlari bo'ylab", "correct": True},
            {"text": "Faqat «Г» yo'nalish bo'ylab", "correct": False},
        ],
    },
    {
        "order": 3,
        "question_text": "Tibbiyot qutichasi va o't o'chirgichi bo'lmagan qanday transport vositalaridan foydalanish taqiqlanadi?",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Faqat M1 toifali transport vositasi", "correct": False},
            {"text": "Faqat M2; M3; N1 toifali transport vositasi", "correct": False},
            {"text": "Faqat N2; N3 toifali transport vositasi", "correct": False},
            {"text": "Barcha yuqorida ko'rsatilgan toifalar", "correct": True},
        ],
    },
    {
        "order": 4,
        "question_text": "Chorrahadan birinchi bo'lib o'tadi:",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Qizil avtomobil", "correct": False},
            {"text": "Ko'k avtomobil", "correct": False},
            {"text": "Sariq avtomobil", "correct": False},
            {"text": "Yashil avtomobil", "correct": True},
        ],
    },
    {
        "order": 5,
        "question_text": "Harakatlanish taqiqlangan:",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Qizil va oq avtomobillarga", "correct": False},
            {"text": "Ko'k, yashil va oq avtomobillarga", "correct": True},
            {"text": "Oq, ko'k va sariq avtomobillarga", "correct": False},
        ],
    },
    {
        "order": 6,
        "question_text": "Qaysi transport vositasining haydovchisi chorrahadan birinchi bo'lib o'tadi?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Avtomobil va avtobus haydovchisi", "correct": True},
            {"text": "Tramvay haydovchisi", "correct": False},
        ],
    },
    {
        "order": 7,
        "question_text": "Shu joyda to'xtab turishga ruxsat etiladimi?",
        "difficulty": "easy",
        "has_photo": True,
        "answers": [
            {"text": "Ruxsat etiladi", "correct": False},
            {"text": "Taqiqlanadi", "correct": True},
        ],
    },
    {
        "order": 8,
        "question_text": "Haydovchi harakatlanishni boshlashdan oldin qanday amallarni bajarishi kerak?",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Transport vositasining sozligini va to'la jihozlanganligini tekshirishi", "correct": False},
            {"text": "Harakatlanish boshlanishi xavfsiz bo'lishiga va harakatning boshqa ishtirokchilariga xalaqit bermasligiga ishonch hosil qilishi", "correct": True},
            {"text": "Tegishli yo'nalishdagi burilishning yorug'lik ko'rsatkichi bilan ishora berishi", "correct": False},
            {"text": "Sanab o'tilgan barcha harakatlarni bajarishi", "correct": False},
        ],
    },
    {
        "order": 9,
        "question_text": "Umurtqa pog'onasining ko'krak sohasi shikastlangan jabrlanuvchini transportda qanday tashish kerak?",
        "difficulty": "hard",
        "has_photo": False,
        "answers": [
            {"text": "Qattiq taxtada orqasi bilan yotgan holda", "correct": True},
            {"text": "Yumshoq to'shamada orqasi bilan yotgan holda", "correct": False},
            {"text": "Qattiq taxtada yoni bilan yotgan holda", "correct": False},
        ],
    },
    {
        "order": 10,
        "question_text": "Bunday taniqlik belgisi bilan belgilanadigan transport vositasi:",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Og'ir vaznli va yirik o'lchamli yuklarni tashuvchi", "correct": False},
            {"text": "Uzunligi yuk bilan yoki yuksiz 20 metrdan ortiq bo'lgan transport vositasi", "correct": True},
            {"text": "Furgon yukxonasida odamlarni tashuvchi", "correct": False},
        ],
    },
    {
        "order": 11,
        "question_text": "Yoqilgan zarg'aldoq rangli yalt-yalt etuvchi chiroq-mayoqcha harakatlanish uchun imtiyoz beradimi?",
        "difficulty": "easy",
        "has_photo": False,
        "answers": [
            {"text": "Ha", "correct": False},
            {"text": "Yo'q", "correct": True},
        ],
    },
    {
        "order": 12,
        "question_text": "Quyidagi belgilar qaysi yo'nalishlarda harakatlanishga ruxsat beradi?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Faqat chapga", "correct": False},
            {"text": "Faqat to'g'riga", "correct": False},
            {"text": "Faqat o'ngga", "correct": False},
            {"text": "To'g'riga, o'ngga va qayrilib olishga", "correct": True},
        ],
    },
    {
        "order": 13,
        "question_text": "Mazkur chiziq nima haqida ogohlantiradi?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Transport vositalarining majburiy to'xtash joyiga yaqinlashayotganligini", "correct": False},
            {"text": "«To'xtamasdan harakatlanish taqiqlangan» belgisi bilan birga qo'llanilganda, haydovchini «To'xtash» chizig'iga yaqinlashayotganligini", "correct": True},
            {"text": "Transport vositasi piyodalarga yo'l berishi kerak bo'lgan joyni ko'rsatadi", "correct": False},
        ],
    },
    {
        "order": 14,
        "question_text": "Avtomagistralda quyidagilar taqiqlanadi:",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Qayrilib olish va ajratuvchi mintaqaning texnologik uzilish joylariga kirish", "correct": False},
            {"text": "Orqaga harakatlanish", "correct": False},
            {"text": "«To'xtab turish joyi» yoki «Dam olish joyi» belgilari bo'lgan maxsus maydonchalardan tashqari joyda to'xtash", "correct": False},
            {"text": "Yuqoridagi barcha holatlar", "correct": True},
        ],
    },
    {
        "order": 15,
        "question_text": "Qaysi transport vositasi haydovchisi to'g'riga harakatlanish huquqiga ega?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Avtobus va mototsikl haydovchilari", "correct": False},
            {"text": "Yengil va yuk avtomobillari haydovchilari", "correct": False},
            {"text": "Yengil avtomobil haydovchisi", "correct": True},
        ],
    },
    {
        "order": 16,
        "question_text": "Qaysi transport vositasining haydovchisi yo'l berishi kerak?",
        "difficulty": "medium",
        "has_photo": True,
        "answers": [
            {"text": "Avtomobil haydovchisi", "correct": False},
            {"text": "Tramvay haydovchisi", "correct": True},
        ],
    },
    {
        "order": 17,
        "question_text": "Transport vositasini orqaga harakatlantirish paytida haydovchi qanday talablarni bajarishi kerak?",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Harakatning boshqa ishtirokchilariga xalaqit bermaslik. Harakat xavfsizligini ta'minlash uchun zarur bo'lsa, boshqa shaxslar yordamidan foydalanish.", "correct": True},
            {"text": "Boshqa shaxslar yordamidan foydalanish.", "correct": False},
            {"text": "Transport vositasida tumanga qarshi orqa chiroqlar bo'lsa, ularni yoqish.", "correct": False},
            {"text": "Gabarit chiroqlarini yoqish.", "correct": False},
        ],
    },
    {
        "order": 18,
        "question_text": "Yo'lning qarama-qarshi harakat yo'nalishi tomoniga chiqish qachon taqiqlanadi?",
        "difficulty": "hard",
        "has_photo": False,
        "answers": [
            {"text": "Ikki tomonlama harakatli, 4 ta yoki undan ko'p tasmali yo'llarda.", "correct": False},
            {"text": "Ikki tomonlama harakatli, qarama-qarshi yo'nalishdagi transport vositalari oqimlari ikkita uzluksiz chiziqlar bilan ajratilgan 4 ta tasmali yo'llarda.", "correct": False},
            {"text": "Yuqoridagi barcha hollarda.", "correct": True},
        ],
    },
    {
        "order": 19,
        "question_text": "Qaysi holatda egri yo'lda harakatlanayotgan avtomobil turg'unligi ta'minlanadi?",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Uzatma ulangan holatda.", "correct": True},
            {"text": "Uzatma ajratilgan holatda.", "correct": False},
            {"text": "Tezlik oshirilganda.", "correct": False},
        ],
    },
    {
        "order": 20,
        "question_text": "Qaysi shartlarda transport vositalaridan foydalanish taqiqlanadi?",
        "difficulty": "medium",
        "has_photo": False,
        "answers": [
            {"text": "Gidravlik tormoz tizimidan suyuqlik oqayotgan bo'lsa.", "correct": False},
            {"text": "Ishchi tormoz tizimi ishlamayotgan bo'lsa.", "correct": False},
            {"text": "Kompressor pnevmatik tormoz tizimida o'rnatilgan bosimni ta'minlay olmagan holatda.", "correct": False},
            {"text": "Ko'rsatilgan barcha holatlarda.", "correct": True},
        ],
    },
]


class Command(BaseCommand):
    help = "1-shablon test savollarini (1-20) bazaga yuklaydi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Mavjud umumiy savollarni o'chirib, qayta yuklaydi",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = TestQuestion.objects.filter(lesson_video__isnull=True).delete()
            self.stdout.write(self.style.WARNING(f"{deleted} ta savol o'chirildi."))

        created_count = 0
        skipped_count = 0

        for q_data in QUESTIONS:
            if TestQuestion.objects.filter(
                question_text=q_data["question_text"],
                lesson_video__isnull=True,
            ).exists():
                skipped_count += 1
                self.stdout.write(f"  [o'tkazildi] {q_data['order']}-savol allaqachon mavjud")
                continue

            question = TestQuestion.objects.create(
                lesson_video=None,
                question_text=q_data["question_text"],
                difficulty=q_data["difficulty"],
                order=q_data["order"],
                is_active=True,
            )

            for i, ans in enumerate(q_data["answers"], start=1):
                TestAnswer.objects.create(
                    question=question,
                    answer_text=ans["text"],
                    is_correct=ans["correct"],
                    order=i,
                )

            has_photo = q_data.get("has_photo", False)
            photo_note = " [📷 rasm kerak]" if has_photo else ""
            self.stdout.write(
                self.style.SUCCESS(f"  [+] {q_data['order']}-savol yaratildi{photo_note}")
            )
            created_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Tugadi: {created_count} ta yangi savol yaratildi, {skipped_count} ta o'tkazildi."
        ))

        photo_questions = [q["order"] for q in QUESTIONS if q.get("has_photo")]
        if photo_questions:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                f"Rasmli savollar (admin orqali qo'shing): {photo_questions}"
            ))
