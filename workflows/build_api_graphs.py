#!/usr/bin/env python3
"""构建 MiniMax H3 视频生成任务的 API 图（ComfyUI /prompt 格式）。

T2V：从前端工作流 JSON 转换（含 4 步加速 LoRA + TurboSampler）
I2V：从队列快照模板改造（绕过 PromptEnhancer，直接喂规则化提示词）
"""

import json
import os
import random
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
T2V_WF = os.path.join(BASE, "minimax_h3_t2v_turbo.json")
I2V_TEMPLATE = os.path.join(BASE, "i2v_api_template.json")
R2V_TEMPLATE = os.path.join(BASE, "r2v_api_template.json")
TASKS_DIR = os.path.join(BASE, "tasks")

# Ref2VA 加速 + 无审查模型配置（覆盖 r2v 模板默认值）
R2V_TURBO_LORA = "minimax_h3_turbo_v4_step600_ema.safetensors"
R2V_LORA_STRENGTH = 0.75
R2V_STEPS = 4
R2V_CLIP_DEFAULT = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"  # 开源默认：官方文本编码器
R2V_UNET_DEFAULT = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
R2V_FINAL_STEPS = 20
R2V_MAX_IMAGES = 8  # 官方 Ref2VA 上限 9 张；默认 8（主角多视图 + 场景 + 分镜）


def _r2v_cfg():
    """从项目根 config.json 读 models.r2v（unet/clip），失败用默认值。"""
    try:
        with open(os.path.join(os.path.dirname(BASE), "config.json"), encoding="utf-8") as f:
            d = json.load(f)
        m = (d.get("models") or {}).get("r2v") or {}
        max_n = int((d.get("console") or {}).get("max_ref_images") or R2V_MAX_IMAGES)
        return {
            "unet": m.get("unet") or R2V_UNET_DEFAULT,
            "clip": m.get("clip") or R2V_CLIP_DEFAULT,
            "max_images": min(max_n, 9),
        }
    except Exception:
        return {"unet": R2V_UNET_DEFAULT, "clip": R2V_CLIP_DEFAULT, "max_images": R2V_MAX_IMAGES}

# 纯 widget 节点：前端 widgets_values 顺序 → API input 名（无连接输入时按此映射）
WIDGET_MAP = {
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "LoadImage": ["image", "upload"],
    "VAELoader": ["vae_name"],
    "KSamplerSelect": ["sampler_name"],
    "BasicScheduler": ["scheduler", "steps", "denoise"],
    "SaveVideo": ["filename_prefix", "format", "codec"],
    "PrimitiveFloat": ["value"],
    "ComfyMathExpression": ["expression"],
    "PrimitiveStringMultiline": ["text"],
    "RandomNoise": ["noise_seed", "mode"],
    "ResolutionSelector": ["aspect_ratio", "megapixels", "multiple"],
    "CreateVideo": ["fps"],
    "MiniMaxH3ReferenceToVideo": ["format", "width", "height", "length", "ref_image_size"],
}

# ---------- 提示词（来自 MiniMax_H3_视频脚本.md，规则化） ----------

PROMPT_T0_TITLE = """integrated_multimodal_description: [Shot 1] Cinematic 3D motion-graphics style, a deep space background with a dark-blue nebula and faint stars. Tiny glowing orange particles drift in from the edges and converge into the center, forming a single line of bold white text: "MINIMAX H3". A warm orange rim light sweeps across the letterforms as the text locks into place, then a smaller letterspaced grey line appears below it: "OPEN SOURCE". The camera pushes in with small amplitude at slow speed toward the text. A confident male narrator says in an off-screen voiceover: <d>[Chinese] MiniMax H3 开源了。文字、图片、视频、声音，一次全理解，直接生成带原生立体声的视频。</d> [Shot 2] At 00:06.500, the shot cuts to an extreme close-up of the glowing letter edges as the scene slowly fades to black.

overall_soundscape: Deep electronic drone fading in with a soft rising shimmer, then silence as the screen fades to black.

non_diegetic_music: Epic cinematic trailer music, a single low piano note with a swelling string chord and a crisp impact hit as the title locks in, then continuing quietly beneath the narrator's voice and fading out."""

PROMPT_T1_OPENING = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic vlog style, a medium close-up of the young Chinese man shown in <Picture 1>, preserving his short black hair, thin round glasses, white crew-neck T-shirt, and the softly blurred indoor background. The camera holds a static shot. He sits facing the camera with a calm, slightly tired expression, then his eyes widen with sudden realization and he breaks into an exaggerated grin. He leans toward the camera, points at the lens, and speaks with an excited, slightly theatrical voice: <d>[Chinese] 以前，AI 视频是土豪的玩具。一条五秒，几十块。</d> He claps his hands together in a triumphant pose, gives a smug nod, and adds with a proud smirk: <d>[Chinese] 直到 MiniMax 把 H3 开源了。</d> He settles back with a satisfied grin while the camera pushes in with small amplitude at slow speed. Nothing flies across the frame at any point during the shot; no birds, insects, papers, particles, or objects pass in front of the camera, and the background remains completely static.

overall_soundscape: Quiet indoor room tone with a faint fan hum and soft fabric rustle as he moves.

non_diegetic_music: Bouncy comedic ukulele plucks at a moderate tempo with a light bass line, swelling as his expression changes, then settling into a playful loop."""

PROMPT_T2_SCIFI = """integrated_multimodal_description: [Shot 1] Cinematic, medium wide shot, the camera pushes in slowly. In the cavernous, dimly lit bridge of a starship, sleek metallic consoles with glowing amber displays flank a massive curved observation window. A female captain in her late 40s with short silver-streaked black hair stands in the center midground with her back to the camera, silhouetted against cool starlight. Outside the window, a massive armada of jagged dark-grey dreadnoughts hovers in tight formation against a deep purple nebula. The fleet's rear thrusters begin to glow with escalating bright blue light. A calm male narrator says in an off-screen voiceover: <d>[Chinese] 这段科幻镜头，画面和声音是模型一次生成的——H3 能同时理解文字、图像、视频和音频，端到端输出带原生立体声的视频。</d> [Shot 2] At 00:04.500, the camera cuts to a close-up of the captain's face and shakes strongly. The blue-white light reflects in her dark eyes as a blinding flash floods the window. The bridge jolts violently and she staggers slightly forward, bracing herself. As the light fades, she slowly closes her eyes in the newly emptied space.

overall_soundscape: A low resonant hum of the ship's life support serves as the baseline, soon drowned by an escalating high-pitched electronic whine as the fleet charges hyperdrives. A massive bass-heavy boom and sharp crackle erupts at the flash, followed by metallic creaking and deep thuds, then cuts abruptly back to a hollow echoing room tone.

non_diegetic_music: Cinematic space-opera orchestral score, slow tempo, a solitary mournful French horn melody over deep sustained string dissonances that build rapidly to a massive peak, then snap into silence right after the jump."""

PROMPT_T3_3D = """integrated_multimodal_description: [Shot 1] Pixar-inspired 3D cartoon rendering, C4D + Octane look, stylized Q-version proportions, warm SSS skin, designed-with-detail hair. A small round robot with big expressive eyes rolls along a bright pastel hallway, its antenna bobbing with each movement. The camera tracks beside it at a medium distance. The robot stops at a doorway, tilts its head, and a paper plane flies past. The robot leaps with exaggerated squash-and-stretch, catches the plane mid-air, and lands with a soft bounce, beaming with pride. A warm male narrator says in an off-screen voiceover: <d>[Chinese] 3D 动画，角色一致、表演有弹性——H3 的指令遵循和运动控制都很稳。</d> [Shot 2] At 00:06.000, the shot cuts to a close-up of the robot's face as it holds the paper plane up, eyes sparkling, then gives one confident nod.

overall_soundscape: Soft mechanical whirrs, gentle rubbery footsteps, a light whoosh of the paper plane, and a soft landing thud.

non_diegetic_music: Playful orchestral pizzicato at a cheerful tempo with light percussion, ending on a short resolved chord."""

PROMPT_T4_PAPER = """integrated_multimodal_description: [Shot 1] Premium editorial paper-collage stop-motion style, a clean flat bold color field background in deep teal with fine paper grain. A black-and-white halftone photographic cut-out of a small lighthouse and a paper sun assemble piece by piece with visible hand-torn edges, warm cream keylines, and soft paper shadows. Each paper piece slides or pops in, lightly bounces, presses flat, and locks into place. A gentle male narrator says in an off-screen voiceover: <d>[Chinese] 连纸拼贴这种手作质感都能做——H3 不只是写实风，风格控制同样能打。</d> The final composition holds still with a subtle parallax shift between the layered paper planes.

overall_soundscape: Tactile collage sound effects only: soft paper slides, pop-ins, light press-flat taps, and tiny paper snaps synchronized to the paper motion. No music, no speech.

non_diegetic_music: N/A"""

PROMPT_T5_CONFIG = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic vlog style, a medium close-up of the young Chinese man shown in <Picture 1>, preserving his short black hair, thin round glasses, white crew-neck T-shirt, and the blurred indoor background. The camera holds a static shot. He sits up straighter, adjusts his collar with a mock-serious expression, and speaks clearly and audibly, his Chinese voice the most prominent sound in the video: <d>[Chinese] 我的配置其实很普通：U7 265K 处理器，48G 内存，RTX 5070 Ti 16G 显存。</d> He turns slightly to one side as if presenting an invisible monitor, gestures with both hands like presenting specifications, then faces the camera and continues in the same clear voice: <d>[Chinese] 跑 MiniMax H3 基本够用——无非就是慢一点。</d> A small grin escapes before he returns to the serious pose. His hands keep a consistent natural skin tone and shape in every frame; there is no color shift, discoloration, or distortion on his hands or fingers at any point. The air and background remain completely clean and static throughout the shot: no confetti, no petals, no ribbons, no glitter, no floating particles, no ink strokes, no sparks, and no light effects or decorations of any kind appear around him or anywhere in the frame.

overall_soundscape: Quiet indoor room tone, a faint chair creak, and light fabric rustle, all kept very low so the man's spoken Chinese lines are clearly audible.

non_diegetic_music: Minimal electronic pulse at a slow tempo with a soft beat, comedic and confident, kept very low under the man's voice and fading out at the end."""

PROMPT_T6_HUMOR = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic vlog style, a medium close-up of the young Chinese man shown in <Picture 1>, preserving his short black hair, thin round glasses, white crew-neck T-shirt, and the blurred indoor background. The camera holds a static shot. He pantomimes pulling an empty dark brown leather wallet from a pocket with a tragic, exaggerated frown and says mournfully: <d>[Chinese] 以前，一个片段顶我一周奶茶钱。</d> A lightbulb moment hits: he slaps his forehead, points at a power outlet in the background, and exclaims with glee: <d>[Chinese] 现在，电费只是一杯奶茶的零头。</d> He does a small victory dance with clenched fists, winks at the camera with a cheeky grin, and mouths a final triumphant laugh. The dark brown leather wallet keeps the exact same color, shape, and texture in every frame throughout the entire shot; its color never changes, fades, or shifts. The air and background remain completely clean and static throughout the shot: no confetti, no petals, no ribbons, no glitter, no floating particles, no ink strokes, no sparks, and no light effects or decorations of any kind appear around him or anywhere in the frame.

overall_soundscape: Quiet indoor room tone, faint fabric rustle, and a light slapping sound on the forehead.

non_diegetic_music: Quirky comedy percussion at a moderate tempo with a bass drop on the victory dance, ending with a playful sting."""

PROMPT_T7_CTA = """integrated_multimodal_description: [Shot 1] 2D-animated motion-graphics style, a dark navy background with a subtle grid. Glowing orange particles swirl in from the corners and converge into a clean circular emblem in the center: a smooth ring with a small white play-triangle icon inside. The emblem pulses softly with a warm orange glow. A cheerful male narrator says in an off-screen voiceover, clearly and audibly: <d>[Chinese] 跟着辉哥学AI，关注我，下期手把手教你！</d> No letters, characters, numbers, seal script, symbols, or text of any kind appears anywhere in the scene. The camera holds still while the emblem and particles glow gently. [Shot 2] At 00:05.000, the shot cuts to a wider view of the emblem floating in a starfield, still completely free of text, as the scene slowly fades to black.

overall_soundscape: Soft electronic shimmer and a gentle low whoosh, kept low under the narrator's voice, then silence as the scene fades.

non_diegetic_music: Bright synth chime at a slow tempo with a warm pad, kept low under the narrator's voice, ending in a clean fade-out."""


# ---------- 任务定义 ----------

TASKS = [
    {
        "id": "T0_title", "mode": "t2v", "prompt": PROMPT_T0_TITLE,
        "duration": 10, "prefix": "video/H3_00_title", "image": None, "mp": 1.0,
    },
    {
        "id": "T2_scifi", "mode": "t2v", "prompt": PROMPT_T2_SCIFI,
        "duration": 10, "prefix": "video/H3_02_scifi", "image": None, "mp": 1.0,
    },
    {
        "id": "T3_3d", "mode": "t2v", "prompt": PROMPT_T3_3D,
        "duration": 10, "prefix": "video/H3_03_3d", "image": None, "mp": 1.0,
    },
    {
        "id": "T4_paper", "mode": "t2v", "prompt": PROMPT_T4_PAPER,
        "duration": 10, "prefix": "video/H3_04_paper", "image": None, "mp": 1.0,
    },
    {
        "id": "T7_cta", "mode": "t2v", "prompt": PROMPT_T7_CTA,
        "duration": 8, "prefix": "video/H3_07_cta", "image": None, "mp": 1.0,
    },
    {
        "id": "T1_opening", "mode": "i2v", "prompt": PROMPT_T1_OPENING,
        "duration": 10, "prefix": "video/H3_01_opening", "image": "3号_1s.png", "mp": 1.0,
    },
    {
        "id": "T5_config", "mode": "i2v", "prompt": PROMPT_T5_CONFIG,
        "duration": 10, "prefix": "video/H3_05_config", "image": "3号_15s.png", "mp": 1.0,
    },
    {
        "id": "T6_humor", "mode": "i2v", "prompt": PROMPT_T6_HUMOR,
        "duration": 10, "prefix": "video/H3_06_humor", "image": "3号_40s.png", "mp": 1.0,
    },
]

# 问题片段重跑：3 条出镜 + 结尾 CTA，768p 高分辨率 + 修复后的提示词
RETRY_TASKS = [
    {
        "id": "T1_opening_r2", "mode": "i2v", "prompt": PROMPT_T1_OPENING,
        "duration": 10, "prefix": "video/H3_01_opening", "image": "3号_1s.png", "mp": 1.0,
    },
    {
        "id": "T5_config_r2", "mode": "i2v", "prompt": PROMPT_T5_CONFIG,
        "duration": 10, "prefix": "video/H3_05_config", "image": "3号_15s.png", "mp": 1.0,
    },
    {
        "id": "T6_humor_r2", "mode": "i2v", "prompt": PROMPT_T6_HUMOR,
        "duration": 10, "prefix": "video/H3_06_humor", "image": "3号_40s.png", "mp": 1.0,
    },
    {
        "id": "T7_cta_r2", "mode": "t2v", "prompt": PROMPT_T7_CTA,
        "duration": 8, "prefix": "video/H3_07_cta", "image": None, "mp": 1.0,
    },
]


def convert_t2v(task):
    """前端工作流 JSON → API 图。"""
    wf = json.load(open(T2V_WF))
    link_map = {}
    for link in wf.get("links", []):
        link_map[link[0]] = (str(link[1]), link[2])
    api = {}
    for n in wf.get("nodes", []):
        ntype = n.get("type")
        if ntype == "MarkdownNote":
            continue
        wv = list(n.get("widgets_values") or [])
        wi = 0
        inputs = {}
        for inp in n.get("inputs", []):
            name = inp.get("name")
            if inp.get("link") is not None:
                src_id, src_slot = link_map[inp["link"]]
                inputs[name] = [src_id, src_slot]
            elif inp.get("widget"):
                if wi < len(wv):
                    inputs[name] = wv[wi]
                    wi += 1
        api[str(n["id"])] = {"class_type": ntype, "inputs": inputs}
    # 覆盖参数
    for node in api.values():
        ct = node["class_type"]
        if ct == "MiniMaxH3ImageToVideo":
            node["inputs"]["prompt"] = task["prompt"]
        elif ct == "ResolutionSelector":
            node["inputs"]["aspect_ratio"] = "9:16 (Portrait Widescreen)"
            node["inputs"]["megapixels"] = task.get("mp", 0.4)
            node["inputs"]["multiple"] = 32
        elif ct == "PrimitiveFloat":
            node["inputs"]["value"] = float(task["duration"])
        elif ct == "RandomNoise":
            node["inputs"]["noise_seed"] = task["seed"]
        elif ct == "SaveVideo":
            node["inputs"]["filename_prefix"] = task["prefix"]
    return api


def build_i2v(task):
    """队列快照模板 → 清理增强器 → API 图。"""
    q = json.load(open(I2V_TEMPLATE))
    prompt = q["queue_running"][0][2]
    drop = {"105:121", "105:122", "105:123", "105:124"}
    prompt = {k: v for k, v in prompt.items() if k not in drop}
    for node in prompt.values():
        node["inputs"] = {
            k: v for k, v in node["inputs"].items()
            if not (isinstance(v, list) and v and str(v[0]) in drop)
        }
    # 覆盖参数
    for nid, node in prompt.items():
        ct = node["class_type"]
        if ct == "MiniMaxH3ImageToVideo":
            node["inputs"]["prompt"] = task["prompt"]
        elif ct == "LoadImage":
            node["inputs"]["image"] = task["image"]
        elif ct == "ResolutionSelector":
            node["inputs"]["aspect_ratio"] = "9:16 (Portrait Widescreen)"
            node["inputs"]["megapixels"] = task.get("mp", 0.4)
            node["inputs"]["multiple"] = 32
        elif ct == "PrimitiveFloat":
            node["inputs"]["value"] = float(task["duration"])
        elif ct == "RandomNoise":
            node["inputs"]["noise_seed"] = task["seed"]
        elif ct == "SaveVideo":
            node["inputs"]["filename_prefix"] = task["prefix"]
        elif ct == "BasicScheduler":
            node["inputs"]["steps"] = int(task.get("steps") or 4)
    return prompt


def build_r2v(task):
    """Ref2VA 工作流模板 → API 图。

    覆盖：
    - UNET：models.r2v.unet（官方 Ref2VA 权重；提交端检测缺失会回退并提示）
    - CLIP：models.r2v.clip（默认无审查模型，用户要求保留）
    - 参考图列表 task['images']（最多 8 张，依次填 ref_image_0..7，官方上限 9）
    - 提示词、时长、分辨率、输出前缀
    - 步数由 task['steps'] 控制（默认：成片档 20 / 快速档 4）
    - 步数 ≤8 时插入加速：UNET → TurboLoRA → SageAttention → Guider/Scheduler
      （turbo LoRA 只适配低步数，步数高时不插，避免劣化音频）
    """
    cfg = _r2v_cfg()
    unet_name = str(task.get("r2v_unet") or cfg["unet"])
    clip_name = str(task.get("r2v_clip") or cfg["clip"])
    max_images = min(int(cfg["max_images"]), 9)
    quality = str(task.get("quality") or "preview")
    is_final = quality == "final"
    steps = int(task.get("steps") or (R2V_FINAL_STEPS if is_final else R2V_STEPS))
    use_turbo = steps <= 8
    wf = json.load(open(R2V_TEMPLATE))
    link_map = {}
    for link in wf.get("links", []):
        link_map[link[0]] = (str(link[1]), link[2])
    api = {}
    for n in wf.get("nodes", []):
        ntype = n.get("type")
        if ntype == "MarkdownNote":
            continue
        wv = list(n.get("widgets_values") or [])
        wi = 0
        inputs = {}
        for inp in n.get("inputs", []):
            name = inp.get("name")
            if inp.get("link") is not None:
                src_id, src_slot = link_map[inp["link"]]
                inputs[name] = [src_id, src_slot]
            elif inp.get("widget"):
                if wi < len(wv):
                    inputs[name] = wv[wi]
                    wi += 1
        # 按 WIDGET_MAP 顺序补齐缺失的 widget 参数（连接优先，未连接时用 widget 值）
        if ntype in WIDGET_MAP:
            names = WIDGET_MAP[ntype]
            for i, name in enumerate(names):
                if i < len(wv) and name not in inputs:
                    inputs[name] = wv[i]
        api[str(n["id"])] = {"class_type": ntype, "inputs": inputs}

    # 参考图：task['images'] + 本段分镜图 story_image（最多 4 张，动态补节点）
    load_ids = [nid for nid, node in api.items() if node["class_type"] == "LoadImage"]
    images = list(task.get("images") or [])
    if task.get("story_image") and task["story_image"] not in images:
        images.append(task["story_image"])
    images = images[:max_images]
    # 参考图多于现有 LoadImage 节点时，动态补充（ref_image_2..7 等）
    for slot in range(len(load_ids), min(len(images), max_images)):
        new_id = f"r2v_img_{slot}"
        api[new_id] = {
            "class_type": "LoadImage",
            "inputs": {"image": images[slot], "upload": "image"},
        }
        load_ids.append(new_id)
    for slot, img in enumerate(images[:max_images]):
        if slot < len(load_ids):
            api[load_ids[slot]]["inputs"]["image"] = img

    # 覆盖参数（load_ids 已就绪）
    unet_id = None
    for nid, node in api.items():
        ct = node["class_type"]
        if ct == "MiniMaxH3ReferenceToVideo":
            node["inputs"]["prompt"] = task["prompt"]
            for slot, lid in enumerate(load_ids[:max_images]):
                key = f"ref_images.ref_image_{slot}"
                node["inputs"][key] = [lid, 0]
            # 未提供的参考图：断开连接（多余 LoadImage 会被 ComfyUI 忽略）
            for slot in range(len(images), max_images):
                key = f"ref_images.ref_image_{slot}"
                node["inputs"][key] = None
        elif ct == "CLIPLoader":
            node["inputs"]["clip_name"] = clip_name
        elif ct == "UNETLoader":
            node["inputs"]["unet_name"] = unet_name
            unet_id = nid
        elif ct == "ResolutionSelector":
            node["inputs"]["aspect_ratio"] = "9:16 (Portrait Widescreen)"
            node["inputs"]["megapixels"] = task.get("mp", 0.4)
            node["inputs"]["multiple"] = 32
        elif ct == "PrimitiveFloat":
            node["inputs"]["value"] = float(task["duration"])
        elif ct == "RandomNoise":
            node["inputs"]["noise_seed"] = task.get("seed", random.randrange(10 ** 15))
        elif ct == "SaveVideo":
            node["inputs"]["filename_prefix"] = task["prefix"]
        elif ct == "BasicScheduler":
            node["inputs"]["steps"] = steps

    # 参考视频：task['ref_video'] → 动态加 LoadVideo 节点并接 ref_videos.ref_video_0
    ref_video = task.get("ref_video")
    if ref_video:
        vid_id = "r2v_video_0"
        api[vid_id] = {
            "class_type": "LoadVideo",
            "inputs": {"video": ref_video, "upload": "video"},
        }
        for node in api.values():
            if node["class_type"] == "MiniMaxH3ReferenceToVideo":
                node["inputs"]["ref_videos.ref_video_0"] = [vid_id, 0]
                node["inputs"]["ref_video_audios.ref_video_audio_0"] = None

    # 低步数（≤8）插入加速节点：UNET → TurboLoRA(新) → SageAttention(新) → Guider/Scheduler
    # 高步数不插加速（turbo LoRA 只适配低步数，高步数会劣化音频），保持 UNET → Guider/Scheduler 直连
    if unet_id and use_turbo:
        lora_id = f"r2v_turbo_{unet_id}"
        attn_id = f"r2v_sage_{unet_id}"
        api[lora_id] = {
            "class_type": "MiniMaxH3TurboLoRA",
            "inputs": {
                "lora_name": R2V_TURBO_LORA,
                "strength": R2V_LORA_STRENGTH,
                "low_vram": False,
                "model": [unet_id, 0],
            },
        }
        api[attn_id] = {
            "class_type": "MiniMaxH3MemoryEfficientSageAttentionPatch",
            "inputs": {"model": [lora_id, 0]},
        }
        for node in api.values():
            ct = node["class_type"]
            if ct in ("BasicGuider", "BasicScheduler"):
                if node["inputs"].get("model") == [unet_id, 0]:
                    node["inputs"]["model"] = [attn_id, 0]

    return api


def main():
    os.makedirs(TASKS_DIR, exist_ok=True)
    rng = random.Random(20260812)
    manifest = []
    tasks = TASKS if len(sys.argv) == 1 or sys.argv[1] != "--retry" else RETRY_TASKS
    for task in tasks:
        task["seed"] = rng.randrange(10**15)
        graph = convert_t2v(task) if task["mode"] == "t2v" else build_i2v(task)
        out = os.path.join(TASKS_DIR, f"{task['id']}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"task": task, "graph": graph}, f, ensure_ascii=False, indent=1)
        manifest.append(
            f"{task['id']} | {task['mode']} | {task['duration']}s | seed={task['seed']} | nodes={len(graph)}"
        )
        print(f"built: {task['id']} -> {out} ({len(graph)} nodes)")
    print("\n".join(manifest))


if __name__ == "__main__":
    main()
