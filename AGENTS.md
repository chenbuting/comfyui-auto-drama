# ComfyUI 短剧生成系统 · 工作准则

## 更新必写说明（硬性规则）

任何对本系统（`console/` 代码、`console/rules/*.md` 规则、前端界面、`workflows/` 工作流）的改动，
**必须在 `console/CHANGELOG.md` 顶部新增一条更新记录**，格式与要求见该文件文末。

- 代码/规则/界面改动 → 必须写（含验证方式与影响说明）
- 仅临时调试、未落盘的改动 → 不写
- 改完不写更新说明 = 本次更新未完成

## 常用命令

```bash
# 启动/重启（setsid 常驻，脱离当前会话）
cd console && python3 start_daemons.py

# 热更新规则（写 rules/*.md 后需重启服务，或通过设置界面保存）
```

## 关键约定

- 数据存 SQLite（`console.db`），运行时数据不进 git
- 配置集中在项目根 `config.json`（见 CONFIG.md），**禁止在代码里写绝对路径**
- 模型支持本地（LM Studio/Boogu）与云端（OpenAI 兼容 API），provider 在 config.json 切换
- 角色服装/发型必须与资产状态表一字不差，提示词不得自行改写
- 失败先定位责任层（资产/镜头契约/提示词/平台/随机），每轮只改一个变量
