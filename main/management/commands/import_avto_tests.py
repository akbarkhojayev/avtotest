"""
Word (.docx) fayllaridan avto-test savollarini bazaga import qilish uchun management command.
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from docx import Document

from main.models import TestQuestion, TestAnswer, Category, Video


def parse_word_file(docx_path):
    """
    Word fayldan test savollarini o'qib, tuzilgan ma'lumot qaytaradi.

    Uchta formatni qabul qiladi:
    1. Eski: Savol: 1 / Variantlar / F1: ... / To'g'ri javob
    2. Yangi: Savol raqami: X / Savol matni: Y / ... / Test javob variantlari / F1: ...
    3. Compact: Savol: ... / F1: ... / F2: ... — Tog'ri javob / etc.
    """
    doc = Document(docx_path)
    all_paras = []

    # Para objekt va content'ni saqlab ol
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            all_paras.append(text)

    # Format aniqlash
    has_new_format = any(re.search(r'Savol raqami\s*:', p, re.I) for p in all_paras)
    # Compact format: F lines with "— Tog'ri javob" OR "(To'g'ri javob)"
    has_compact_format = any(
        re.match(r'^F\d+:\s*', p) and (re.search(r"—.*Tog'ri javob", p, re.I) or re.search(r"\(To[g']g'ri javob\)", p, re.I))
        for p in all_paras
    )

    if has_new_format:
        return _parse_new_format(all_paras)
    elif has_compact_format:
        return _parse_compact_format(all_paras)
    else:
        return _parse_old_format(all_paras)


def _parse_compact_format(paras):
    """
    Compact format: Savol: ... / F1: ... / F2: ... — Tog'ri javob / F3: (To'g'ri javob)
    Variantlar to'g'ridan-to'g'ri savol ketidan keladi, "Variantlar" header yo'q
    """
    questions = []
    current_q = None
    current_q_number = None

    for para in paras:
        lines = para.split('\n')

        for line in lines:
            text = line.strip()
            if not text:
                continue

            # Question number (e.g., "881-savol", "882-savol")
            match_num = re.match(r'^(\d+)-savol\s*$', text, re.I)
            if match_num:
                current_q_number = text
                continue

            # Question text (savol raqami bo'lganidan keyin)
            if current_q_number is not None and not text.startswith('F'):
                if current_q is not None:
                    questions.append(current_q)
                current_q = {
                    'question_text': text,
                    'variants': {},
                    'correct_answer_key': None,
                    'images': []
                }
                current_q_number = None
                continue

            # "Savol:" direktli (raqamsiz format)
            if re.match(r'^[sS]avol\s*[:]\s*', text, re.I):
                if current_q is not None:
                    questions.append(current_q)
                current_q = {
                    'question_text': text,
                    'variants': {},
                    'correct_answer_key': None,
                    'images': []
                }
                continue

            # Variant line (F1, F2, etc.) - ikkita marker formatini qabul qil
            # Format 1: F1: text — Tog'ri javob
            # Format 2: F2: text (To'g'ri javob)
            match = re.match(r"^(F\d+):\s*(.+?)(\s*(?:—|)\s*(?:\()?To[g']g'ri javob\)?)?$", text, re.I)
            if match and current_q is not None:
                key = match.group(1)
                answer_text = match.group(2)
                has_marker = match.group(3)

                # Clean answer text (remove parentheses marker if any)
                answer_text = re.sub(r"\s*\(To[g']g'ri javob\)\s*$", '', answer_text, flags=re.I).strip()

                if has_marker:
                    current_q['correct_answer_key'] = key

                current_q['variants'][key] = answer_text
                continue

    if current_q is not None:
        questions.append(current_q)

    return questions


def _parse_old_format(paras):
    """
    Eski format: Savol: 1 / Variantlar / F1: ... / To'g'ri javob
    """
    questions = []
    current_q = None
    state = None

    for para in paras:
        lines = para.split('\n')

        for line in lines:
            text = line.strip()
            if not text:
                continue

            # Question header
            if re.match(r'^[sS]avol\s*[:]\s*\d+|\d+[-:\s]*[sS]avol', text, re.I):
                if current_q is not None:
                    questions.append(current_q)
                current_q = {
                    'question_text': '',
                    'variants': {},
                    'correct_answer_key': None,
                    'images': []
                }
                state = 'question_text'
                continue

            # Variant header
            if re.match(r'^Variantlar\s*(\(|:)?|^Test javob variantlari|^Test variantlari', text, re.I):
                state = 'variants'
                continue

            # Correct answer header
            if re.match(r"^To'g'ri javob\s*:?", text, re.I):
                state = 'correct_answer'
                match = re.search(r'(F\d+):?\s*', text)
                if match and current_q:
                    current_q['correct_answer_key'] = match.group(1)
                continue

            # Parse variant line
            if state == 'variants':
                match = re.match(r'^(F\d+)\s*(\([^)]*\))?\s*:\s*(.+)', text)
                if match:
                    key = match.group(1)
                    marker = match.group(2)
                    answer_text = match.group(3)

                    if marker and re.search(r"To'g'ri javob", marker, re.I):
                        if current_q:
                            current_q['correct_answer_key'] = key

                    answer_text = re.sub(r'\s*\([^)]*\)\s*', ' ', answer_text).strip()
                    if current_q:
                        current_q['variants'][key] = answer_text
                continue

            # Parse correct answer line
            if state == 'correct_answer':
                match = re.match(r'^(F\d+):\s*', text)
                if match and current_q:
                    current_q['correct_answer_key'] = match.group(1)
                continue

            # Parse question text
            if state == 'question_text':
                if current_q:
                    if current_q['question_text']:
                        current_q['question_text'] += '\n'
                    current_q['question_text'] += text

    if current_q is not None:
        questions.append(current_q)

    return questions


def _parse_new_format(paras):
    """
    Yangi format: Savol raqami: X / Savol matni: Y / ... / Test javob variantlari / F1: ...
    Savollar va variantlar alohida bloklarida bo'ladi.
    """
    questions_raw = []
    variants_raw = []

    # Step 1: Extract questions and variant blocks
    i = 0
    while i < len(paras):
        para = paras[i]

        # Check for question
        if re.search(r'Savol raqami\s*:', para, re.I) and re.search(r'Savol matni\s*:', para, re.I):
            parts = re.split(r'Savol matni\s*:\s*', para, flags=re.I)
            if len(parts) > 1:
                q_text = parts[1].strip()
                questions_raw.append({
                    'index': i,
                    'text': q_text,
                    'variants': {}
                })

        # Check for variant block
        if re.search(r'Test javob variantlari', para, re.I):
            variants = {}
            lines = para.split('\n')

            for line in lines:
                line = line.strip()
                match = re.match(r'^(F\d+)\s*(\([^)]*\))?\s*:\s*(.+)', line)
                if match:
                    key = match.group(1)
                    marker = match.group(2)
                    answer_text = match.group(3)

                    # Determine if correct
                    is_correct = marker and re.search(r"To'g'ri javob", marker, re.I)

                    # Clean answer text
                    answer_text = re.sub(r'\s*\([^)]*\)\s*', ' ', answer_text).strip()

                    variants[key] = {
                        'text': answer_text,
                        'is_correct': is_correct
                    }

            if variants:
                variants_raw.append({
                    'index': i,
                    'variants': variants
                })

        i += 1

    # Step 2: Match questions with variants (bitta variant block faqat bitta savol uchun)
    questions = []
    used_variant_indices = set()

    for q_idx, q in enumerate(questions_raw):
        # Find NEXT variant block after this question (lekin ishlatilmagan)
        variant_block = None
        for v in variants_raw:
            if v['index'] > q['index'] and v['index'] not in used_variant_indices:
                variant_block = v
                break

        # Assemble question
        q_data = {
            'question_text': q['text'],
            'variants': {},
            'correct_answer_key': None,
            'images': []
        }

        if variant_block:
            used_variant_indices.add(variant_block['index'])
            for vkey, vdata in variant_block['variants'].items():
                q_data['variants'][vkey] = vdata['text']
                if vdata['is_correct']:
                    q_data['correct_answer_key'] = vkey

        questions.append(q_data)

    return questions


class Command(BaseCommand):
    help = "Word (.docx) fayllaridan avto-test savollarini bazaga import qiladi."

    def add_arguments(self, parser):
        parser.add_argument(
            'docx_path',
            type=str,
            help="Word fayli yo'li"
        )
        parser.add_argument(
            '--category',
            type=int,
            default=None,
            help='Category ID'
        )
        parser.add_argument(
            '--video',
            type=int,
            default=None,
            help='Video (lesson_video) ID'
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            choices=['easy', 'medium', 'hard'],
            default='medium',
            help='Savol qiyinligi'
        )
        parser.add_argument(
            '--start-order',
            type=int,
            default=0,
            help="Order ning boshlang'ich qiymati"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Bazaga yozmasdan faqat ko'rsatadi"
        )

    def handle(self, *args, **options):
        docx_path = options['docx_path']
        category_id = options['category']
        video_id = options['video']
        difficulty = options['difficulty']
        start_order = options['start_order']
        dry_run = options['dry_run']

        # Fayl mavjudligini tekshir
        if not Path(docx_path).exists():
            raise CommandError(f"Fayl topilmadi: {docx_path}")

        # Category va Video ni tekshir
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise CommandError(f"Category topilmadi: {category_id}")

        video = None
        if video_id:
            try:
                video = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                raise CommandError(f"Video topilmadi: {video_id}")

        # Word faylni parse qil
        self.stdout.write(f"Word fayli o'qilmoqda: {docx_path}")
        try:
            questions_data = parse_word_file(docx_path)
        except Exception as e:
            raise CommandError(f"Word fayli o'qishda xato: {e}")

        if not questions_data:
            raise CommandError("Savollar topilmadi")

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(questions_data)} ta savol topildi"
        ))

        # Dry-run rejimida faqat ma'lumotlarni ko'rsatadi
        if dry_run:
            self._show_preview(questions_data)
            return

        # Bazaga yozish
        with transaction.atomic():
            created_count = 0

            for order_idx, q_data in enumerate(questions_data, start=start_order):
                question_text = q_data['question_text']
                variants = q_data['variants']
                correct_key = q_data['correct_answer_key']
                images = q_data['images']

                # Variantlar mavjudligini tekshir
                if not variants:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Savol {order_idx}: variantlar topilmadi, o'tkazildi"
                        )
                    )
                    continue

                # TestQuestion yaratish
                question = TestQuestion(
                    question_text=question_text,
                    category=category,
                    lesson_video=video,
                    difficulty=difficulty,
                    order=order_idx,
                )

                # Rasmni biriktir
                if images:
                    image_bytes = images[0]
                    filename = f"question_{order_idx}.jpg"
                    question.photo.save(filename, ContentFile(image_bytes))

                question.save()

                # TestAnswer larni yaratish
                answers = []
                for variant_key, answer_text in sorted(variants.items()):
                    is_correct = (variant_key == correct_key)

                    # Variant key dan F-number ni ol (F1 -> 1)
                    order_val = int(variant_key[1:]) if variant_key.startswith('F') else 0

                    answer = TestAnswer(
                        question=question,
                        answer_text=answer_text,
                        is_correct=is_correct,
                        order=order_val
                    )
                    answers.append(answer)

                TestAnswer.objects.bulk_create(answers)
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {created_count} ta savol bazaga qo'shildi!"
        ))

    def _show_preview(self, questions_data):
        """Dry-run rejimida savollarni ko'rsatadi."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("DRY-RUN REJIMI - BAZAGA YOZILMAYDI")
        self.stdout.write("="*60)

        for idx, q_data in enumerate(questions_data[:10], 1):
            self.stdout.write(f"\n📋 SAVOL #{idx}")
            self.stdout.write("-" * 40)

            text = q_data['question_text']
            if len(text) > 100:
                text = text[:97] + "..."
            self.stdout.write(f"Matni: {text}")

            self.stdout.write(f"Variantlar: {len(q_data['variants'])} ta")
            for key, ans in sorted(q_data['variants'].items()):
                marker = "✓" if key == q_data['correct_answer_key'] else " "
                ans_short = ans[:40] + "..." if len(ans) > 40 else ans
                self.stdout.write(f"  [{marker}] {key}: {ans_short}")

            if not q_data['correct_answer_key']:
                self.stdout.write(
                    self.style.WARNING("  ⚠ To'g'ri javob topilmadi!")
                )

        if len(questions_data) > 10:
            self.stdout.write(f"\n... va {len(questions_data) - 10} ta boshqa savol")

        self.stdout.write("\n" + "="*60)
