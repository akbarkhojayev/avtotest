# Generated manually for book purchases

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_otp_user_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentrequest',
            name='book',
            field=models.ForeignKey(
                blank=True,
                help_text="Kitob uchun to'lov bo'lsa tanlanadi",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payment_requests',
                to='main.book',
            ),
        ),
    ]
