"""Build a demo website from the FICTIONAL test feeds (offline, no API key). Output: demo_site/"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tests")]
os.chdir(ROOT)

import newsroom.dedupe as dd  # noqa: E402
import newsroom.writer as wr  # noqa: E402
from demo_writer import fake_claude  # noqa: E402
from newsroom.pipeline import run  # noqa: E402

wr.call_claude = dd.call_claude = fake_claude
tmp = os.path.join(ROOT, ".demo_tmp")
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree("demo_site", ignore_errors=True)
run(sources_file="tests/fixtures/sources_test.yaml", out_dir=os.path.join(tmp, "out"),
    state_path=os.path.join(tmp, "state.json"), use_llm=True, publish=True, all_day=True,
    content_dir=os.path.join(tmp, "content"), site_dir="demo_site",
    banner="نسخة تجريبية: كل الأخبار هنا بيانات اختبار وهمية وليست أخباراً حقيقية")
shutil.rmtree(tmp, ignore_errors=True)
print("demo_site/index.html")
