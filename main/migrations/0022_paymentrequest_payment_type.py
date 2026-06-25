# Generated manually to separate subscription and book payments.
from django.db import migrations, models
import django.db.models.deletion


def infer_payment_type(apps, schema_editor):
    PaymentRequest = apps.get_model('main', 'PaymentRequest')
    PaymentRequest.objects.filter(book__isnull=False).update(payment_type='book')
    PaymentRequest.objects.filter(book__isnull=True).update(payment_type='subscription')


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_paymentrequest_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentrequest',
            name='payment_type',
            field=models.CharField(
                choices=[('subscription', 'Kurs/obuna'), ('book', 'Kitob')],
                default='subscription',
                help_text="To'lov turi: kurs/obuna yoki kitob",
                max_length=20,
            ),
        ),
        migrations.RunPython(infer_payment_type, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='paymentrequest',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(('book__isnull', False), ('payment_type', 'book')),
                    models.Q(('book__isnull', True), ('payment_type', 'subscription')),
                    _connector='OR',
                ),
                name='payment_type_matches_book',
            ),
        ),
    ]
