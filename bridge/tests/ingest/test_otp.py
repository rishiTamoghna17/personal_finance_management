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
