from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ingest", "0007_category_needed")]

    operations = [
        migrations.CreateModel(
            name="MessageFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(choices=[
                    ("transaction_alert", "Transaction"), ("promotion", "Promotion"),
                    ("card_bill_payment", "Card Bill Payment"), ("failed_payment", "Failed Payment"),
                    ("refund_reversal", "Refund or Reversal"), ("due_reminder", "Due Reminder"),
                    ("other", "Other"),
                ], max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("raw", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                              related_name="feedback", to="ingest.rawmessage")),
            ],
        ),
    ]
