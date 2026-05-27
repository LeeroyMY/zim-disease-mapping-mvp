import django
import os
import traceback
import faulthandler
import threading
import sys

faulthandler.enable()

def dump_trace():
    print("DUMPING TRACEBACK")
    faulthandler.dump_traceback(sys.stderr)
    os._exit(1)

timer = threading.Timer(10.0, dump_trace)
timer.start()

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
try:
    print("setting up...")
    django.setup()
    print("setup done")
    import core.urls
    print("SUCCESS: Loaded core.urls")
except Exception:
    traceback.print_exc()
finally:
    timer.cancel()
