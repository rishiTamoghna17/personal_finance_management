import pytest

from ingest.otp import contains_secret

# Generic wording, not any bank's real format.
SECRETS = [
    "482913 is your OTP for login. Valid for 5 minutes.",
    "Your OTP is 482913. Do not share it with anyone.",
    "OTP: 482913 for transaction of INR 500.00 at SHOP",
    "Do not share OTP 482913 with anyone",
    "Use 482913 to verify your mobile number",
    "Your verification code is 4829",
    "One-Time Password for card XX1234 is 482913",
    "Your login password is Abc@1234",
    "Your new MPIN has been set to 4829",
    "CVV for your virtual card is 482",
    "Security code: 482913",
    "Your code is 482913",
    "482913 is the authentication code for your request",
]

KEPT = [
    "INR 1,500.00 debited from a/c XX1234 on 12-11-26. Never share your OTP/PIN with anyone.",
    "Rs.1500 spent on card XX1234 at SHOP. Never share OTP, PIN or CVV.",
    "INR 250.00 credited to a/c XX1234 ref 123456789012. Do not share your card details with anyone.",
    "Payment of INR 3,000.00 received on card ending 1234. Thank you.",
    "Your a/c XX1234 balance is INR 12,345.67 as of 12-11-26",
]


@pytest.mark.parametrize("text", SECRETS)
def test_secret_messages_are_detected(text):
    assert contains_secret(text)


@pytest.mark.parametrize("text", KEPT)
def test_transaction_alerts_with_warnings_are_kept(text):
    assert not contains_secret(text)


def test_whitespace_and_case_do_not_hide_a_secret():
    assert contains_secret("YOUR\n   ONE TIME\tPASSWORD   is 482913")


# --- email ------------------------------------------------------------------------
from ingest.otp import contains_secret_email

EMAIL_SECRETS = [
    ("One Time Password (OTP) for your online transaction at SHOP", "Dear Cardholder, 482913 is the OTP for your transaction."),
    ("SBI Card One Time Password", "Your one time password is 482913."),
    ("Account update", "Your OTP is 482913. It is valid for 5 minutes. Do not share it with anyone."),
    ("Your request", "482913 is your verification code for the request."),
    ("Your request", "Please do not share OTP 482913 with anyone."),
]
EMAIL_KEPT = [
    ("Transaction Alert from SBI Card", "Rs.450.00 spent on your SBI Credit Card ending 1006 at SHOP on 01/11/26. "
     "Safe Banking Tip: Never share your Card Number, CVV, PIN, OTP, Internet Banking User ID or Password with anyone. "
     "Call 1860 180 1290 or 39 02 02 02."),
    ("Your Axis Bank Credit Card Statement", "Option 1: Enter the first four letters of your name in UPPER CASE and your date "
     "of birth in DDMM format. For example: Name C.K. Ajay Kumar + Date of Birth 01.01.1990 Password CKAJ0101."),
    ("Federal Bank - Savings Account Statement", "For example, if your name is Om R Dev & you were born on Jan 25, your passcode is OMRD2501."),
    ("Statements for Accounts", "This statement is secured by a unique password. Your password is your date of birth (DDMMYY) "
     "followed by the 4th to the 9th digit of your Customer ID."),
    ("Account update", "HSBC will never contact you by email to ask you to validate your user ID or password 1234."),
]


@pytest.mark.parametrize("subject,body", EMAIL_SECRETS)
def test_email_secrets_are_dropped(subject, body):
    assert contains_secret_email(subject, body)


@pytest.mark.parametrize("subject,body", EMAIL_KEPT)
def test_email_alerts_and_password_instructions_are_kept(subject, body):
    assert not contains_secret_email(subject, body)
