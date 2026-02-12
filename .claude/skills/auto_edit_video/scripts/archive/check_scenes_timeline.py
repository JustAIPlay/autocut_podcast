import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open(r'd:\channel\video_projects\2nd_video\raw_materials\copys\AITSmx000087_scenes.json', encoding='utf-8') as f:
    scenes_data = json.load(f)

# 兼容新旧格式
if isinstance(scenes_data, dict) and "scenes" in scenes_data:
    data = scenes_data["scenes"]  # 新格式
else:
    data = scenes_data  # 旧格式（纯数组）

null_count = sum(1 for s in data if s.get('start_time') is None)

print(f'总场景数: {len(data)}')
print(f'时间线为null: {null_count}')
print(f'时间线完整: {len(data)-null_count}')
print(f'完整率: {(len(data)-null_count)/len(data)*100:.1f}%')

print(f'\n时间线为null的场景:')
for s in data:
    if s.get('start_time') is None:
        print(f'  场景{s["scene"]}: {s["text"][:40]}...')

print(f'\n场景时间分布:')
for i, s in enumerate(data):
    if s.get('start_time') is not None:
        print(f'  场景{s["scene"]}: [{s["start_time"]:.2f}-{s["end_time"]:.2f}] ({s["duration"]:.2f}s)')
    else:
        print(f'  场景{s["scene"]}: [NULL] (无时间)')
