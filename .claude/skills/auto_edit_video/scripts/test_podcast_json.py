#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证播客文案转 JSON 格式
"""
import sys
import json
from pathlib import Path

# 添加脚本目录到路径
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from generate_podcast_tts import parse_podcast_script, create_soulx_input


def test_parse_podcast():
    """测试播客脚本解析"""
    
    # 测试数据
    test_script = """[S1] 家里这几样东西千万别忽略了。
[S1] 咱们现在说说，大家是不是都有过那种时候？
[S2] 您这话可算是说到点子上了！
[S2] 老天爷呀，您今年可要好好照顾眼前这位正在看视频的有缘人。
[S1] 脸色发黄、苍白、没光泽，在我们看来，往往是脾虚、血虚、循环不畅的信号。
"""
    
    print("=" * 60)
    print("测试播客脚本解析")
    print("=" * 60)
    
    # 解析脚本
    dialogues = parse_podcast_script(test_script)
    
    print(f"\n✅ 解析成功！共 {len(dialogues)} 条对话\n")
    
    for i, (speaker, text) in enumerate(dialogues, 1):
        print(f"{i}. [{speaker}] {text[:50]}{'...' if len(text) > 50 else ''}")
    
    # 创建 JSON 输入
    print("\n" + "=" * 60)
    print("生成 SoulX-Podcast JSON 格式")
    print("=" * 60)
    
    voice_s1 = "D:/AI/SoulX-Podcast/voices/speaker1.wav"
    voice_s2 = "D:/AI/SoulX-Podcast/voices/speaker2.wav"
    
    soulx_input = create_soulx_input(dialogues, voice_s1, voice_s2)
    
    print("\n生成的 JSON 格式：\n")
    print(json.dumps(soulx_input, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    # 验证格式
    assert "speakers" in soulx_input, "缺少 speakers 字段"
    assert "text" in soulx_input, "缺少 text 字段"
    assert "S1" in soulx_input["speakers"], "缺少 S1 说话人"
    assert "S2" in soulx_input["speakers"], "缺少 S2 说话人"
    assert "prompt_audio" in soulx_input["speakers"]["S1"], "S1 缺少 prompt_audio"
    assert "prompt_text" in soulx_input["speakers"]["S1"], "S1 缺少 prompt_text"
    assert len(soulx_input["text"]) == len(dialogues), "对话数量不匹配"
    
    print("\n✅ 所有验证通过！")
    print(f"   - S1 参考文本: {soulx_input['speakers']['S1']['prompt_text']}")
    print(f"   - S2 参考文本: {soulx_input['speakers']['S2']['prompt_text']}")
    print(f"   - 对话条数: {len(soulx_input['text'])}")


if __name__ == "__main__":
    test_parse_podcast()
