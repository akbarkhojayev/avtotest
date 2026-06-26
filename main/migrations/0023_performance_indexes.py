from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_paymentrequest_payment_type'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='video',
            index=models.Index(fields=['is_active', 'order', 'created_at'], name='video_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='videoprogress',
            index=models.Index(fields=['user', '-last_watched'], name='progress_user_last_idx'),
        ),
        migrations.AddIndex(
            model_name='videoprogress',
            index=models.Index(fields=['user', 'is_completed'], name='progress_user_done_idx'),
        ),
        migrations.AddIndex(
            model_name='testresult',
            index=models.Index(fields=['user', '-completed_at'], name='testresult_user_done_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentrequest',
            index=models.Index(fields=['user', 'status', '-created_at'], name='payment_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='paymentrequest',
            index=models.Index(fields=['user', 'book', 'status'], name='payment_user_book_idx'),
        ),
        migrations.AddIndex(
            model_name='book',
            index=models.Index(fields=['is_active', 'order', 'created_at'], name='book_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='roadsign',
            index=models.Index(fields=['is_active', 'category', 'order'], name='roadsign_active_cat_idx'),
        ),
    ]
