import os


HOST = "0.0.0.0"
PORT = 8765
DEFAULT_PWM_FREQUENCY = 1000

ALLOWED_PINS = {
	17,
	18,
	22,
	23,
	24,
	25,
}

MOCK_GPIO = os.getenv("MOCK_GPIO", "").lower() in {
	"1",
	"true",
	"yes",
}

BASE_DIR = "/opt/rpi-dashboard"

RELEASES_DIR = f"{BASE_DIR}/releases"

CURRENT_LINK = f"{BASE_DIR}/current"

SERVICE_NAME = "berryboard.service"

UPDATE_BRANCH = "main"

REPO_URL = "git@github.com:your-user/your-project.git"