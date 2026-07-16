import asyncio
import os
import subprocess
from datetime import datetime

from config import *


def run(command, cwd=None):

    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )

    return {
        "code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }



async def deploy():

    version = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    release = (
        f"{RELEASES_DIR}/{version}"
    )


    os.makedirs(
        release,
        exist_ok=True
    )


    yield {
        "step":"download",
        "message":"Cloning repository"
    }


    result = run(
        f"git clone "
        f"--branch {UPDATE_BRANCH} "
        f"{REPO_URL} {release}"
    )


    if result["code"] != 0:

        yield {
            "step":"error",
            "message":result["stderr"]
        }

        return



    yield {
        "step":"dependencies",
        "message":"Installing packages"
    }


    run(
        "python3 -m venv venv",
        cwd=release
    )


    run(
        "./venv/bin/pip install -r requirements.txt",
        cwd=release
    )



    yield {
        "step":"switch",
        "message":"Switching release"
    }


    run(
        f"ln -sfn {release} {CURRENT_LINK}"
    )



    yield {
        "step":"restart",
        "message":"Restarting service"
    }


    run(
        f"sudo systemctl restart {SERVICE_NAME}"
    )


    yield {
        "step":"done",
        "message":version
    }