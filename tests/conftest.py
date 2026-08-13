import pytest
import os
import sys

# Ensure root workspace directory is in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Set test environment
os.environ["ENV"] = "test"
os.environ["OPENAI_API_KEY"] = "mock_openai_api_key"
os.environ["ELEVENLABS_API_KEY"] = "mock_elevenlabs_api_key"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_mockkey123"
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_secret_mock456"



@pytest.fixture
def mock_user_phone():
    return "+919876543210"


@pytest.fixture
def sample_running_shoe_transcript():
    return "Bhai, mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9"
