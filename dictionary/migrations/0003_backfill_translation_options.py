from django.db import migrations


def forwards(apps, schema_editor):
    Word = apps.get_model("dictionary", "Word")
    TranslationOption = apps.get_model("dictionary", "TranslationOption")

    for word in Word.objects.all().iterator():
        translation = (word.ukrainian_translation or "").strip()
        if not translation:
            continue

        exists = TranslationOption.objects.filter(word=word).exists()
        if exists:
            continue

        TranslationOption.objects.create(
            word=word,
            text=translation,
            part_of_speech="other",
            priority=1,
            usage_note="",
        )


def backwards(apps, schema_editor):
    TranslationOption = apps.get_model("dictionary", "TranslationOption")
    TranslationOption.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("dictionary", "0002_translationoption_word_source_language_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
