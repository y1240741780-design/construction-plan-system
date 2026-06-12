# -*- coding: utf-8 -*-
"""
方案模板选择器 — 从模板库中选择方案类型，输出大纲和参数需求
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(r"D:\fanben\施工方案生成系统")
TEMPLATE_DB = BASE_DIR / "模板" / "方案模板库.json"
CONFIG_DIR = BASE_DIR / "配置"

def load_templates():
    with open(TEMPLATE_DB, encoding='utf-8') as f:
        data = json.load(f)
    return data["templates"]

def show_all():
    """展示所有可用模板"""
    templates = load_templates()
    print(f"\n{'='*55}")
    print(f"  📋 施工方案模板库（共 {len(templates)} 种）")
    print(f"{'='*55}")
    
    # 按分类分组
    categories = {}
    for t in templates:
        cat = t["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    
    for cat, tmps in categories.items():
        print(f"\n  【{cat}】")
        for t in tmps:
            danger = " ⚠️危大" if t.get("dangerous_project") else ""
            expert = f"\n       专家论证：{t['expert_review']}" if t.get("expert_review") else ""
            print(f"    {t['icon']} [{t['id']}] {t['name']}{danger}")
            print(f"       {t['description']}{expert}")
    
    print(f"\n{'='*55}")
    print("  使用方式: python 技能/select_template.py <模板ID>")
    print("  示例:     python 技能/select_template.py rebar")
    print(f"{'='*55}\n")
    return templates

def show_detail(template_id):
    """展示单个模板详情"""
    templates = load_templates()
    t = next((t for t in templates if t["id"] == template_id), None)
    
    if not t:
        print(f"❌ 未找到模板: {template_id}")
        print(f"   可用ID: {', '.join([t['id'] for t in templates])}")
        return None
    
    print(f"\n{'='*55}")
    print(f"  {t['icon']} {t['name']}施工方案")
    print(f"{'='*55}")
    print(f"\n  📝 描述: {t['description']}")
    print(f"  🏷️  分类: {t['category']}")
    print(f"  🏢 适用: {t['applicable']}")
    
    if t.get("dangerous_project"):
        print(f"  ⚠️  危大工程: 是")
        print(f"  👨‍⚖️  专家论证: {t.get('expert_review', '详见规范')}")
    
    print(f"\n  📐 方案大纲:")
    for i, item in enumerate(t["outline"], 1):
        print(f"     {i}. {item}")
    
    print(f"\n  🔑 关键参数:")
    for p in t["key_params"]:
        print(f"     • {p}")
    
    print(f"\n  📚 依据规范:")
    for n in t["key_norms"]:
        print(f"     • {n}")
    
    print(f"\n{'='*55}\n")
    
    # 保存选择
    selection = {
        "template_id": t["id"],
        "template_name": t["name"],
        "outline": t["outline"],
        "key_params": t["key_params"],
        "key_norms": t["key_norms"],
        "dangerous_project": t.get("dangerous_project", False),
        "expert_review": t.get("expert_review", "")
    }
    
    sel_path = CONFIG_DIR / "当前模板选择.json"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(sel_path, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已保存选择: {sel_path}")
    print(f"  👉 下一步：在对话中逐步确认参数，然后生成方案\n")
    
    return selection

def compare_templates():
    """对比所有模板"""
    templates = load_templates()
    print(f"\n{'='*70}")
    print(f"  📊 模板对比总览")
    print(f"{'='*70}")
    print(f"  {'ID':<16} {'名称':<12} {'分类':<10} {'章节数':<6} {'危大':<4}")
    print(f"  {'-'*48}")
    for t in templates:
        danger = "是" if t.get("dangerous_project") else ""
        print(f"  {t['id']:<16} {t['name']:<12} {t['category']:<10} {len(t['outline']):<6} {danger:<4}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_all()
    elif sys.argv[1] == "--compare":
        compare_templates()
    else:
        show_detail(sys.argv[1])
