# ComfyUI 批量生成控制台

批量填写 H3 提示词 → 一键提交远程 ComfyUI → 自动监控、记录耗时、下载结果。

## 快速开始

```bash
cd /Volumes/macos/Knowledge_Base_V2/comfyui项目/batch_console
python3 batch_console.py 8890
```

浏览器打开 <http://127.0.0.1:8890>。

## 数据存储（SQLite）

- 系统状态（项目库、剧本、提示词、任务、配置）存于 `console.db`（SQLite，事务安全、支持多进程并发）
- 首次启动会自动把旧版 `batch_state.json` 迁移进数据库，原文件保留为 `batch_state.json.bak`
- 提交/生成记录导出为 `batch_records.csv` / `batch_records.md`；参考图、分镜、视频存于 `../素材/` 与 `../comfyui_backup/outputs/`
- `console.db` 是运行时数据，**不要提交进 git**；出售/开源时建议在 `.gitignore` 里排除，并保留一份空库或首次启动自动建库

## 使用流程

1. **连接测试**：顶部填远程服务器地址（默认 `http://192.168.1.23:8188`），点「连接测试」，绿灯说明在线
2. **填任务**：每行一个任务，或点「导入 CSV/JSON」批量粘贴
   - 模式：`T2V`（文生视频）/ `I2V`（图生视频，需选首帧图）
   - 分辨率：`0.4` ≈ 480p 预览，`1.0` ≈ 768p 高清，`1.5` 更清晰
   - 提示词必须按 H3 规范（`integrated_multimodal_description` 三字段）
   - **也可以直接粘贴 AI 对话导出的「Prompt 分块」格式**（如 `Prompt 1（0:00-0:15）` + `Copy` + 三字段正文），自动按 Prompt 分段填表，剥掉 `Copy` 无效标记，镜头重排为 `[Shot 1]`，时长从标题时间自动解析
   - **📜 剧本 JSON**：导入弹窗第三个页签，粘贴剧本 JSON（Novel-Director / ArcReel / 通用分镜格式均可），自动拆段、匹配角色/场景参考图、无提示词时自动组装 H3 三段式（见下文）
3. **提交**：勾选要跑的任务 → 点「🚀 提交选中任务」
4. **监控**：任务卡片自动刷新（排队中 / 生成中 / 已完成 / 失败），显示实测耗时
5. **结果**：完成后自动下载到 `../comfyui_backup/outputs/`，耗时自动写入 `batch_records.csv` 和 `batch_records.md`

## 🔗 链式衔接（连续镜头）

勾选顶部「链式衔接」后，任务按表格顺序串联：**上一段生成完 → 自动抽最后一帧 → 上传服务器 → 作为下一段首帧参考（`<Picture 1>`）→ 自动提交下一段**，人物、服装、光影自然延续。

用法：

1. 勾选「链式衔接」
2. 按时间顺序填任务（第一段可以是 T2V，后面直接写 T2V 式提示词即可）
3. 提交后系统自动逐段推进：前一段完成才提交后一段，卡片会先显示「等待上段」
4. 已实测：两段 5 秒 480p，分别 65 秒 / 62 秒完成，衔接帧人物/服装/光线一致

提示词自动改造规则：

- 如果提示词已含 `For the target video` / `<Picture 1>`（I2VA/Ref2VA 写法），原样保留
- 如果是普通 T2V 三段式，自动在前面加 I2VA 对齐指令，并在 `[Shot 1]` 注入「人物、光线、服装、构图与 `<Picture 1>` 完全延续」约束
- 衔接帧命名：`chain_<任务id>.png`，上传到服务器 `input/` 根目录

注意：

- 链式模式下除第一段外，每段的任务参数（模式/首帧图）会被自动改写为 I2V + 链帧
- 想打断链条：取消勾选「链式衔接」，或把任务分两次提交

## 🎭 R2V 多参考模式（角色一致性）

当剧情人物多、单帧参考容易"跑脸"（比如上一段是背影，下一段模型脑补正脸）时，用 **R2V 多参考**：

1. 顶部「角色参考图」选一张**人物正脸清晰图**（如 `参考_第1段正脸.png`）
2. 勾选「链式衔接」
3. 提交后：第一段照常生成；从第二段起自动走 R2V 工作流（`video_minimax_h3_r2v`），**同时参考「角色正脸图 + 上段末帧」**，既锁脸又衔接画面
4. 每行也可单独选 R2V 模式，用行内首帧图作为参考图

R2V 工作流已内置加速：

- **无审查 CLIP**：`qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors`
- **Turbo LoRA** 4 步 + SageAttention + int8（与 T2V/I2V 一致）
- 参考图最多 3 张（正脸 / 上段末帧 / 场景参考）

注意：R2V 比 I2V 慢一些（参考 token 全程参与采样），但角色一致性明显更稳。

## 📜 剧本 JSON 导入（剧本 → 分镜 → 参考资产）

导入弹窗第三个页签「剧本 JSON」，支持三种剧本结构，自动完成：

1. **拆段**：`storyboard_list` / `segments` / `scenes` 每个分镜 → 一行任务
2. **角色匹配**：`role_list` / `characters` 角色表 → 自动匹配本地锚点图（关键词表 + 文件名），前两个角色进链式 R2V 参考
3. **场景匹配**：分镜的 `scene` / `location` 字段 → 匹配场景锚点（麦田 / 卧室 / 校园 / 办公室），有锚点图的自动作为该段参考
4. **提示词组装**：分镜有 `prompt` 则规范化为 H3 三段式；没有则按「场景 + 角色 + 动作 + 对白 + 运镜」组装，对白自动加 `<d>[Chinese] ...</d>`，默认 `non_diegetic_music: N/A`

Novel-Director 风格示例：

```json
{
  "title": "雨夜加班",
  "role_list": [
    {"role_name": "苏晚", "role_desc": "年轻女职员，白衬衫深色铅笔裙", "avatar": "角色锚点_女孩_1980s.png"},
    {"role_name": "林深", "role_desc": "男上司，深色西装", "avatar": "角色锚点_男孩_1980s.png"}
  ],
  "storyboard_list": [
    {"id": 1, "scene": "办公室", "roles": ["苏晚", "林深"], "camera": "缓慢推近",
     "action": "两人在走廊擦肩", "dialogue": "今天……能陪我去个地方吗？", "duration": 10},
    {"id": 2, "scene": "麦田夜景", "roles": ["苏晚", "林深"], "camera": "中景固定",
     "action": "并肩走在田埂上", "dialogue": "好呀。", "duration": 10}
  ]
}
```

ArcReel 风格：`characters: [{name, description, image}]` + `segments: [{index, characters, location, dialogue, duration}]` 同样支持。

导入后：

- 顶部「角色参考图1/2」「场景参考图」自动填上匹配的锚点图
- 每行模式自动设为 `R2V`（有参考）或 `T2V`（无参考）
- 未匹配到角色/场景的段会弹黄色警告，不会静默出错
- 勾选「链式衔接」提交，即可自动逐段推进（上段末帧 → 下段首帧）

### ✨ 深度扩写细节（剧本 → 可执行分镜）

剧本页签默认勾选「深度扩写细节」+「AI 智能扩写」，导入时把简略分镜扩写成 H3 规范的专业描述：

**AI 智能扩写（优先）**：调用本地 LM Studio（`127.0.0.1:1234`，模型 `qwen3.6-27b-abliterated-mlx`），
理解剧情语义后自动补全环境、光线色温、人物动作、情绪表演、运镜、声音设计。剧本只写
「两人在麦田相遇」也能扩成完整分镜；对白原文一字不改，不发明剧情。LM Studio 不可用/
token 无效时自动回退下面的规则扩写。token 在控制台「剧本 JSON」页签填入（存本地 state，
不落日志），或设环境变量 `LM_API_TOKEN`。实测 2 段约 3-4 分钟。

**规则扩写（兜底）**：

- **运镜词典**：`缓慢推近`/`固定机位`/`特写`/`跟拍`/`环绕` 等中文 → 英文自然句（类型+幅度+速度）
- **场景氛围**：按场景补充光线、色调、氛围（月光麦浪 / 钨丝灯卧室 / 黄昏校园 / 雨夜办公室）
- **动作细节**：`并肩`/`擦肩`/`对视`/`低头` 等 → 精确动作描述
- **身份锁定**：人物与参考图身份/发型/服装/肤色完全一致
- **负面约束**：no ghosting / no double exposure / no extra people / no floating particles
- **声音设计**：按场景自动生成 `overall_soundscape`（麦浪虫鸣 / 时钟滴答 / 键盘雨声）
- 对白自动 `<d>[Chinese] 原文</d>`，默认 `non_diegetic_music: N/A`

分镜自带 `prompt` 时保留原文，仅补全缺失字段，不改你的叙事。

## CSV 格式

表头：`name,mode,duration,mp,image,images,prefix,prompt`

```csv
name,mode,duration,mp,image,prefix,prompt
科幻展示,t2v,10,1.0,,,video/H3_batch_1,"integrated_multimodal_description: ..."
出镜段,i2v,10,1.0,3号_1s.png,,video/H3_batch_2,"For the target video, ..."
角色段,r2v,10,1.0,,参考_第1段正脸.png,video/H3_batch_3,"integrated_multimodal_description: ..."
```

- 提示词含逗号/换行时，整段用英文双引号包裹
- `images` 列（R2V 多参考）用 `|` 分隔多张图
- 也可以粘贴 JSON：`[{"name":"...","mode":"t2v","duration":10,"mp":1.0,"image":"","prefix":"...","prompt":"..."}]`
- 「Prompt 分块」格式示例（导入框会智能识别，无需手动选格式）：

```text
雨夜加班（第 1-10 段）
Prompt 1（0:00-0:15）

Copy
integrated_multimodal_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: ...
```

## 说明与限制

- 图转换复用 `工作流/build_api_graphs.py`（Turbo LoRA 4 步 + TurboSampler + 9:16 竖版），改动模板即改全局
- 首帧图从 `出镜素材/`、`素材/` 目录选择，提交 I2V 前自动上传到服务器 `input/`
- 同一任务名重复提交会被跳过（防误重跑）
- 服务器 `/history` 是内存存储，重启即丢——本工具任务完成后立即下载+记录，重启服务器前先看本地记录
- 想换横向或其他比例，改 `工作流/build_api_graphs.py` 里 `aspect_ratio` 一行
- H3 输出 mp4 在 `/history` 里挂在 `images` 字段下（不是 `videos`），链式抽帧按文件扩展名识别，已处理

## 文件

| 文件 | 作用 |
|---|---|
| `batch_console.py` | 后端：提交/监控/下载/记录/导入导出 |
| `index.html` | 前端：任务表格 + 状态卡片 |
| `batch_state.json` | 任务状态持久化（自动生成） |
| `batch_records.csv/md` | 实测耗时记录（自动生成） |
