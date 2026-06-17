"""
Autostart papkasidan hamma Word fayllarini bulk import qiladi.
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from main.models import Video
from .import_avto_tests import parse_word_file


class Command(BaseCommand):
    help = "Autostart papkasidagi hamma Word fayllarini bulk import qiladi."

    def add_arguments(self, parser):
        parser.add_argument(
            '--folder',
            type=str,
            default='autostart',
            help="Import qilish papkasi (default: autostart)"
        )
        parser.add_argument(
            '--difficulty',
            type=str,
            choices=['easy', 'medium', 'hard'],
            default='medium',
            help="Savol qiyinligi"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Bazaga yozmasdan faqat ko'rsatadi"
        )

    def handle(self, *args, **options):
        folder = Path(options['folder'])
        difficulty = options['difficulty']
        dry_run = options['dry_run']

        if not folder.exists():
            raise CommandError(f"Papka topilmadi: {folder}")

        # Word fayllarini topish
        docx_files = sorted(folder.glob('*.docx'))
        if not docx_files:
            raise CommandError(f"Word fayllar topilmadi: {folder}")

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(docx_files)} ta Word fayl topildi"
        ))

        # Mapping yaratish: fayl raqami -> video
        video_mapping = self._create_video_mapping()
        if not video_mapping:
            self.stdout.write(self.style.WARNING(
                "⚠ Video topilmadi - fayllar video bilan bog'lanmaydi"
            ))

        stats = {
            'total_files': len(docx_files),
            'successful': 0,
            'failed': 0,
            'total_questions': 0,
            'errors': []
        }

        # Fayllarni import qilish
        for file_path in docx_files:
            try:
                file_num = self._extract_file_number(file_path.name)
                self.stdout.write(
                    f"\n📄 Import: {file_path.name} (#{file_num})...",
                    ending=''
                )

                # Video ni topish
                video = None
                if file_num in video_mapping:
                    video = video_mapping[file_num]

                # Savollarni parse qilish
                questions_data = parse_word_file(str(file_path))

                if not questions_data:
                    self.stdout.write(self.style.WARNING(" ⚠ Savollar topilmadi"))
                    stats['failed'] += 1
                    continue

                # Bazaga yozish
                if not dry_run:
                    self._save_questions(questions_data, video, difficulty)

                stats['successful'] += 1
                stats['total_questions'] += len(questions_data)
                self.stdout.write(self.style.SUCCESS(
                    f" ✓ {len(questions_data)} ta savol"
                ))

            except Exception as e:
                stats['failed'] += 1
                error_msg = f"{file_path.name}: {str(e)}"
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f" ✗ Xato: {e}"))

        # Xulosa
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 IMPORT NATIJALARI")
        self.stdout.write("="*60)
        self.stdout.write(f"Jami fayllar: {stats['total_files']}")
        self.stdout.write(self.style.SUCCESS(
            f"✓ Muvaffaqiyatli: {stats['successful']}"
        ))
        self.stdout.write(self.style.ERROR(
            f"✗ Muvaffaqiyatsiz: {stats['failed']}"
        ))
        self.stdout.write(f"📋 Jami savollar: {stats['total_questions']}")

        if stats['errors']:
            self.stdout.write("\n" + self.style.ERROR("XATOLAR:"))
            for error in stats['errors'][:5]:
                self.stdout.write(f"  • {error}")
            if len(stats['errors']) > 5:
                self.stdout.write(f"  ... va {len(stats['errors']) - 5} ta boshqa xato")

        if dry_run:
            self.stdout.write("\n" + self.style.WARNING(
                "⚠ DRY-RUN REJIMI - Bazaga hech narsa yozilmadi!"
            ))

    def _extract_file_number(self, filename):
        """Fayl nomidan raqamni o'qib oladi."""
        match = re.match(r'^(\d+)-', filename)
        if match:
            return int(match.group(1))
        return None

    def _create_video_mapping(self):
        """Fayl raqami va Video o'rtasida mapping yaratadi. (Video qoldirish - None)"""
        # Video mapping yo'q - hamma savolni video=None bilan saqla
        return {}

    def _save_questions(self, questions_data, video, difficulty):
        """Savollarni bazaga saqlaydi."""
        from django.core.files.base import ContentFile
        from main.models import TestQuestion, TestAnswer

        with transaction.atomic():
            order = 0
            for q_data in questions_data:
                question_text = q_data['question_text']
                variants = q_data['variants']
                correct_key = q_data['correct_answer_key']
                images = q_data['images']

                # Variantlar bo'lmasa skip qil
                if not variants:
                    continue

                # TestQuestion yaratish
                question = TestQuestion(
                    question_text=question_text,
                    lesson_video=video,  # None bo'ladi, video mapping yo'q
                    difficulty=difficulty,
                    order=order,
                )

                # Rasmni biriktir
                if images:
                    image_bytes = images[0]
                    filename = f"q_{video.id if video else 0}_{order}.jpg"
                    question.photo.save(filename, ContentFile(image_bytes))

                question.save()
                order += 1

                # Variantlarni yaratish
                answers = []
                for variant_key, answer_text in sorted(variants.items()):
                    is_correct = (variant_key == correct_key)
                    order_val = int(variant_key[1:]) if variant_key.startswith('F') else 0

                    answer = TestAnswer(
                        question=question,
                        answer_text=answer_text,
                        is_correct=is_correct,
                        order=order_val
                    )
                    answers.append(answer)

                TestAnswer.objects.bulk_create(answers)
