# 场景系统 + 游戏化互动 — 完整设计方案

> 基于 `docs/branch-scenes-game.md` 分支规划，深入设计场景系统的全部细节。
> **状态：方案阶段，待讨论确认后编码。**

---

## 一、场景定义

### 1.1 四个场景

| ID | 名称 | 类型 | 历史依据 |
|----|------|------|---------|
| `shuwu` | 菊香书屋 | 室内·办公 | 中南海丰泽园内毛泽东书房，办公/读书/会客之处 |
| `keting` | 丰泽园客厅 | 室内·居家 | 丰泽园客厅，藤椅、搪瓷杯、旧报纸，更放松 |
| `xiaolu` | 菊香书屋外的小路上 | 室外·办公地周围 | 中南海内散步道，林荫小路，办公间隙散步 |
| `shuxia` | 丰泽园外的树下 | 室外·家周围 | 丰泽园外庭院/树下，菜地、田野意象，更闲适 |

### 1.2 场景氛围文本

```python
SCENES = {
    "shuwu": {
        "id": "shuwu",
        "name": "菊香书屋",
        "type": "indoor_work",
        "atmosphere": (
            "你和主席在菊香书屋——他的书房兼办公室。"
            "满墙的书架堆着线装书和马列著作，大书桌上文件摞成小山，"
            "红铅笔压在《人民日报》上，搪瓷杯冒着热气。"
            "墙上挂着大地图，红机电话偶尔响起。"
            "空气中弥漫着淡淡的烟草味和书香。"
        ),
        "actions": [
            "批了两份文件，搁下红铅笔",
            "从书架上抽出一本线装书翻了两页",
            "拿起红铅笔在报告上画了个圈",
            "把文件推到一边，腾出桌面",
            "摘下眼镜放桌上，揉了揉鼻梁",
            "拿起《人民日报》扫了一眼标题",
            "往搪瓷杯里续了热水",
            "靠在椅背上，目光扫过满墙的书架",
        ],
        "background_prompt": (
            "中南海菊香书屋内部，毛泽东的书房兼办公室，满墙书架堆满线装书和马列著作，"
            "大书桌上摆着文件和《人民日报》，一盏绿色台灯亮着，墙上挂着中国地图，"
            "红机电话在桌角，搪瓷杯冒着热气，窗外阳光透过纱帘洒进来。"
            "暖色调，怀旧氛围，电影级光影，9:16竖屏。"
        ),
    },
    "keting": {
        "id": "keting",
        "name": "丰泽园客厅",
        "type": "indoor_home",
        "atmosphere": (
            "你和主席在丰泽园的客厅里。藤椅旁边的茶几上摆着搪瓷杯，"
            "旧报纸叠在一边，烟灰缸里有几个烟蒂。"
            "窗外能看到院子里的树影，屋里安静而自在。"
            "主席靠在藤椅上，姿态放松，像在家里和老朋友聊天。"
        ),
        "actions": [
            "往藤椅里靠了靠，换了个舒服的姿势",
            "端起搪瓷杯喝了口浓茶",
            "从茶几上拿起旧报纸翻了翻",
            "弹了弹烟灰，烟灰缸里又多了个烟蒂",
            "拿起蒲扇轻轻扇了两下",
            "指了指窗外院子里的树",
            "把脚边的暖水瓶挪了挪",
            "拿起一个橘子慢慢剥着",
        ],
        "background_prompt": (
            "丰泽园客厅内部，中式老式客厅，藤椅、茶几上摆着搪瓷杯和旧报纸，"
            "烟灰缸、暖水瓶、蒲扇，窗外可见庭院树影，午后的阳光斜照进来，"
            "宁静的居家氛围，暖色调，怀旧，电影级光影，9:16竖屏。"
        ),
    },
    "xiaolu": {
        "id": "xiaolu",
        "name": "菊香书屋外的小路上",
        "type": "outdoor_work",
        "atmosphere": (
            "你和主席走出菊香书屋，走在庭院的小路上。"
            "两旁是修剪整齐的冬青，几棵老槐树投下斑驳的树影。"
            "远处偶尔传来中南海里工作人员的脚步声。"
            "主席背着手慢慢走着，偶尔停下来看看路边的花草。"
            "微风拂过，空气里有草木的清香。"
        ),
        "actions": [
            "背着手慢慢走着，脚步不急不缓",
            "停下来看了看路边的冬青",
            "抬头望了望树梢上的鸟",
            "深吸一口新鲜空气，舒展了一下肩膀",
            "在路边的一块石头上坐下来歇了歇",
            "指着路边一丛花说了句什么",
            "弯腰捡起一片落叶看了看",
            "眯起眼看了看远处的天空",
        ],
        "background_prompt": (
            "中南海庭院小路，两旁冬青和槐树，斑驳树影洒在石板路上，"
            "远处隐约可见红墙建筑，天空湛蓝有白云，几只鸟飞过树梢，"
            "宁静的午后散步氛围，暖色调，电影级光影，9:16竖屏。"
        ),
    },
    "shuxia": {
        "id": "shuxia",
        "name": "丰泽园外的树下",
        "type": "outdoor_home",
        "atmosphere": (
            "你和主席坐在丰泽园外的大树下。树冠如盖，挡住了午后的太阳，"
            "只漏下星星点点的光斑。远处有菜地的影子，"
            "池塘边的芦苇在微风里轻轻摇着。"
            "偶尔有鸟叫和蝉鸣。主席坐在树荫里，"
            "手里可能夹着一支烟，也可能什么都没拿，就这么静静待着。"
            "空气中带着泥土和青草的气息，安静得能听见风吹树叶的声音。"
        ),
        "actions": [
            "靠在树干上，望着远处的田野",
            "用树枝在地上划拉着什么",
            "指了指池塘那边飞过的水鸟",
            "眯起眼享受树荫下的凉风",
            "拔了根草叼在嘴里",
            "拍了一下腿上的蚊子，笑了起来",
            "抬头看了看树冠里透下的光斑",
            "指着菜地说那边种的什么菜",
        ],
        "background_prompt": (
            "丰泽园外大树下，树冠如盖投下大片阴凉，远处可见菜地和池塘，"
            "芦苇在微风中摇曳，几只鸟飞过天空，树荫下光影斑驳，"
            "宁静的田园氛围，暖色调，电影级光影，9:16竖屏。"
        ),
    },
}
```

### 1.3 场景映射关系

| 原分支名称 | 新名称 | 说明 |
|-----------|--------|------|
| 🏢 办公室 (office) | 🏢 菊香书屋 (shuwu) | 更具体，有历史真实感 |
| 🛋️ 客厅 (living) | 🛋️ 丰泽园客厅 (keting) | 同上 |
| 🌳 办公地外 (garden) | 🌳 菊香书屋外的小路上 (xiaolu) | 动态场景——散步 |
| 🏡 家周围 (home_out) | 🏡 丰泽园外的树下 (shuxia) | 静态场景——闲坐 |

---

## 二、动作库设计

### 2.1 动作分类体系

```
动作总库
├── 通用动作 (COMMON_ACTIONS)        # 不依赖场景，任何场景都可触发
├── 场景动作 (SCENE_ACTIONS)         # 每个场景专属，与场景事物强绑定
├── 疲劳动作 (FATIGUE_ACTIONS)       # 黄/红疲劳时触发，按疲劳度分层
│   ├── 室内疲劳动作                  # 室内场景的疲劳动作
│   └── 室外疲劳动作                  # 室外场景的疲劳动作
└── 离开动作 (EXIT_ACTIONS)          # 主席主动结束对话时，按场景分层
    ├── 室内离开动作
    └── 室外离开动作
```

### 2.2 通用动作（COMMON_ACTIONS）

不依赖场景事物，任何场景都可安全使用：

```python
COMMON_ACTIONS = [
    # 烟/茶类（通用）
    "[主席抽了口烟，等你开口]",
    "[老人家端起搪瓷杯，喝了口浓茶]",
    "[主席掐灭烟头，若有所思地看着你]",
    "[主席往搪瓷杯里续了热水，杯口冒着白气]",
    # 神态类（通用）
    "[老人家微笑着，手指轻轻敲着]",
    "[主席点点头，示意你继续说]",
    "[老人家沉默了片刻，目光深远]",
    "[主席笑了起来，笑得很爽朗]",
    # 身体动作类（通用）
    "[老人家摘下眼镜，用衣角擦了擦]",
    "[主席轻轻叹了口气]",
]
```

### 2.3 场景动作 vs 通用动作的选择逻辑

```python
def pick_action(scene_id, fatigue_level):
    """选择动作：场景动作 70% 概率，通用动作 30% 概率"""
    if random.random() < 0.7:
        # 场景专属动作
        pool = SCENES[scene_id]["actions"]
    else:
        # 通用动作
        pool = COMMON_ACTIONS

    # 疲劳时混入疲劳动作
    if fatigue_level != "green" and random.random() < 0.4:
        pool = FATIGUE_ACTIONS_BY_SCENE.get(scene_id, FATIGUE_ACTIONS_COMMON)

    return random.choice(pool)
```

### 2.4 现有 IDLE_ACTIONS 的迁移

现有 12 个 IDLE_ACTIONS 需要按场景归类：

| 现有动作 | 新归属 |
|---------|--------|
| 抽了口烟、等你开口 | → COMMON（烟类） |
| 端起搪瓷杯喝茶 | → COMMON（茶类） |
| 靠在藤椅上、望向窗外 | → `keting`（藤椅是客厅专属） |
| 提起铅笔批文件 | → `shuwu`（书桌/文件） |
| 站起来看大地图 | → `shuwu`（地图在书房） |
| 摘下眼镜擦了擦 | → COMMON（神态类） |
| 掐灭烟头若有所思 | → COMMON（烟类） |
| 翻开《资治通鉴》 | → `shuwu`（书架在书房） |
| 站起身踱步 | → `shuwu`（室内踱步） |
| 微笑着手指敲桌面 | → COMMON（神态类） |
| 续热水、杯口冒白气 | → COMMON（茶类） |
| 红铅笔在人民日报上画圈 | → `shuwu`（书桌） |

---

## 三、场景切换机制

### 3.1 切换动机分类

```
场景切换
├── 用户主动触发
│   ├── 聊天中自然表达："主席我陪您出去走走？"
│   │   → LLM 识别意图（在 think 阶段注入场景切换检测 prompt）
│   │   → 后端返回 scene_change_suggestion
│   │   → 前端弹出切换确认/自动切换
│   └── 点击场景标签栏
│       → 直接切换，前端发送 POST /api/scene/set
│
└── 主席主动提议（被动触发）
    ├── 触发条件：连续 3 次冷场动作（约 90 秒无用户输入）
    │   → 主席提议切换："小鬼，坐了这么久，陪我到外面走走？"
    │   → 前端弹窗"主席邀请你出去走走" / 自动切换
    └── 触发条件：用户在某个室内场景对话超过 15 轮
        → 主席提议："在屋里坐久了，出去透透气吧。"
```

### 3.2 切换检测（LLM 识别）

在 `think.jinja2` 中追加场景切换检测段：

```jinja2
## 场景切换检测
当前场景：{{ scene_name }}（{{ scene_type }}）

如果对方表达了想换个环境的意思（比如"出去走走""到外面坐坐""进屋聊吧"），
在你的分析中标注：`[场景切换意图: 目标场景ID]`。

可能的切换目标：
- 想出去 → {{ outdoor_scene_id }}（如果当前是室内）
- 想进屋 → {{ indoor_scene_id }}（如果当前是室外）
- 想在附近散步 → xiaolu
- 想坐下休息 → shuxia 或 keting
```

后端在 think 结果中解析 `[场景切换意图: xxx]`，如果存在则返回给前端。

### 3.3 切换动画设计

#### 方案：幻灯片背景切换 + 中间过渡场景

每个切换不是简单的 fade，而是在两个场景之间插入一个"过渡场景"，模拟真实的空间移动：

```
室内场景 A  ──→  过渡场景（楼道/门廊/小路）  ──→  室外场景 B
          fadeOut          slide + 文字           fadeIn
```

```
┌──────────────────────────────────────────────────┐
│                                                    │
│     [背景图片：楼道/门廊/庭院的过渡场景]             │
│                                                    │
│    "你跟着主席慢慢走下楼梯，                          │
│     阳光从树叶间洒下来……"                           │
│                                                    │
│              ⏳ ...                                 │
│                                                    │
└──────────────────────────────────────────────────┘
```

**动画规格：**
- 总时长：2.5 ~ 3.5 秒（含过渡场景）
- 旧场景 fadeOut：0.3s
- 过渡场景 slideIn + 文字逐字显示：1.5~2s
- 新场景预加载 + fadeIn：0.5~0.8s
- 过渡背景图为预生成的过渡场景图片
- 过渡文字由后端生成（`POST /api/scene/transition`）
- **同类型场景切换**（室内↔室内 或 室外↔室外）：直接切换背景，无过渡场景，仅文字提示

**过渡文字对照表（含过渡场景背景）：**

| 切换方向 | 过渡场景 | 过渡文字示例 | 过渡背景提示词 |
|---------|---------|------------|-------------|
| shuwu → xiaolu | 菊香书屋门廊/楼道 | "主席放下手里的文件，站起身说：'走，陪我出去走走。'你跟着他走出菊香书屋，穿过门廊……" | 中南海菊香书屋门廊，青砖墙、老式木门、台阶通向庭院，阳光从门外洒进来 |
| xiaolu → shuwu | 菊香书屋门廊/楼道 | "走了一圈，主席在一棵树下停下来看了看，转身往回走。你跟着他穿过门廊，回到菊香书屋……" | 同上，从庭院方向看菊香书屋门口 |
| keting → shuxia | 丰泽园门廊/庭院入口 | "主席从藤椅上站起来，拿起蒲扇：'屋里闷，到树下坐坐。'你们走出丰泽园客厅，穿过小院子……" | 丰泽园客厅门口到庭院，门廊、青砖地、远处的大树 |
| shuxia → keting | 丰泽园门廊/庭院入口 | "太阳偏西了，主席拍拍裤腿站起来：'天晚了，进屋吧。'你们穿过院子，走回丰泽园客厅……" | 同上，傍晚光线从庭院看回客厅门口 |
| shuwu → keting | 走廊/过道 | "主席批完最后一份文件：'走，到客厅坐坐，这儿太闷。'你们从书房走过走廊，来到客厅……" | 中南海建筑的内部走廊，老式建筑、青砖墙、木地板 |
| xiaolu → shuxia | 庭院小径延伸 | "沿着小路走了一阵，主席指指前面的大树：'那儿凉快，过去坐会儿。'你们沿小路走向丰泽园外的大树……" | 中南海庭院小路延伸向大树，树冠远景、草地、远处的池塘 |
| 同类型切换 | 无 | 直接切换，文字提示"[你跟着主席来到了XX]" | — |

#### 过渡文字生成

新增接口 `POST /api/scene/transition`：
- 参数：`from_scene, to_scene`
- 返回：`{transition_text, transition_duration_ms}`
- 逻辑：查表返回预定义过渡文字 + 小幅度 LLM 润色（非必须，可缓存）

### 3.4 切换动画执行流程

```
[前端]
1. 触发切换（用户点击 / 主席提议 / LLM 检测到意图）
2. 调用 POST /api/scene/transition → 获取过渡文字
3. 创建过渡层 <div class="scene-transition">
4. 播放动画：
   t=0ms:    过渡层 fadeIn + 过渡文字逐字显示
   t=800ms:  新场景背景图预加载
   t=1500ms: 过渡层 fadeOut
   t=1800ms: 新场景聊天背景切换完成，主席发出一条与场景切换相关的消息
5. 移除过渡层
```

### 3.5 背景图生成提示词

> 用途：GPTIMAGE2 生成。共 9 张图（4 主场景 + 5 过渡场景）。
> 统一约束：1970 年代中国 · 中南海朴素庄重 · 无人物 · 暖色调怀旧 · 9:16 竖屏 · 适合文字叠加。

---

#### 主场景 1：菊香书屋（shuwu）

```
A quiet study room in Zhongnanhai, Beijing, 1970s China. Floor-to-ceiling wooden bookshelves
filled with thread-bound Chinese classics and Marxist-Leninist volumes. A large wooden desk
covered with documents, a copy of People's Daily, a red pencil on top. A classic green
banker's lamp glows warmly. On the wall hangs a large faded map of China. A red hotline
telephone sits at the desk corner. A white enamel cup with dark tea steams gently. Sunlight
filters through a gauze curtain over a wooden-framed window. Simple, dignified, scholarly
atmosphere — not luxurious. Warm amber tones, nostalgic, cinematic lighting, soft focus
background suitable for text overlay, 9:16 vertical composition, no people.
```

#### 主场景 2：丰泽园客厅（keting）

```
A traditional Chinese living room in Zhongnanhai, Beijing, 1970s. An old rattan armchair
with worn armrests, a low wooden tea table with a white enamel teacup and folded old
newspapers. A ceramic ashtray with a few cigarette butts. A red thermos flask on the floor
beside the chair. A worn palm-leaf fan leans against the chair. Through a wooden-framed
window, tree shadows from the courtyard are visible. Afternoon sunlight slants into the room.
Simple, lived-in, peaceful domestic atmosphere — the home of an elderly scholar, not a
palace. Warm amber tones, nostalgic, cinematic natural light, soft focus, 9:16 vertical, no people.
```

#### 主场景 3：菊香书屋外的小路上（xiaolu）

```
A stone-paved garden path in Zhongnanhai, Beijing, 1970s. Lined with neatly trimmed holly
bushes on both sides. Several old locust trees cast dappled shadows across the path. In the
far distance, faint red walls of traditional buildings are visible through the greenery.
Blue sky with soft white clouds, a few birds flying past the treetops. Peaceful afternoon
walking atmosphere. Simple, natural, serene — the quiet dignity of an old revolutionary's
daily stroll. Warm golden sunlight filtering through leaves, cinematic lighting, soft focus
background for text overlay, 9:16 vertical, no people.
```

#### 主场景 4：丰泽园外的树下（shuxia）

```
Under a large old tree outside Fengzeyuan in Zhongnanhai, Beijing, 1970s. The tree's canopy
spreads like a great umbrella, casting deep cool shade. Dappled spots of sunlight filter
through the leaves onto the patchy grass below. In the distance, a small vegetable field
and a pond with gentle reeds swaying in the breeze. A few water birds fly low over the pond.
Simple rustic countryside-within-compound atmosphere. Cicada buzz and bird calls implied
by the stillness. Warm late-afternoon light, golden and peaceful, cinematic, soft focus
suitable for text overlay, 9:16 vertical, no people.
```

---

#### 过渡场景 1：菊香书屋门廊（shuwu ↔ xiaolu）

```
The doorway and porch of Juxiang Study in Zhongnanhai, Beijing, 1970s. Grey brick walls
with subtle weathering, an old wooden double door with traditional Chinese lattice panels
slightly ajar. Stone steps leading down into a sunlit garden courtyard beyond. Warm sunlight
pours through the doorway from outside, creating a gentle glow on the old brick floor inside.
The threshold between the quiet scholarly interior and the bright natural garden. Simple,
aged, dignified — the humble entrance of a working study. Warm amber tones transitioning
from indoor shadow to outdoor light, cinematic, soft focus, 9:16 vertical, no people.
```

#### 过渡场景 2：走廊（shuwu ↔ keting）

```
An interior corridor in a traditional Zhongnanhai building, Beijing, 1970s. Grey brick walls
with decades of quiet patina. Dark wooden floorboards that creak with history. Soft light
from a frosted window at the far end of the corridor. Simple wooden door frames on either
side leading to different rooms. The corridor is narrow but not cramped — functional and
unadorned. The quiet passage between the study and the living quarters. Warm muted tones,
subdued lighting, nostalgic atmosphere, soft focus, 9:16 vertical, no people.
```

#### 过渡场景 3：丰泽园庭院入口（keting ↔ shuxia）

```
The courtyard entrance of Fengzeyuan in Zhongnanhai, Beijing, 1970s. A traditional doorway
with grey brick walls opens from the living quarters onto a small courtyard. Grey brick
paving underfoot, slightly uneven with age. Beyond the courtyard, a large old tree is
visible in the middle distance, its canopy promising shade. Midday sunlight illuminates
the scene evenly. The simple threshold between indoor comfort and outdoor ease. Warm natural
tones, peaceful transition atmosphere, cinematic lighting, soft focus, 9:16 vertical, no people.
```

#### 过渡场景 4：傍晚庭院入口（shuxia → keting · 专用）

```
The same courtyard entrance of Fengzeyuan in Zhongnanhai, but at dusk, 1970s. The golden
evening light falls low and horizontal, casting long shadows from the doorway across the
grey brick paving. The large tree in the distance is silhouetted against a warm orange sky.
The doorway glows with a soft interior light, inviting return. Quiet end-of-day atmosphere.
The gentle close of an afternoon outdoors. Warm golden-to-amber gradient tones, nostalgic,
cinematic evening light, soft focus, 9:16 vertical, no people.
```

#### 过渡场景 5：庭院小径延伸（xiaolu ↔ shuxia）

```
A garden path in Zhongnanhai, Beijing, 1970s, curving gently through the greenery. Stone
paving flanked by trimmed holly on one side and grassy ground on the other. The path leads
the eye toward a large old tree in the distance, its broad canopy visible against a blue
sky with soft clouds. A pond glimmers faintly beyond the tree. The path itself is the
subject — the quiet journey between two peaceful outdoor places. Warm afternoon sunlight,
natural green and earth tones, cinematic depth of field, soft focus, 9:16 vertical, no people.
```

---

#### 生图参数建议

| 参数 | 值 |
|------|-----|
| 比例 | 9:16（竖屏） |
| 风格 | 写实摄影 / 电影剧照风格 |
| 色调 | 暖色 / 琥珀色 / 怀旧胶片 |
| 虚化 | 轻微柔焦，留文字叠加空间 |
| 人物 | 无 |
| 格式 | PNG（后续压缩为 WebP 供 Web 使用） |

#### 文件命名约定

```
web/static/img/scenes/
├── bg-shuwu.webp          # 菊香书屋
├── bg-keting.webp         # 丰泽园客厅
├── bg-xiaolu.webp         # 菊香书屋外的小路上
├── bg-shuxia.webp         # 丰泽园外的树下
├── trans-doorway.webp     # 菊香书屋门廊
├── trans-corridor.webp    # 走廊
├── trans-courtyard.webp   # 丰泽园庭院入口
├── trans-dusk.webp        # 傍晚庭院入口
└── trans-path.webp        # 庭院小径延伸
```

---

## 四、场景事物系统

### 4.1 事物分类

每个场景维护一个事物清单，用于场景互动触发：

```python
SCENE_ENTITIES = {
    "shuwu": {
        "sky": [],  # 室内无天空
        "ground": [],
        "objects": {
            "bookshelf": {
                "name": "书架",
                "desc": "满墙的书架，线装书和马列著作塞得满满当当",
                "triggers": ["资治通鉴", "二十四史", "资本论", "读书"],
            },
            "desk": {
                "name": "书桌",
                "desc": "大书桌上文件摞成小山，红铅笔压着《人民日报》",
                "triggers": ["文件", "报告", "工作", "写文章"],
            },
            "map": {
                "name": "大地图",
                "desc": "墙上挂着大幅中国地图，边角已经泛黄",
                "triggers": ["地图", "中国", "地方", "省"],
            },
            "teacup": {
                "name": "搪瓷杯",
                "desc": "搪瓷杯里泡着浓茶，杯口冒着热气",
                "triggers": ["茶", "喝水", "渴"],
            },
            "phone": {
                "name": "红机电话",
                "desc": "桌角的红机电话，直通中央",
                "triggers": ["电话", "中央", "开会"],
            },
            "cigarette": {
                "name": "香烟",
                "desc": "烟灰缸里堆着几个烟蒂，屋里弥漫着淡淡烟味",
                "triggers": ["抽烟", "烟"],
            },
        },
        "other": ["窗外阳光", "纱帘", "台灯的光"],
    },
    "keting": {
        "sky": [],
        "ground": [],
        "objects": {
            "cane_chair": {
                "name": "藤椅",
                "desc": "老藤椅，扶手已经被磨得光滑发亮",
                "triggers": ["坐", "椅子", "休息"],
            },
            "teacup": {
                "name": "搪瓷杯",
                "desc": "茶几上的搪瓷杯，茶已经喝了大半",
                "triggers": ["茶", "喝水"],
            },
            "newspaper": {
                "name": "旧报纸",
                "desc": "茶几上叠着几份旧报纸",
                "triggers": ["报纸", "新闻", "人民日报"],
            },
            "ashtray": {
                "name": "烟灰缸",
                "desc": "烟灰缸里有几个烟蒂",
                "triggers": ["抽烟", "烟"],
            },
            "fan": {
                "name": "蒲扇",
                "desc": "夏天用的老蒲扇，边角有点破了",
                "triggers": ["热", "扇", "夏天"],
            },
            "window": {
                "name": "窗户",
                "desc": "窗外能看到院子里的树影",
                "triggers": ["窗外", "院子", "外面"],
            },
        },
        "other": ["午后的阳光", "暖水瓶", "橘子"],
    },
    "xiaolu": {
        "sky": {
            "sky": {"name": "天空", "desc": "湛蓝的天空，飘着几朵白云"},
            "sun": {"name": "阳光", "desc": "温暖的阳光透过树叶洒下来"},
            "wind": {"name": "微风", "desc": "微风拂过，带着草木的清香"},
            "bird": {"name": "飞鸟", "desc": "几只鸟飞过树梢"},
        },
        "ground": {
            "path": {"name": "小路", "desc": "石板小路，两旁是修剪整齐的冬青"},
            "stone": {"name": "石头", "desc": "路边有几块平整的石头可以歇脚"},
            "leaf": {"name": "落叶", "desc": "路面上散落着几片落叶"},
        },
        "objects": {
            "holly": {"name": "冬青", "desc": "修剪整齐的冬青丛"},
            "locust_tree": {
                "name": "老槐树",
                "desc": "几棵老槐树，树冠如盖，投下斑驳树影",
                "triggers": ["树", "槐树", "大树"],
            },
            "flower": {
                "name": "路边花",
                "desc": "路边开着不知名的小花",
                "triggers": ["花", "好看"],
            },
        },
        "other": ["中南海红墙", "远处的工作人员"],
    },
    "shuxia": {
        "sky": {
            "sky": {"name": "天空", "desc": "透过树叶能看到蓝天白云"},
            "sun": {"name": "光斑", "desc": "阳光从树叶间漏下星星点点的光斑"},
            "wind": {"name": "凉风", "desc": "树荫下凉风习习"},
            "bird": {"name": "鸟叫", "desc": "偶尔有鸟叫和蝉鸣"},
        },
        "ground": {
            "grass": {"name": "草地", "desc": "树下的草长得稀疏但柔软"},
            "earth": {"name": "泥土", "desc": "空气中带着泥土和青草的气息"},
        },
        "objects": {
            "tree": {
                "name": "大树",
                "desc": "树冠如盖的大树，挡住了午后的太阳",
                "triggers": ["树", "大树", "树荫"],
            },
            "pond": {
                "name": "池塘",
                "desc": "远处的池塘，芦苇在微风里轻轻摇着",
                "triggers": ["池塘", "水", "鱼"],
            },
            "field": {
                "name": "菜地",
                "desc": "远处有一片菜地，绿油油的",
                "triggers": ["菜地", "菜", "种地", "庄稼"],
            },
        },
        "other": ["蝉鸣", "水鸟", "蚊子"],
    },
}
```

### 4.2 事物在对话中的使用方式

1. **强话题触发**：用户说的话命中了 `triggers` 关键词 → 主席的回复中主动提及该事物
2. **弱话题触发**：主席回复中自然地提及场景事物，不与用户话题强关联
3. **被动触发**：冷场/长时间无输入时，主席从场景事物中随机选一个做切入点

---

## 五、主席与场景互动

### 5.1 互动分类

```
主席场景互动
├── 强话题互动（主动触发）
│   ├── 用户提到场景事物关键词
│   │   例：用户说"读书" → 主席："你看我这书架上的资治通鉴..."
│   ├── 主席发起话题（冷场/长对话后）
│   │   例：主席："小鬼，你看这棵老槐树，怕是比我年纪还大。"
│   │   触发条件：连续冷场 ≥ 2 次 且 当前处于室外场景
│   └── 主席讲场景故事
│       例：主席："这棵树底下，我当年和恩来同志..."
│       触发条件：红色疲劳 且 对话轮次 ≥ 20
│
├── 弱话题互动（被动融入）
│   ├── 回复中顺便提及场景事物
│   │   例："...就像这窗外的树，根扎得深才站得稳。"
│   └── 动作描写中包含场景事物
│       例："[主席指了指窗外池塘那边飞过的水鸟]"
│
└── 频次控制
    ├── 强话题互动：每 5 轮最多 1 次
    ├── 弱话题互动：每轮都可，但不强制
    └── 场景互动整体占比：不超过总回复的 40%
```

### 5.2 强话题触发逻辑

```
触发条件（满足任一）：
1. 用户消息中包含场景事物 triggers 关键词
2. 连续 3 次冷场动作 + 室外场景 → 主席主动找一个场景事物开启话题
3. 对话轮次 ≥ 15 + 疲劳度 yellow → 主席用场景事物做比喻讲道理

触发时行为：
→ think 阶段：在分析中标注 `[场景互动: 事物名称, 强度: 强]`
→ speak 阶段：
  a. 在回复开头/中间以场景事物为引子
  b. 格式："[主席指了指XX]，你看这XX..."
  c. 将事物与当前对话话题关联
```

### 5.3 弱话题触发逻辑

```
触发条件：
- 不回回触发，概率 30%~50%（随机）
- 不改变回复主题，仅作为修辞/比喻融入

触发时行为：
→ speak 阶段：
  a. 在回复中顺便提及场景事物
  b. 例："...就像这搪瓷杯里的茶，越泡越有味道。"
  c. 或在动作描写中带上场景事物：
     "[主席端起搪瓷杯喝了一口]"
```

### 5.4 频次控制算法

```python
class SceneInteractionController:
    def __init__(self):
        self.strong_trigger_count = 0    # 本轮对话强互动次数
        self.total_reply_count = 0       # 总回复次数
        self.last_strong_round = -5      # 上次强互动所在轮次

    def should_strong_trigger(self, current_round, user_has_triggers, scene_type):
        # 用户触发：命中关键词 → 直接触发
        if user_has_triggers:
            return True
        # 间隔控制：至少隔 8 轮（室内）/ 5 轮（室外）
        min_gap = 8 if scene_type.startswith("indoor") else 5
        if current_round - self.last_strong_round < min_gap:
            return False
        # 频率控制：室内不超过 10%，室外不超过 20%
        max_ratio = 0.10 if scene_type.startswith("indoor") else 0.20
        if self.total_reply_count > 0:
            if self.strong_trigger_count / self.total_reply_count > max_ratio:
                return False
        return True

    def should_weak_trigger(self, scene_type):
        # 弱互动：室内 20% 概率，室外 35% 概率
        prob = 0.20 if scene_type.startswith("indoor") else 0.35
        return random.random() < prob
```

### 5.5 场景互动提示词注入

在 `speak.jinja2` 中追加：

```jinja2
## 当前场景
你正在：{{ scene_name }}
{{ scene_atmosphere }}

场景中你可以互动的有：
{% for entity in scene_entities %}
- {{ entity }}
{% endfor %}

{% if scene_interaction %}
## 场景互动提示
{{ scene_interaction }}
请在回复中自然地提及或使用场景中的事物。
{% endif %}

## 动作约束
- 你的动作描写必须和当前场景一致
- 当前场景是「{{ scene_type }}」，所以：
  {% if scene_type == "indoor" %}
  - 不能出现"抬头看天""摘树叶""走在路上"等室外动作
  - 可以有"看向窗外""翻书""批文件""踱步"等室内动作
  {% else %}
  - 不能出现"批文件""看地图""翻书"等办公桌动作
  - 可以有"背着手走""看树""指鸟""坐下歇"等室外动作
  {% endif %}
```

---

## 六、主席主动结束对话

### 6.1 触发逻辑

```
时间线：
┌──────────────────────────────────────────────────────────────────┐
│ 0s        30s        60s      8min       10min        11min    │
│ 用户发消息   冷场动作1   冷场动作2   疲倦预警    离开语      自动退出  │
│             (idle)      (idle)   (打哈欠)   (主席说话)   (保存)   │
└──────────────────────────────────────────────────────────────────┘

具体触发：
1. 无用户输入 ≥ 8 分钟
   → 主席发出疲倦信号（按场景分层）
   → 例：室内"[主席打了个哈欠，揉了揉太阳穴]"；室外"[主席抬头看了看天色]"
   → 前端疲劳条转为红色

2. 无用户输入 ≥ 10 分钟（TIMEOUT_SECONDS 改为 10min）
   → 主席发出一段场景关联的结束语
   → 前端弹出提示 + 1 分钟倒计时

3. 离开语后 1 分钟内无用户响应
   → 自动保存会话日志
   → 回到首页

注意：如果用户在 8 分钟预警后重新发消息，所有计时器重置。
```

### 6.2 离开语模板

按场景分层：

```python
EXIT_TEMPLATES = {
    "shuwu": [
        (
            "[称呼]，[事件]。今天聊了不少，你回去再好好想想。"
            "下次再来，我让卫士给你泡杯好茶。"
        ),
        (
            "[称呼]，我马上有个会要开，[话题总结]。"
            "你先回去，有什么想不明白的，随时来找我。"
        ),
    ],
    "keting": [
        (
            "[称呼]，坐久了也乏了。我让警卫员送你出去。"
            "今天聊的这些，你回去琢磨琢磨。"
        ),
        (
            "[称呼]，天不早了，[事件]。"
            "[话题总结]，下次来了接着聊。"
        ),
    ],
    "xiaolu": [
        (
            "[称呼]，走了一圈也差不多了，该回去了。"
            "你也回去歇着吧。[话题总结]"
        ),
        (
            "[称呼]，风大了，回屋吧。"
            "今天散步聊的这些，你记住就好。下次再走。"
        ),
    ],
    "shuxia": [
        (
            "[称呼]，太阳快落山了，该回了。"
            "[话题总结]你回去再好好思考一下，欢迎下次再来。"
        ),
        (
            "[称呼]，树下坐久了腿都麻了。起来活动活动，你也回去吧。"
            "改天再聊。"
        ),
    ],
}
```

### 6.3 称呼和事件随机池

```python
GREETING_NAMES = [
    "小鬼", "小同志", "年轻人", "你这个小鬼头", "同志",
]

RANDOM_EVENTS_BY_SCENE = {
    "shuwu": [
        "我马上有客人要来",
        "待会儿有个会",
        "这份文件还没批完",
        "我有点累了，需要休息下",
    ],
    "keting": [
        "我有点乏了，想眯一会儿",
        "警卫员该来送晚饭了",
        "天黑了该开灯了",
    ],
    "xiaolu": [
        "风有点凉了",
        "该回去办公了",
        "走了这么远也该歇歇了",
    ],
    "shuxia": [
        "太阳快落山了",
        "蚊子多了",
        "起风了，怕要变天",
    ],
}
```

### 6.4 离开流程

```
[前端]
1. idle timer 累计到 10 分钟
2. 调用 POST /api/chat/scene-exit（后端组装离开语）
3. 返回 {exit_message, countdown_seconds: 60}
4. 聊天区域显示主席离开语（打字机效果）
5. 底部出现倒计时条："60 秒后自动退出"
   ┌──────────────────────────────────────────┐
   │ ⏳ 主席已离开，60 秒后自动保存并返回首页    │
   │ [立即退出]              [再聊会儿]        │
   └──────────────────────────────────────────┘
6. 倒计时到 0 → 自动 saveSession() + 回到首页
7. 用户点击"再聊会儿" → 重新进入对话，idle timer 重置
```

---

## 七、普通互动 vs 场景互动分类

### 7.1 定义

| 类型 | 定义 | 触发方式 | 示例 |
|------|------|---------|------|
| **普通互动** | 不关联场景事物的常规对话 | 默认模式，每次对话都发生 | 讨论哲学、历史、时事 |
| **场景互动** | 关联当前场景事物的互动 | 触发条件满足时发生 | 主席指树、聊天气、借物喻理 |

### 7.2 普通互动的内容范围

- RAG 检索 + 知识库驱动的回答（核心）
- 不刻意植入场景事物
- 不使用场景专属动作（使用通用动作）
- 不改变场景背景/氛围

### 7.3 场景互动的内容范围

- **动作层面**：使用场景专属动作（概率 70%）
- **语言层面**：在回复中融入场景事物（弱互动 40% 概率）
- **话题层面**：主席主动以场景事物为切入点（强互动，受频次控制）
- **氛围层面**：回复语气与场景氛围一致
  - 室内：更正式、更深思熟虑
  - 室外：更放松、更随意、更多自然比喻

### 7.4 频率设计

```
每 10 条主席回复中（预期分布）：

室内场景（菊香书屋 / 丰泽园客厅）：
├── 普通互动：9 条
│   └── 纯知识/观点回复，偶尔带通用动作
└── 场景互动（弱）：1 条
    └── 回复中提及场景事物或使用场景专属动作

室外场景（小路上 / 树下）：
├── 普通互动：8 条
│   └── 纯知识/观点回复
├── 场景互动（弱）：1~2 条
│   └── 回复中自然融入场景事物
└── 场景互动（强）：0~1 条
    └── 主席以场景事物为引子开启话题
```

**设计原则**：场景互动是"调味料"而非主菜。主席的核心价值在于知识和思想的深度，场景只是增加沉浸感的辅助手段，不能喧宾夺主。

### 7.5 实现方式

在 `build_speak_prompt` 中新增参数控制互动强度：

```python
def build_speak_prompt(self, question, thinking_result, scene_context=None, interaction_level="normal"):
    """
    interaction_level:
      - "normal": 普通互动，不刻意注入场景事物
      - "weak": 弱场景互动，提示融入场景事物但不强制
      - "strong": 强场景互动，要求以场景事物为引子
    """
```

---

## 八、游戏化：考考你（嵌入对话流）

### 8.1 设计理念

「考考你」不是独立游戏面板，而是**对话流的一部分**。主席聊到兴起时，自然而然地考用户一个问题——就像真实的聊天中，长辈突然问"那我考考你"一样。

### 8.2 出题触发条件

```
触发条件（满足任一 + 频次控制）：

1. 主席主动出题（强场景互动的一种形式）
   ├── 对话轮次 ≥ 8 且 场景互动频次允许
   ├── 主席正在讲某个话题（哲学/历史/诗词/党史/军事）
   └── 主席在回复结尾附上一道选择题
   
2. 用户主动求考
   ├── 点击 🔔 按钮 → 发送"主席，您考考我吧"
   ├── 直接输入"考考我""出个题"等
   └── 主席立即出一道题
   
3. 场景联动（不同场景倾向不同题型）
   ├── 菊香书屋 → 主：党史（50%） 副：哲学（30%） 通用（20%）
   │    └── 书房+红机电话，聊党史和辩证法最自然
   ├── 丰泽园客厅 → 主：历史（50%） 副：诗词（30%） 通用（20%）
   │    └── 藤椅喝茶看报纸，谈古论诗
   ├── 小路上 → 主：军事（50%） 副：党史（30%） 通用（20%）
   │    └── 散步时聊行军打仗、战略战术
   └── 树下 → 主：诗词（50%） 副：哲学（30%） 通用（20%）
        └── 树荫闲坐，吟诗论道，人生感悟
```

**频次控制**：每 15 轮对话最多主动出 1 次题。用户求考不限。

### 8.3 对话内交互流程

```
┌──────────────────────────────────────────┐
│ 主席：说到辩证法的运用，我问你一个问题——      │
│                                          │
│ ┌────────────────────────────────────┐   │
│ │ 📝 《矛盾论》写于哪一年？            │   │
│ │                                    │   │
│ │ [1936年]  [1937年]  [1938年]       │   │
│ └────────────────────────────────────┘   │
│                                          │
│ （用户点击了 [1937年]）                    │
│                                          │
│ 主席：对头！1937年8月，和《实践论》同年。   │
│ 看来你下了点功夫。                         │
│ （对话自然继续...）                        │
└──────────────────────────────────────────┘
```

**UI 细节**：
- 题目以主席消息气泡形式出现，内容包含题目文字 + 3 个可点击选项按钮
- 选项按钮样式：米黄色底、深红边框，hover 变深红底白字
- 点击选项后：所有选项变灰不可再点，选中的高亮（✓ 或 ✗ 标记）
- 主席在**下一条消息**中点评（对错 + 一句背景知识）
- 答对 → 连对计数器 +1；连对 3 题 → 主席特殊表扬
- 答错 → 连对计数器归零
- 整个问答就是正常对话的 2 轮（主席出题 → 用户答 → 主席点评），不跳出对话流

### 8.4 后端实现

#### 8.4.1 题库结构 (`pipeline/game_engine.py`)

```python
QUESTIONS = [
    {
        "id": 1,
        "q": "《矛盾论》写于哪一年？",
        "opts": ["1936年", "1937年", "1938年"],
        "answer": 1,  # 正确选项索引
        "hint": "1937年8月，和《实践论》同年写的。",
        "category": "哲学",         # 题型分类
        "scene_bias": ["shuwu"],    # 倾向场景（空=通用）
    },
    # ... 30 题
]

PRAISE = [
    "对头！",
    "没错，就是这个理。",
    "看来你下了点功夫。",
    "孺子可教。",
    "答得好。",
    "嗯，记得不错。",
    "小鬼，有两下子嘛。",
]

CORRECT_MSG = [
    "不对。",
    "没说到点子上。",
    "再想想看。",
    "差一点。",
    "这个没记住啊。",
]

STREAK_PRAISE = {  # 连对特殊表扬
    3: "连对三道！小鬼，你读了不少书嘛。",
    5: "五道全对！看来你是真下了功夫的。",
    7: "不得了，你这是把我的书都翻过了？",
}
```

#### 8.4.2 API 改动

**不在 chat 之外新增接口**。出题逻辑集成在 chat 流程中：

```python
# web/app.py — chat 接口内

# speak 阶段完成后，检查是否需要附加题目
if _should_quiz(scene_id, round_count):
    question = game_engine.pick_question(scene_id, asked_ids)
    answer["quiz"] = {
        "q": question["q"],
        "opts": question["opts"],
        "id": question["id"],
    }
    session_pending_quiz = question["id"]

# 用户下一条消息：如果 session_pending_quiz 不为空
# 且用户消息只是 "A"/"B"/"C" 或选项索引
# → 判断对错，生成点评，清除 pending
# → 用户消息如果是正常文本 → 正常 chat，清除 pending（视作跳过）
```

#### 8.4.3 出题选择逻辑

```python
# 场景 → 题型权重
SCENE_BIAS = {
    "shuwu":  {"党史": 0.50, "哲学": 0.30},   # 20% 通用
    "keting":  {"历史": 0.50, "诗词": 0.30},
    "xiaolu":  {"军事": 0.50, "党史": 0.30},
    "shuxia":  {"诗词": 0.50, "哲学": 0.30},
}

def pick_question(scene_id, asked_ids):
    """按场景偏好加权选题，已出过的不重复"""
    bias = SCENE_BIAS.get(scene_id, {})
    available = [q for q in QUESTIONS if q["id"] not in asked_ids]
    if not available:
        asked_ids.clear()
        available = QUESTIONS
    
    # 加权随机：偏向题权重高，但也可能选到通用题
    weights = []
    for q in available:
        w = bias.get(q.get("category", ""), 0.20)  # 无倾向 = 20% 底权
        weights.append(w)
    return random.choices(available, weights=weights, k=1)[0]
```

### 8.5 🔔 按钮新角色

```
聊天操作栏（4 个按钮）：
┌─────────┬─────────┬─────────┬─────────┐
│ 💾 保存 │🔥 找话题│ 🔔 考考 │ 🚪 退出 │
└─────────┴─────────┴─────────┴─────────┘
```

- 点击后：在输入框填入"主席，您考考我吧"并自动发送
- 和 🔥找话题 按钮一样，是一个「快捷话题启动器」
- 如果正在进行中（pending quiz），按钮变灰不可用

---

## 九、数据流总览（更新）

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (app.js)                            │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ 场景标签栏 │  │ 聊天输入  │  │ 过渡动画层     │  │
│  │ sceneBar  │  │ chatInput│  │ transition    │  │
│  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │             │                 │           │
│       ▼             ▼                 ▼           │
│  POST /api/     POST /api/      POST /api/        │
│  scene/set     chat             scene/transition  │
│  (含 quiz 答    (含 quiz 出题)                    │
│   题判定)
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                         后端 (app.py)                             │
│                                                                   │
│  session_scene ──→ build_speak_prompt(scene_context)             │
│  pending_quiz_id (出题状态，存内存)                                │
│  idle_timer (10min → exit)                                       │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐        │
│  │ scenes.py   │  │ game_engine  │  │ speak.jinja2     │        │
│  │ 场景定义     │  │ 题库+选题    │  │ + 场景氛围注入    │        │
│  │ 动作库      │  │ 评分+表扬   │  │ + 动作约束       │        │
│  │ 事物清单     │  │ (嵌入chat)  │  │ + 场景互动提示    │        │
│  └─────────────┘  └──────────────┘  └──────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 十、实现优先级

### Phase 1：核心场景系统（最小可行）

1. `pipeline/scenes.py` — 场景定义、动作库、事物清单
2. `web/app.py` — `POST /api/scene/set`、`GET /api/scene/get`
3. `web/static/index.html` — 场景标签栏 HTML
4. `web/static/app.js` — `setScene()` 函数
5. `web/static/style.css` — 场景标签样式
6. `reasoning/prompts/speak.jinja2` — 注入场景氛围 + 动作约束

### Phase 2：场景互动

7. `reasoning/framework.py` — `build_speak_prompt` 增加 `scene_context` 参数
8. `web/app.py` — chat 接口传入场景信息，speak 阶段注入场景互动提示
9. `web/app.py` — idle-actions 接口改为按场景返回动作

### Phase 3：场景切换动画

10. `POST /api/scene/transition` — 过渡文字生成
11. 前端过渡层 HTML/CSS/JS
12. 背景图 CSS 变量切换

### Phase 4：主席主动结束

13. 后端：10min 超时 → exit 语生成
14. 前端：倒计时退出 UI

### Phase 5：游戏化（嵌入对话流）

15. `pipeline/game_engine.py` — 题库（30 题，5 分类 × 6 题）、选题逻辑、评分表扬
16. `web/app.py` — chat 接口中集成出题判断 + 答题判定；`pending_quiz_id` 状态
17. `reasoning/prompts/speak.jinja2` — 追加 quiz 出题提示段
18. `web/static/app.js` — 解析 `quiz` 字段渲染选项按钮；答题交互；连对计数
19. `web/static/style.css` — 选项按钮样式、正确/错误高亮
20. `web/static/index.html` — 操作栏增加 🔔 按钮（快捷求考）

---

## 十一、待讨论事项

1. ~~**切换动画复杂度**~~ ✅ 已决策：幻灯片背景切换，中间插入过渡场景（门廊/楼道/小路），同类型直接切。
2. ~~**主席离开的 10 分钟阈值**~~ ✅ 已决策：8 分钟疲倦预警 → 10 分钟离开语 → 11 分钟自动退出。
3. ~~**场景切换是否需要用户确认**~~ ✅ 已决策：用户主动操作直接切换；主席提议时弹窗确认。
4. ~~**场景互动占比**~~ ✅ 已决策：室外 20%（强互动），室内 10%（强互动）。
5. ~~**游戏化模式**~~ ✅ 已决策：嵌入对话流（模式 B），不设独立面板；🔔 按钮改为快捷求考；题库扩到 30 题、5 分类。
6. ~~**过渡场景背景图生成**~~ ✅ 提示词已写入 §3.5（5 张过渡场景）。
7. ~~**主场景背景图生成**~~ ✅ 提示词已写入 §3.5（4 张主场景）。

---

*方案版本：v2.0 | 2026-07-31 | 5 项已决策，2 项待讨论*
