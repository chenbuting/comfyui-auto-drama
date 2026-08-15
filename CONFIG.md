# 配置说明（CONFIG）

复制 `config.example.json` 为 `config.json`（同一目录），按下面说明填写。
**所有路径均为相对项目根目录的相对路径**，禁止写绝对路径（如 `/Users/xxx/...`）。
所有支持云端 API 的配置项，本地服务不可用时自动降级到云端。

---

## comfyui（远程生成服务器）

| 字段 | 说明 | 示例 |
|---|---|---|
| `server` | ComfyUI 服务器地址（局域网远程机或本机） | `http://192.168.1.23:8188` |
| `workflow_dir` | 工作流脚本目录（`build_api_graphs.py`、`*_api_template.json` 所在处） | `workflows` |

**说明**：远程 ComfyUI 需要安装 MiniMax H3 节点与模型（ref2va 工作流、turbo LoRA、SageAttention、无审查 CLIP），详见 `README.md` 的"远程依赖"章节。

## storage（存储路径）

| 字段 | 说明 | 示例 |
|---|---|---|
| `output_dir` | 生成视频/图片的下载目录 | `comfyui_backup/outputs` |
| `asset_dirs` | 参考素材目录列表（角色锚点图、场景图、分镜图存放处） | `["素材", "出镜素材"]` |

## llm（语言模型：剧本生成 / 改写 / 提示词扩写）

| 字段 | 说明 | 示例 |
|---|---|---|
| `provider` | 当前使用本地还是云端：`local` 或 `cloud` | `local` |
| `provider_type` | 云端接口格式：`openai` / `claude` / `dashscope` | `openai` |
| `local.url` | 本地 OpenAI 兼容服务地址（LM Studio / Ollama） | `http://127.0.0.1:1234` |
| `local.model` | 本地模型名（需已在 LM Studio 加载） | `qwen3.6-27b-abliterated-mlx` |
| `local.token` | 本地服务鉴权 token（无鉴权留空） | `sk-lm-xxx` |
| `cloud.enabled` | 是否启用云端 API（本地不可用时自动降级） | `false` |
| `cloud.base_url` | 云端 OpenAI 兼容地址 | `https://api.openai.com/v1` |
| `cloud.api_key` | 云端 API Key（**不要提交进 git**） | `sk-xxx` |
| `cloud.model` | 云端模型名 | `gpt-4o-mini` |

**说明**：
- 只要接口兼容 OpenAI `/v1/chat/completions` 即可，DeepSeek、通义、Moonshot、OpenRouter 等都可用（填各自 base_url / api_key / model）。
- 不兼容 OpenAI 的服务用适配器：`claude`（Anthropic Messages）、`dashscope`（通义原生）；
  适配器自动转换请求/响应格式，主流程无感知。
- 云端不可用且本地离线时，控制台自动回退内置规则扩写（效果差一些，但能跑）。

## image_gen（文生图：角色锚点图 / 场景图 / 分镜图）

| 字段 | 说明 | 示例 |
|---|---|---|
| `provider` | `local` 或 `cloud` | `local` |
| `provider_type` | 云端接口格式：`openai` / `dashscope` | `openai` |
| `local.url` | 本地生图服务（Boogu-Image）地址 | `http://127.0.0.1:8081` |
| `cloud.enabled` | 是否启用云端文生图 | `false` |
| `cloud.base_url` | 云端 OpenAI 兼容图片接口 | `https://api.openai.com/v1` |
| `cloud.api_key` | 云端 Key | `sk-xxx` |
| `cloud.model` | 图片模型名 | `gpt-image-1` |

**说明**：
- 本地部署见 `README.md` 的"Boogu-Image 本地部署"（Apple Silicon / MLX，一键脚本 `scripts/deploy_boogu.sh`）
- 云端接口按 OpenAI `/v1/images/generations` 兼容实现（支持 `b64_json` 或 `url` 返回）；
  `provider: cloud` 时走云端，主端点失败自动降级本地
- 通义万相用 `provider_type: dashscope`（异步任务 + 自动轮询）

## vision（图片质检：检查穿帮 / 服装一致性 / 人数）

| 字段 | 说明 | 示例 |
|---|---|---|
| `base_url` | OpenAI 兼容视觉服务（本地或云端） | `http://127.0.0.1:8001/v1` |
| `api_key` | 服务鉴权（无则留空） | `sk-xxx` |
| `model` | 视觉模型名 | `qwen-vl-max` |

## console（控制台自身）

| 字段 | 说明 | 示例 |
|---|---|---|
| `port` | 控制台 Web 端口 | `8890` |

---

## 环境变量覆盖（可选）

以下环境变量可覆盖 config.json（优先于配置文件）：

| 环境变量 | 覆盖项 |
|---|---|
| `BATCH_CONSOLE_CONFIG` | 指定 config.json 路径 |
| `COMFYUI_SERVER` | `comfyui.server` |
| `LLM_CLOUD_API_KEY` | `llm.cloud.api_key` |
| `IMAGE_CLOUD_API_KEY` | `image_gen.cloud.api_key` |
