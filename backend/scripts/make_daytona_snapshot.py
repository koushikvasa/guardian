"""One-time: build a Daytona snapshot with Playwright preinstalled, then set DAYTONA_SNAPSHOT=guardian-detonator.
Cuts detonation from ~30 s (pip install every time) to a few seconds."""
import sys
sys.path.insert(0, ".")
from app import config
from daytona import Daytona, DaytonaConfig, Image, CreateSnapshotParams

d = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
image = Image.debian_slim("3.12").pip_install(["playwright==1.48.0"])
d.snapshot.create(CreateSnapshotParams(name="guardian-detonator", image=image), on_logs=print)
print("done -> add DAYTONA_SNAPSHOT=guardian-detonator to .env")
