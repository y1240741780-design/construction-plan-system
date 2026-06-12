# -*- coding: utf-8 -*-
"""
素材分析引擎 — 分析素材库文件，提取参数，辅助方案编制
支持：PDF / Excel / Word / TXT / 图片(索引)
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path(r"D:\fanben\施工方案生成系统")
PROJECT_DIR = BASE_DIR / "项目"
INDEX_FILE = PROJECT_DIR / "项目索引.json"

# ===== 1. PDF 分析 =====

def analyze_pdf(filepath):
    """提取 PDF 文本内容 + 关键参数识别"""
    try:
        import fitz
    except ImportError:
        return {"error": "pymupdf 未安装", "text": "", "params": {}}
    
    doc = fitz.open(filepath)
    full_text = ""
    pages_info = []
    
    for i, page in enumerate(doc):
        text = page.get_text()
        full_text += text + "\n"
        if i < 3:  # 前3页单独记录（通常是封面、目录、概述）
            pages_info.append({"page": i+1, "preview": text[:200]})
    
    doc.close()
    
    params = extract_params_from_text(full_text)
    
    return {
        "type": "PDF",
        "pages": len(pages_info),
        "total_chars": len(full_text),
        "text_preview": full_text[:500],
        "params": params,
        "first_pages": pages_info
    }

# ===== 2. Excel 分析 =====

def analyze_excel(filepath):
    """读取 Excel 表格，提取数据概要"""
    try:
        import openpyxl
    except ImportError:
        return {"error": "openpyxl 未安装", "sheets": [], "params": {}}
    
    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheets_info = []
    all_text = ""
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        
        # 提取前10行作为预览
        preview_rows = []
        for row in rows[:10]:
            preview_rows.append([str(c) if c is not None else "" for c in row])
        
        # 收集所有文本用于参数提取
        for row in rows:
            for cell in row:
                if cell:
                    all_text += str(cell) + " "
        
        sheets_info.append({
            "name": sheet_name,
            "rows": len(rows),
            "cols": ws.max_column or 0,
            "preview": preview_rows[:5]
        })
    
    wb.close()
    
    params = extract_params_from_text(all_text)
    
    return {
        "type": "Excel",
        "sheets": sheets_info,
        "total_rows": sum(s["rows"] for s in sheets_info),
        "params": params
    }

# ===== 3. Word 分析 =====

def analyze_word(filepath):
    """分析 Word 文档（同历史方案分析）"""
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = []
        all_text = ""
        
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                style = p.style.name if p.style else ""
                level = 0
                if "Heading" in style:
                    m = re.search(r'(\d+)', style)
                    level = int(m.group(1)) if m else 1
                paragraphs.append({"style": style, "text": text, "level": level})
                all_text += text + "\n"
        
        params = extract_params_from_text(all_text)
        
        # 提取章节标题
        headings = [p for p in paragraphs if p["level"] >= 1]
        
        return {
            "type": "Word",
            "paragraphs": len(paragraphs),
            "headings": headings[:20],
            "total_chars": len(all_text),
            "text_preview": all_text[:500],
            "params": params
        }
    except Exception as e:
        return {"type": "Word", "error": str(e), "params": {}}

# ===== 4. TXT 分析 =====

def analyze_txt(filepath):
    """分析纯文本文件"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    text = ""
    for enc in encodings:
        try:
            with open(filepath, encoding=enc) as f:
                text = f.read()
            break
        except:
            continue
    
    if not text:
        return {"type": "TXT", "error": "无法读取文件编码", "params": {}}
    
    params = extract_params_from_text(text)
    
    return {
        "type": "TXT",
        "total_chars": len(text),
        "lines": len(text.split('\n')),
        "text_preview": text[:500],
        "params": params
    }

# ===== 5. 图片索引 =====

def analyze_image(filepath):
    """图片文件：记录元信息，内容分析需 AI 视觉"""
    from pathlib import Path
    stat = Path(filepath).stat()
    
    return {
        "type": "图片",
        "size_kb": round(stat.st_size / 1024, 1),
        "format": Path(filepath).suffix.upper(),
        "note": "图片内容分析需通过对话中的 vision 工具进行",
        "params": {}
    }

# ===== 6. 参数提取核心 =====

def extract_params_from_text(text):
    """从文本中自动提取工程参数"""
    params = {}
    
    # 建筑面积
    m = re.search(r'(\d[\d,.]*)\s*(?:万)?\s*[㎡平方米m²m2]', text)
    if m:
        val = m.group(1).replace(',', '')
        params["建筑面积"] = f"{val}㎡"
    
    # 层数
    m = re.search(r'地下\s*(\d+)\s*层.*?地上\s*(\d+)\s*层', text)
    if m:
        params["地下层数"] = m.group(1)
        params["地上层数"] = m.group(2)
    
    # 栋数
    m = re.search(r'(\d+)\s*栋', text)
    if m:
        params["栋数"] = m.group(1)
    
    # 工期
    m = re.search(r'工期.*?(\d+)\s*(?:天|日历天|d)', text)
    if m:
        params["工期"] = f"{m.group(1)}天"
    
    # 结构类型
    for st in ["框架-剪力墙", "剪力墙结构", "框架结构", "钢结构", "框剪结构"]:
        if st in text:
            params["结构类型"] = st
            break
    
    # 基础类型
    for bt in ["桩基础", "筏板基础", "独立基础", "条形基础", "箱型基础"]:
        if bt in text:
            params["基础类型"] = bt
            break
    
    # 混凝土强度
    m = re.search(r'[CＣ](\d{2})\s*(?:混凝土|强度)', text)
    if m:
        params["混凝土强度"] = f"C{m.group(1)}"
    
    # 抗震等级
    m = re.search(r'抗震.*?(\d)\s*级', text)
    if m:
        params["抗震等级"] = f"{m.group(1)}级"
    
    # 钢筋级别
    grades = re.findall(r'HPB\d{3}|HRB\d{3,4}', text)
    if grades:
        params["钢筋级别"] = list(set(grades))
    
    # 日期
    m = re.search(r'(\d{4})[年.-](\d{1,2})[月.-](\d{1,2})', text)
    if m:
        params["相关日期"] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    
    # 高度
    m = re.search(r'(?:建筑)?高度\s*[:：]?\s*(\d+\.?\d*)\s*m', text)
    if m:
        params["建筑高度"] = f"{m.group(1)}m"
    
    return params

# ===== 7. 综合分析 =====

def analyze_all_materials(proj_id):
    """分析项目中所有素材"""
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return None
    
    proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
    mat_dir = proj_dir / "素材库"
    
    if not mat_dir.exists():
        print("📭 素材库为空")
        return None
    
    # 收集所有文件
    all_files = []
    for cat_dir in mat_dir.iterdir():
        if cat_dir.is_dir():
            for f in cat_dir.iterdir():
                if f.is_file():
                    all_files.append((f, cat_dir.name))
    
    if not all_files:
        print("📭 素材库为空")
        return None
    
    results = []
    merged_params = {}
    
    print(f"\n{'='*60}")
    print(f"  🔬 素材分析 — {p['name']}")
    print(f"  📂 共 {len(all_files)} 个文件")
    print(f"{'='*60}")
    
    for filepath, category in all_files:
        ext = filepath.suffix.lower()
        print(f"\n  📄 {filepath.name}")
        print(f"     分类: {category} | 格式: {ext}")
        
        try:
            if ext == '.pdf':
                result = analyze_pdf(str(filepath))
            elif ext in ['.xls', '.xlsx', '.csv', '.xlsm']:
                result = analyze_excel(str(filepath))
            elif ext in ['.doc', '.docx']:
                result = analyze_word(str(filepath))
            elif ext in ['.txt', '.md']:
                result = analyze_txt(str(filepath))
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                result = analyze_image(str(filepath))
            else:
                result = {"type": ext, "note": "不支持的内容分析", "params": {}}
            
            result["filename"] = filepath.name
            result["category"] = category
            result["analyzed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            results.append(result)
            
            # 提取参数
            params = result.get("params", {})
            if params:
                print(f"     🔑 提取参数: {json.dumps(params, ensure_ascii=False)}")
                for k, v in params.items():
                    if k not in merged_params:
                        merged_params[k] = v
            else:
                preview = result.get("text_preview", "")[:80]
                if preview:
                    print(f"     📝 内容预览: {preview}...")
                else:
                    print(f"     ℹ️  {result.get('note', '已分析')}")
        
        except Exception as e:
            print(f"     ❌ 分析失败: {e}")
            results.append({"filename": filepath.name, "error": str(e)})
    
    # 保存分析结果
    analysis_dir = proj_dir / "分析结果"
    analysis_dir.mkdir(exist_ok=True)
    
    # 逐文件报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = analysis_dir / f"素材分析报告_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "merged_params": merged_params}, f, ensure_ascii=False, indent=2)
    
    # 参数补丁（供方案生成使用）
    patch_path = proj_dir / "素材参数补丁.json"
    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(merged_params, f, ensure_ascii=False, indent=2)
    
    # 打印汇总
    print(f"\n{'='*60}")
    print(f"  📊 分析汇总")
    print(f"{'='*60}")
    print(f"  分析文件: {len(results)} 个")
    print(f"  提取参数: {len(merged_params)} 项")
    if merged_params:
        for k, v in merged_params.items():
            print(f"    • {k}: {v}")
    
    print(f"\n  📂 详细报告: {report_path}")
    print(f"  🔧 参数补丁: {patch_path}")
    print(f"  👉 生成方案时将自动应用这些参数\n")
    
    return {"results": results, "merged_params": merged_params}

def search_in_materials(proj_id, keyword):
    """在素材中搜索关键词"""
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return
    
    proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
    analysis_dir = proj_dir / "分析结果"
    
    # 先加载已有分析报告
    if analysis_dir.exists():
        for report_file in sorted(analysis_dir.glob("素材分析报告_*.json"), reverse=True):
            with open(report_file, encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"\n🔍 搜索 '{keyword}' — {report_file.name}")
            hits = 0
            for r in data.get("results", []):
                text = json.dumps(r, ensure_ascii=False)
                if keyword.lower() in text.lower():
                    print(f"  📄 {r.get('filename', '?')} ({r.get('type', '?')})")
                    params = r.get("params", {})
                    if params:
                        print(f"     参数: {json.dumps(params, ensure_ascii=False)}")
                    hits += 1
            
            if hits == 0:
                print(f"  未找到匹配")
            return
    
    print("📭 尚未分析素材，请先运行: python 技能/analyze_materials.py analyze <项目ID>")

def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"projects": []}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("素材分析引擎 — 用法:")
        print("  分析全部素材: python 技能/analyze_materials.py analyze <项目ID>")
        print("  搜索关键词:   python 技能/analyze_materials.py search <项目ID> <关键词>")
        print("  示例:")
        print("    python 技能/analyze_materials.py analyze binjiang")
        print("    python 技能/analyze_materials.py search binjiang 混凝土")
    elif sys.argv[1] == "analyze":
        proj_id = sys.argv[2] if len(sys.argv) >= 3 else "binjiang"
        analyze_all_materials(proj_id)
    elif sys.argv[1] == "search":
        if len(sys.argv) >= 4:
            search_in_materials(sys.argv[2], sys.argv[3])
        else:
            print("用法: python 技能/analyze_materials.py search <项目ID> <关键词>")
    else:
        print(f"未知命令: {sys.argv[1]}")
