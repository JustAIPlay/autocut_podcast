#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕脱敏处理脚本

功能：
- 解析 SRT 字幕文件
- 根据敏感词替换规则进行脱敏
- 保持时间轴不变
- 生成脱敏报告
"""

import sys
import io
import re
import random
from pathlib import Path

# ==================== 白名单（不脱敏词库） ====================
WHITELIST = {
    # 常用表达
    '身体', '健康', '营养', '食物', '生活', '方法', '作用', '效果', '问题',
    '情况', '时间', '研究', '发现', '证明', '建议', '注意', '重要', '简单',
    '容易', '坚持', '这', '很多', '一些', '大量', '少量', '适量', '足够', '充足',
    
    # 食材/食物
    '蔬菜', '水果', '鸡蛋', '牛奶', '豆腐', '大蒜', '生姜', '洋葱', '西兰花',
    '菠菜', '番茄', '胡萝卜', '花生', '核桃', '三文鱼', '鸡肉', '猪肉', '牛肉',
    
    # 动作/行为
    '吃', '喝', '做', '看', '学习', '了解', '知道', '明白', '记住',
}

# ==================== 敏感词替换表 ====================
# 格式：(敏感词, [推荐替换, 备选1, 备选2])

SENSITIVE_WORDS = {
    # 六字词
    '预防骨质疏松': ['预防骨Z疏松', '預防骨質疏鬆'],
    
    # 五字词
    '糖化血红蛋白': ['糖化X红蛋白', '糖化血紅蛋白'],
    '阿尔茨海默': ['阿尔茨H默', '阿爾茨海默'],
    '增强免疫力': ['增强免Y力', '增強免疫力'],
    '提高免疫力': ['提高免Y力'],
    '保护胃黏膜': ['保护胃黏M', '保護胃黏膜'],
    '降低胆固醇': ['降低胆固C', '降低膽固醇'],
    '提升免疫力': ['提升免Y力'],
    
    # 四字词
    '最大程度': ['Z大程度', '朂大程度'],
    '买一送一': ['买一S一', '買一送一'],
    '动脉硬化': ['动M硬化', '動脈硬化', '动麦硬化'],
    '心肌梗塞': ['心肌G塞', '心肌梗塞', '心机梗塞'],
    '骨质疏松': ['骨Z疏松', '骨質疏鬆'],
    '老年痴呆': ['老年C呆', '老年癡呆', '老年吃呆'],
    '肠道菌群': ['肠道菌群', '腸道菌群', '常道菌群'],
    '美容养颜': ['美容养Y', '美容養顏'],
    '排名第一': ['排名Di一', '排名苐一', '排名地一'],
    '效果最好': ['效果Z好', '效果朂好'],
    '帮助消化': ['帮助X化', '幫助消化'],
    '缓解便秘': ['缓解便M', '緩解便祕'],
    '阿司匹林': ['阿司匹L', '阿司匹林'],
    
    # 三字词
    '高血压': ['高X压', '髙洫圧', '高雪压'],
    '糖尿病': ['糖尿B', '糖尿疒', '糖尿饼'],
    '冠心病': ['冠心B', '冠心疒', '冠心饼'],
    '心脏病': ['心脏B', '心臟疒', '心脏饼'],
    '脑梗塞': ['脑G塞', '腦梗塞', '闹梗塞'],
    '脑血栓': ['脑X栓', '腦血栓', '闹血栓'],
    '关节炎': ['关节Y', '關節炎', '关节言'],
    '抑郁症': ['抑郁Z', '抑鬱症', '一郁症'],
    '焦虑症': ['焦虑Z', '焦慮症', '交虑症'],
    '胰岛素': ['胰D素', '胰島素', '一岛素'],
    '脂肪肝': ['脂肪G', '脂肪肝', '脂肪干'],
    '帕金森': ['帕金S', '帕金森', '怕金森'],
    '胆结石': ['胆结S', '膽結石', '但结石'],
    '肾结石': ['肾结S', '腎結石', '身结石'],
    '低血糖': ['低X糖', '低洫糖', '低雪糖'],
    '高血脂': ['高X脂', '高洫脂', '高雪脂'],
    '慢性病': ['慢性B', '慢性疒', '慢性饼'],
    '牙周炎': ['牙周🔥', 'yzy', '牙周言'],
    '蛋白质': ['蛋白Z', '蛋白質', '蛋白纸'],
    '抗氧化': ['抗Y化', '抗氧化', '康养化'],
    '助消化': ['助X化', '助消化', '住消化'],
    '抗衰老': ['抗S老', '抗衰老', '康帅老'],
    '免疫力': ['免Y力', '免疫力', '勉疫力'],
    '降血压': ['降X压', '降洫壓', '降雪压'],
    '降血脂': ['降X脂', '降洫脂', '降雪脂'],
    '降血糖': ['降X糖', '降洫糖', '降雪糖'],
    '前列腺': ['前列X', '前列腺', '前列先'],
    '甲状腺': ['甲状X', '甲狀腺', '甲状先'],
    '毛细血管': ['毛细X管', '毛細血管', '毛细雪管'],
    '最简单': ['Z简单', '朂简单'],
    '最便宜': ['Z便宜', '朂便宜'],
    '最先进': ['Z先进', '朂先进'],
    '最重要': ['Z重要', '朂重要'],
    '最密集': ['Z密集', '朂密集'],
    '国家级': ['国J级', '國迦级'],
    '管理员': ['管理Y', '管理員', '管理圆'],
    '银行卡': ['银行K', '銀行卡', '银杏卡'],
    '斯蒂芬': ['斯蒂F', '斯蒂芬'],
    '潜规则': ['潜规Z', '潛規則', '钱规则'],
    '荷尔蒙': ['荷尔M', '荷爾蒙'],
    
    # 两字词
    '医院': ['🏥', '醫阮', '一院'],
    '医生': ['👨‍⚕️', '醫甡', '一生'],
    '医疗': ['医L', '醫療', '一疗'],
    '医美': ['医M', '醫美', '一美'],
    '吃药': ['吃💊', '吃葯', '吃要'],
    '打针': ['打Z', '打針', '打真'],
    '血压': ['洫压', '洫圧', '雪压'],
    '血糖': ['洫糖', 'X糖', '雪糖'],
    '血脂': ['洫脂', 'X脂', '雪脂'],
    '血管': ['洫管', 'X管', '雪管'],
    '血液': ['洫液', 'X液', '雪液'],
    '失眠': ['失M', '夨眠', '师眠'],
    '头痛': ['头T', '頭痌', '投痛'],
    '便秘': ['便M', '便祕', '变密'],
    '心脏': ['🫀', '心臟', '心zang'],
    '肝脏': ['肝臟', '肝zang', '干脏'],
    '肾脏': ['肾臟', '肾zang', '身脏'],
    '大脑': ['大N', '大腦', '大闹'],
    '神经': ['神J', '神經', '身经'],
    '关节': ['关J', '關節', '关接'],
    '肌肉': ['肌R', '肌肉', '机肉'],
    '皮肤': ['皮F', '皮膚'],
    '黏膜': ['黏M', '黏膜', '年膜'],
    '细胞': ['細胞', '戏包', '🦠'],
    '细菌': ['細菌', 'xi菌', '戏菌'],
    '炎症': ['🔥症', '炎癥', '言正'],
    '症状': ['症Z', '癥狀', '正状'],
    '改善': ['改S', '盖善'],
    '体检': ['体J', '體檢', '替检'],
    '保健': ['保J', '保健', '宝健'],
    '专家': ['专J', '專家', '砖家'],
    '激素': ['激S', '激素', '机素'],
    '代谢': ['代X', '代謝', '带谢'],
    '肠道': ['肠D', '腸道', '常道'],
    '根治': ['根Z', '根治', '跟治'],
    '防治': ['防Z', '防治', '放治'],
    '治疗': ['治L', '治療', '志疗'],
    '治愈': ['治Y', '治癒', '志愈'],
    '抑制': ['抑Z', '抑制', '意志'],
    '缓解': ['缓J', '緩解', '换解'],
    '护眼': ['护Y', '護眼', '互眼'],
    '真相': ['真X', '眞相', '针相'],
    '死亡': ['Si亡', '死亾', '斯亡'],
    '真正': ['真Z', '眞正', '针正'],
    '超级': ['超J', '趫級', '抄级'],
    '必须': ['必X', '必須', '必需'],
    '唯一': ['唯Y', '唯一', '维一'],
    '绝对': ['绝D', '絕對', '决对'],
    '完美': ['完M', '完美', '玩美'],
    '抗炎': ['抗Yan', '抗炎', '康言'],
    '免疫': ['免Y', '免疫', '勉疫'],
    '促进': ['促J', '促進', '粗进'],
    '提高': ['提G', '提髙', '体高'],
    '提升': ['提S', '提升', '体升'],
    
    # 单字词
    '最': ['Z', '朂', '嘴'],
    '药': ['💊', '葯', '要'],
    '血': ['洫', 'x', '雪'],
    '病': ['疒', 'bing', '饼'],
    '脑': ['N', '腦', '闹'],
    '毒': ['D', '蝳', '读'],
    '死': ['Si', '亡', '斯'],
    '钱': ['Q', '錢', '前'],
    '送': ['S', '送', '颂'],
    '仅': ['J', '僅', '近'],
    '神': ['S', '神', '身'],
    '必': ['Bi', '必', '毕'],
    '极': ['J', '極', '及'],
    '癌': ['A', '癌', 'ai'],
}

# ==================== 书名保护 ====================
def extract_book_titles(text):
    """提取文本中所有书名号内的内容"""
    pattern = r'《([^》]+)》'
    titles = re.findall(pattern, text)
    return titles

def is_in_book_title(text, word, start_pos):
    """检查词汇是否在书名号内"""
    # 查找所有书名号的位置
    pattern = r'《[^》]+》'
    for match in re.finditer(pattern, text):
        if match.start() <= start_pos < match.end():
            return True
    return False

# ==================== 脱敏处理 ====================
def desensitize_text(text, book_titles_in_doc=None):
    """
    对文本进行脱敏处理
    
    Args:
        text: 原始文本
        book_titles_in_doc: 文档中的书名列表（用于保护）
    
    Returns:
        (脱敏后文本, 替换记录列表)
    """
    if book_titles_in_doc is None:
        book_titles_in_doc = []
    
    replacements = []
    result = text
    
    # 按长度排序敏感词（长词优先）
    sorted_words = sorted(SENSITIVE_WORDS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for sensitive_word, replacement_options in sorted_words:
        # 跳过白名单词汇
        if sensitive_word in WHITELIST:
            continue
        
        # 查找所有出现位置
        pattern = re.escape(sensitive_word)
        matches = list(re.finditer(pattern, result))
        
        if not matches:
            continue
        
        # 从后往前替换（避免位置偏移）
        for match in reversed(matches):
            start_pos = match.start()
            
            # 检查是否在书名号内
            if is_in_book_title(result, sensitive_word, start_pos):
                continue
            
            # 随机选择一个替换方案
            replacement = random.choice(replacement_options)
            
            # 执行替换
            result = result[:start_pos] + replacement + result[match.end():]
            
            # 记录替换
            replacements.append({
                'original': sensitive_word,
                'replaced': replacement,
                'position': start_pos
            })
    
    return result, replacements

# ==================== SRT 处理 ====================
def parse_srt(srt_path):
    """解析 SRT 文件"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分割成字幕块
    blocks = content.strip().split('\n\n')
    
    subtitles = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timecode = lines[1]
            text = '\n'.join(lines[2:])
            subtitles.append({
                'index': index,
                'timecode': timecode,
                'text': text
            })
    
    return subtitles

def generate_srt(subtitles, output_path):
    """生成 SRT 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles):
            f.write(subtitle['index'] + '\n')
            f.write(subtitle['timecode'] + '\n')
            f.write(subtitle['text'] + '\n')
            if i < len(subtitles) - 1:
                f.write('\n')

def desensitize_srt(input_path, output_path):
    """
    对 SRT 文件进行脱敏处理
    
    Args:
        input_path: 输入 SRT 文件路径
        output_path: 输出 SRT 文件路径
    
    Returns:
        脱敏报告字典
    """
    print(f"📖 正在读取字幕文件: {input_path}")
    
    # 解析 SRT
    subtitles = parse_srt(input_path)
    
    # 收集所有文本，用于识别书名
    all_text = '\n'.join([sub['text'] for sub in subtitles])
    book_titles = extract_book_titles(all_text)
    
    print(f"📚 识别到书名（保护区域）: {book_titles if book_titles else '无'}")
    
    # 脱敏处理
    all_replacements = []
    desensitized_subtitles = []
    
    for subtitle in subtitles:
        desensitized_text, replacements = desensitize_text(subtitle['text'], book_titles)
        
        desensitized_subtitles.append({
            'index': subtitle['index'],
            'timecode': subtitle['timecode'],
            'text': desensitized_text
        })
        
        all_replacements.extend(replacements)
    
    # 生成输出文件
    generate_srt(desensitized_subtitles, output_path)
    
    # 生成报告
    report = {
        'input_file': str(input_path),
        'output_file': str(output_path),
        'total_replacements': len(all_replacements),
        'replacements': all_replacements,
        'book_titles': book_titles,
        'unique_words': {}
    }
    
    # 统计每个敏感词的替换次数
    for rep in all_replacements:
        word = rep['original']
        if word not in report['unique_words']:
            report['unique_words'][word] = {
                'count': 0,
                'replaced_with': []
            }
        report['unique_words'][word]['count'] += 1
        if rep['replaced'] not in report['unique_words'][word]['replaced_with']:
            report['unique_words'][word]['replaced_with'].append(rep['replaced'])
    
    return report

def print_report(report):
    """打印脱敏报告"""
    print("\n" + "="*60)
    print("📊 字幕脱敏报告")
    print("="*60)
    print(f"原文件: {report['input_file']}")
    print(f"新文件: {report['output_file']}")
    print(f"替换总数: {report['total_replacements']}处")
    
    if report['book_titles']:
        print(f"\n📚 书名保护:")
        for title in report['book_titles']:
            print(f"  《{title}》保持原样")
    
    if report['unique_words']:
        print(f"\n🔄 主要替换:")
        for word, info in sorted(report['unique_words'].items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            replacements = ', '.join(info['replaced_with'])
            print(f"  {word} → {replacements} ({info['count']}次)")
    
    print("="*60)

# ==================== 主函数 ====================
def main():
    # 设置 UTF-8 输出（仅在命令行运行时）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    if len(sys.argv) < 2:
        print("用法: python desensitize_subtitles.py <项目名>")
        print("示例: python desensitize_subtitles.py AITSmx000087")
        sys.exit(1)
    
    project_name = sys.argv[1]
    
    # 文件路径 (脚本在 .claude/skills/auto_edit_video/scripts，需要回到项目根目录)
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    input_path = base_dir / 'raw_materials' / 'captions' / f'{project_name}_final.srt'
    output_path = base_dir / 'raw_materials' / 'captions' / f'{project_name}_final_desensitized.srt'
    
    if not input_path.exists():
        print(f"❌ 错误: 找不到字幕文件 {input_path}")
        sys.exit(1)
    
    # 执行脱敏
    print(f"🚀 开始脱敏处理...")
    report = desensitize_srt(input_path, output_path)
    
    # 打印报告
    print_report(report)
    
    print(f"\n✅ 脱敏完成！")

if __name__ == '__main__':
    main()
