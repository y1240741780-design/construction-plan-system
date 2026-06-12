# -*- coding: utf-8 -*-
"""
历史方案分析器 — 读取历史施工方案，提炼结构、用词、模式
输出：结构化模板 + 分析报告
"""
import os
import re
import json
from collections import Counter
from pathlib import Path

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

BASE_DIR = Path(r"D:\fanben\施工方案生成系统")
HISTORY_DIR = BASE_DIR / "知识库" / "历史方案"
TEMPLATE_DIR = BASE_DIR / "模板"
REPORT_DIR = BASE_DIR / "知识库" / "分析报告"

# ========== 1. 文档读取 ==========

def read_docx(path):
    """读取 Word 文档，返回段落列表 [(样式名, 文本, 层级)]"""
    doc = Document(path)
    paragraphs = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        style = p.style.name if p.style else "Normal"
        # 判断层级
        level = 0
        if "Heading" in style or "heading" in style or "标题" in style:
            level_match = re.search(r'(\d+)', style)
            level = int(level_match.group(1)) if level_match else 1
        elif p.text.strip().startswith("第") and "章" in p.text[:10]:
            level = 1
        paragraphs.append({
            "style": style,
            "text": text,
            "level": level,
            "bold": any(r.bold for r in p.runs if r.bold),
            "font_size": p.runs[0].font.size if p.runs else None
        })
    return paragraphs

def read_txt(path):
    """读取纯文本，按空行分段"""
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    paragraphs = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        level = 0
        # 检测章节标题
        if re.match(r'^第[一二三四五六七八九十\d]+章', text):
            level = 1
        elif re.match(r'^\d+\.\d+', text):
            level = 2
        elif re.match(r'^\d+、', text):
            level = 2
        paragraphs.append({
            "style": "Normal",
            "text": text,
            "level": level,
            "bold": False,
            "font_size": None
        })
    return paragraphs

# ========== 2. 结构提取 ==========

def extract_structure(paragraphs):
    """提取文档结构（章节标题树）"""
    structure = []
    current_chapter = None
    chapter_order = []
    
    for p in paragraphs:
        if p["level"] == 1:
            # 清理标题编号
            title = re.sub(r'^第[一二三四五六七八九十\d]+章\s*', '', p["text"])
            current_chapter = {
                "title": title,
                "full_title": p["text"],
                "sections": [],
                "word_count": 0
            }
            structure.append(current_chapter)
            chapter_order.append(title)
        elif p["level"] == 2 and current_chapter:
            section_title = re.sub(r'^\d+\.\d+\s*', '', p["text"])
            current_chapter["sections"].append(section_title)
        elif current_chapter:
            current_chapter["word_count"] += len(p["text"])
    
    return structure, chapter_order

# ========== 3. 用词分析 ==========

def analyze_vocabulary(paragraphs):
    """分析用词特征"""
    all_text = " ".join([p["text"] for p in paragraphs])
    
    # 分词（中文：按字符+常见词组）
    words = re.findall(r'[\u4e00-\u9fff]{2,}', all_text)
    word_counter = Counter(words)
    
    # 提取固定搭配（3-6字短语，出现2次以上）
    phrases = []
    for length in [3, 4, 5, 6]:
        for i in range(len(all_text) - length):
            phrase = all_text[i:i+length]
            if re.match(r'^[\u4e00-\u9fff]+$', phrase):
                phrases.append(phrase)
    phrase_counter = Counter(phrases)
    common_phrases = [(p, c) for p, c in phrase_counter.most_common(50) if c >= 2 and len(p) >= 4]
    
    # 句式特征
    sentences = re.split(r'[。；\n]', all_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_lengths = [len(s) for s in sentences]
    avg_sentence_len = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    
    # 常见动词
    action_verbs = re.findall(r'(施工|浇筑|安装|绑扎|支设|搭设|验收|检查|测量|控制|管理|组织|编制|审查|审批|监测|检测)', all_text)
    verb_counter = Counter(action_verbs)
    
    return {
        "top_words": word_counter.most_common(30),
        "common_phrases": common_phrases[:20],
        "avg_sentence_length": round(avg_sentence_len, 1),
        "sentence_count": len(sentences),
        "top_action_verbs": verb_counter.most_common(15),
        "total_characters": len(all_text)
    }

# ========== 4. 模式提炼 ==========

def distill_patterns(structure_list, vocab_list):
    """从多个文档的分析结果中提炼通用模式"""
    # 章节频率统计
    chapter_freq = Counter()
    section_freq = Counter()
    
    for struct, _ in structure_list:
        for ch in struct:
            chapter_freq[ch["title"]] += 1
            for sec in ch["sections"]:
                section_freq[sec] += 1
    
    doc_count = len(structure_list)
    
    # 常用章节（出现率>=50%）
    common_chapters = [
        {"title": title, "frequency": f"{count}/{doc_count}", "ratio": count/doc_count}
        for title, count in chapter_freq.most_common(20)
        if count / doc_count >= 0.5
    ]
    
    # 合并词汇特征
    merged_vocab = {
        "top_words": Counter(),
        "top_verbs": Counter(),
        "common_phrases": Counter()
    }
    for v in vocab_list:
        for w, c in v.get("top_words", []):
            merged_vocab["top_words"][w] += c
        for w, c in v.get("top_action_verbs", []):
            merged_vocab["top_verbs"][w] += c
        for w, c in v.get("common_phrases", []):
            merged_vocab["common_phrases"][w] += c
    
    return {
        "common_chapters": common_chapters,
        "vocabulary": {
            "top_words": merged_vocab["top_words"].most_common(30),
            "top_verbs": merged_vocab["top_verbs"].most_common(15),
            "common_phrases": merged_vocab["common_phrases"].most_common(20),
        },
        "doc_count": doc_count
    }

# ========== 5. 生成分析报告 ==========

def generate_report(doc_name, structure, vocab):
    """生成单文档分析报告"""
    lines = []
    lines.append(f"# 文档分析报告：{doc_name}")
    lines.append("")
    lines.append("## 一、结构分析")
    lines.append("")
    
    for ch in structure:
        lines.append(f"### {ch['full_title']}")
        lines.append(f"- 字数：{ch['word_count']}")
        lines.append(f"- 子节数：{len(ch['sections'])}")
        for sec in ch['sections']:
            lines.append(f"  - {sec}")
        lines.append("")
    
    lines.append("## 二、用词特征")
    lines.append("")
    lines.append(f"- 总字符数：{vocab['total_characters']}")
    lines.append(f"- 句子数：{vocab['sentence_count']}")
    lines.append(f"- 平均句长：{vocab['avg_sentence_length']} 字")
    lines.append("")
    lines.append("### 高频词汇 Top 20")
    lines.append("")
    for word, count in vocab["top_words"][:20]:
        lines.append(f"- {word}（{count}次）")
    lines.append("")
    lines.append("### 常见动词")
    lines.append("")
    for verb, count in vocab["top_action_verbs"]:
        lines.append(f"- {verb}（{count}次）")
    lines.append("")
    lines.append("### 固定搭配/常用短语")
    lines.append("")
    for phrase, count in vocab["common_phrases"]:
        lines.append(f"- {phrase}（{count}次）")
    
    return "\n".join(lines)

def save_template(name, structure, vocab, patterns=None):
    """将提炼的模板保存为 JSON"""
    template = {
        "name": name,
        "source": str(HISTORY_DIR),
        "structure": structure,
        "vocabulary": vocab,
        "patterns": patterns
    }
    outpath = TEMPLATE_DIR / "施工组织设计" / f"{name}_提炼模板.json"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    return outpath

# ========== 6. 主流程 ==========

def analyze_all():
    """扫描历史方案目录，分析所有文档"""
    if not HISTORY_DIR.exists():
        print(f"❌ 目录不存在: {HISTORY_DIR}")
        return
    
    files = list(HISTORY_DIR.glob("*"))
    docx_files = [f for f in files if f.suffix.lower() == '.docx']
    txt_files = [f for f in files if f.suffix.lower() == '.txt']
    
    all_files = docx_files + txt_files
    
    if not all_files:
        print(f"📭 历史方案目录为空，请放入 .docx 或 .txt 文件：")
        print(f"   {HISTORY_DIR}")
        return
    
    if docx_files and not HAS_DOCX:
        print("⚠️  python-docx 未安装，将跳过 .docx 文件")
    
    all_structures = []
    all_vocabs = []
    
    for fpath in all_files:
        print(f"\n{'='*60}")
        print(f"📄 分析: {fpath.name}")
        print(f"{'='*60}")
        
        try:
            if fpath.suffix.lower() == '.docx':
                if not HAS_DOCX:
                    print("  ⚠️ 跳过（python-docx 未安装）")
                    continue
                paragraphs = read_docx(str(fpath))
            else:
                paragraphs = read_txt(str(fpath))
            
            structure, chapter_order = extract_structure(paragraphs)
            vocab = analyze_vocabulary(paragraphs)
            
            print(f"  章节数: {len(structure)}")
            print(f"  章节列表: {', '.join([c['title'] for c in structure])}")
            print(f"  总字数: {vocab['total_characters']}")
            
            # 生成报告
            report = generate_report(fpath.stem, structure, vocab)
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            report_path = REPORT_DIR / f"{fpath.stem}_分析报告.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"  ✅ 分析报告: {report_path}")
            
            # 保存模板
            template_path = save_template(fpath.stem, structure, vocab)
            print(f"  ✅ 提炼模板: {template_path}")
            
            all_structures.append((structure, chapter_order))
            all_vocabs.append(vocab)
            
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
    
    # 多文档综合提炼
    if len(all_structures) >= 2:
        print(f"\n{'='*60}")
        print(f"🔬 综合模式提炼（基于 {len(all_structures)} 份文档）")
        print(f"{'='*60}")
        
        patterns = distill_patterns(all_structures, all_vocabs)
        
        # 保存综合模板
        master_path = save_template("_综合模式", [], {}, patterns)
        print(f"  ✅ 综合模式: {master_path}")
        
        # 输出摘要
        print(f"\n  📊 通用章节结构（出现率≥50%）:")
        for ch in patterns["common_chapters"]:
            print(f"     {ch['title']} ({ch['frequency']})")
        print(f"\n  📝 高频动词 Top 10:")
        for verb, count in patterns["vocabulary"]["top_verbs"][:10]:
            print(f"     {verb}（{count}次）")
    
    print(f"\n{'='*60}")
    print(f"✅ 全部分析完成！共处理 {len(all_files)} 个文档")
    print(f"📂 分析报告: {REPORT_DIR}")
    print(f"📂 提炼模板: {TEMPLATE_DIR / '施工组织设计'}")

if __name__ == "__main__":
    analyze_all()
