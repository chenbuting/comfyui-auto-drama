#!/usr/bin/env python3
"""生成《生成耗时记录.md》：按批次对比每次运行的参数与耗时。

数据源：ComfyUI /history（execution_start/execution_success 毫秒时间戳）。
每个任务记录：批次、分辨率、模式、时长、Seed、开始/结束、耗时、输出、质检备注。
用法：python3 write_record.py [--rebuild]
"""

import json
import os
import time
import urllib.request

SERVER = os.environ.get("COMFYUI_URL", "http://192.168.1.23:8188")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(BASE, "生成耗时记录.md")

# 批次 1：480x864 / 0.4MP / 初版提示词
BATCH1 = {
    "T0_title": "2274de16-fe16-4894-ac3c-f35ced4417e8",
    "T2_scifi": "9569978a-a50a-44c1-87d4-7528c38ff1cf",
    "T3_3d": "88b1fe7f-1cd5-4b03-8af1-2c28f99ebdae",
    "T4_paper": "47a4def3-7bc4-4b09-b377-76aad7f6c44d",
    "T7_cta": "dfabe9f8-928f-4ab2-bb2a-96b8651a319a",
    "T1_opening": "c1073dc3-3a82-45c1-9ada-3522c5796dc3",
    "T5_config": "6bc11e18-dbae-4095-a0bd-53e4f6885297",
    "T6_humor": "39210eae-6174-4817-b5d8-e9fb3f8666a0",
}

# 批次 2：768p T2V 五条（00002）
BATCH2 = {
    "T0_title": "35f80334-a753-40e4-8de0-d02a1de6e183",
    "T2_scifi": "55209ee7-c96a-46df-bc9d-9776e9f0255a",
    "T3_3d": "572ab3b1-50fe-4d8c-b44b-2f03210dbbc4",
    "T4_paper": "ebcadcc5-11be-4a43-89f1-cc76f9e16796",
    "T7_cta": "9edb4d36-b444-4010-9ec1-080b66c33ea0",
}

# 批次 3：768p I2V 三条（00003）
BATCH3 = {
    "T1_opening": "6a796f96-e053-49b2-89dc-879069a0c8a4",
    "T5_config": "86566b7b-9c4e-4952-87e9-5821bf7e2299",
    "T6_humor": "8a9c2176-2ecf-483d-a57e-bf0b7591dd6b",
}

NAME = {
    "T0_title": "片头 MINIMAX H3", "T1_opening": "开场出镜+对白",
    "T2_scifi": "展示①科幻", "T3_3d": "展示②3D", "T4_paper": "展示③纸拼贴",
    "T5_config": "配置介绍+对白", "T6_humor": "幽默段+对白", "T7_cta": "结尾 CTA",
}

MODES = {"T0_title": "T2V", "T2_scifi": "T2V", "T3_3d": "T2V", "T4_paper": "T2V",
         "T7_cta": "T2V", "T1_opening": "I2V", "T5_config": "I2V", "T6_humor": "I2V"}
DUR = {"T0_title": 8, "T2_scifi": 10, "T3_3d": 10, "T4_paper": 10,
       "T7_cta": 8, "T1_opening": 10, "T5_config": 10, "T6_humor": 10}

# 批次 1 质检备注（用户反馈 + 实测）
NOTES1 = {
    "T7_cta": "文字错误：应为'辉哥学AI'，实际生成为无关印章文字",
    "T1_opening": "6-8s 画面有异物飞过",
    "T5_config": "右手变色",
    "T6_humor": "钱包明显变色",
    "T0_title": "OK（低清）", "T2_scifi": "OK（低清）",
    "T3_3d": "OK（低清）", "T4_paper": "OK（低清）",
}

SEEDS = {
    "T0_title": 75291004820246, "T2_scifi": 718594657610073,
    "T3_3d": 795263069031780, "T4_paper": 923647400592540,
    "T7_cta": 334589047446745, "T1_opening": 45433196751309,
    "T5_config": 204837648526926, "T6_humor": 763411942193493,
}


def api_get(path):
    with urllib.request.urlopen(SERVER + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fmt(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}分{s:02d}秒"


def row(batch, task, pid, seed, res, note=""):
    try:
        h = api_get(f"/history/{pid}")
        e = h.get(pid, {})
    except Exception:
        e = {}
    msgs = {m[0]: m[1] for m in e.get("status", {}).get("messages", [])}
    t0 = msgs.get("execution_start", {}).get("timestamp")
    t1 = msgs.get("execution_success", {}).get("timestamp")
    st = e.get("status", {}).get("status_str", "?")
    dur = fmt((t1 - t0) / 1000.0) if t0 and t1 else "-"
    t0s = time.strftime("%H:%M:%S", time.localtime(t0 / 1000)) if t0 else "-"
    t1s = time.strftime("%H:%M:%S", time.localtime(t1 / 1000)) if t1 else "-"
    outs = []
    for nid, out in e.get("outputs", {}).items():
        for kind in ("images", "videos", "audio"):
            for item in out.get(kind, []):
                outs.append(f"{item.get('filename')}")
    return (
        f"| {batch} | {task} | {NAME.get(task, task)} | {MODES.get(task, '-')} "
        f"| {DUR.get(task, '-')}s | {res} | {seed} | {t0s} | {t1s} | {dur} "
        f"| {st} | {', '.join(outs) or '-'} | {note} |"
    )


def main():
    lines = [
        "# MiniMax H3 生成耗时记录（参数对比版）",
        "",
        "> 项目：《MiniMax H3 开源模型介绍视频》 2026-08-12",
        "> 数据来源：ComfyUI /history execution 时间戳（毫秒），真实记录",
        "> 批次说明：批次1 = 480x864(0.4MP) 初版提示词；批次2 = 768p T2V 五条；批次3 = 768p I2V 三条",
        "",
        "| 批次 | 任务 | 内容 | 模式 | 时长 | 分辨率 | Seed | 开始 | 结束 | 耗时 | 状态 | 输出 | 质检备注 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for task, pid in BATCH1.items():
        lines.append(row("批次1", task, pid, SEEDS[task], "480x864", NOTES1.get(task, "")))
    for task, pid in BATCH2.items():
        lines.append(row("批次2", task, pid, SEEDS[task], "768x1376", "待质检"))
    for task, pid in BATCH3.items():
        lines.append(row("批次3", task, pid, SEEDS[task], "768x1376", "待质检"))
    lines += [
        "",
        "## 参数对比结论（批次2 完成后填写）",
        "",
        "- 分辨率对比：批次1(T2V 10s) 约 2-3 分钟/条；批次2(T2V 10s, 768p) 约 11-12 分钟/条",
        "- I2V 768p：开场(含模型切换) 25分33秒，常驻后配置 9分05秒、幽默 16分34秒",
        "- 提示词修复效果：钱包变色/右手变色/异物飞过/CTA 文字=辉哥学AI 已在新批次重跑（待最终质检确认）",
        "- 推荐参数：正式成片用 768p/1.0MP/修复版提示词；快速预览用 0.4MP",
    ]
    with open(RECORD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"已写入 {RECORD}")


if __name__ == "__main__":
    main()
