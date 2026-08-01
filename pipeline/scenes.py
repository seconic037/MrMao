"""场景系统：场景定义、动作库、事物清单、离开语模板。"""
import random

# ═══════════════════════════════════════════════════════════════════
# 场景定义
# ═══════════════════════════════════════════════════════════════════

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
    },
}

# 默认场景
DEFAULT_SCENE = "shuwu"

# 室内 / 室外分组
INDOOR_SCENES = [k for k, v in SCENES.items() if v["type"].startswith("indoor")]
OUTDOOR_SCENES = [k for k, v in SCENES.items() if v["type"].startswith("outdoor")]


# ═══════════════════════════════════════════════════════════════════
# 动作库
# ═══════════════════════════════════════════════════════════════════

# 通用动作：不依赖场景，任何场景都可安全使用
COMMON_ACTIONS = [
    # 烟/茶类
    "[主席抽了口烟，等你开口]",
    "[老人家端起搪瓷杯，喝了口浓茶]",
    "[主席掐灭烟头，若有所思地看着你]",
    "[主席往搪瓷杯里续了热水，杯口冒着白气]",
    # 神态类
    "[老人家微笑着，手指轻轻敲着]",
    "[主席点点头，示意你继续说]",
    "[老人家沉默了片刻，目光深远]",
    "[主席笑了起来，笑得很爽朗]",
    # 身体动作类
    "[老人家摘下眼镜，用衣角擦了擦]",
    "[主席轻轻叹了口气]",
]

# 疲劳动作（按场景类型）
FATIGUE_ACTIONS = {
    "indoor": {
        "yellow": [
            "[主席揉了揉太阳穴]",
            "[老人家放下手里的文件，闭了会儿眼]",
            "[主席端起搪瓷杯，喝完最后一口浓茶]",
            "[老人家把烟头掐灭，烟灰缸里已经四五个烟蒂了]",
        ],
        "red": [
            "[主席打了个哈欠，眼皮有点沉]",
            "[老人家身子往椅子里靠了靠，快睡着了]",
            "[主席的烟灰缸里已经堆满了烟头，他又续了一支]",
            "[老人家摆了摆手，像是说今天就到这儿吧]",
            "[主席摘下眼镜放到一旁，背靠在椅子上]",
        ],
    },
    "outdoor": {
        "yellow": [
            "[主席停下脚步，捶了捶腰]",
            "[老人家在路边石头上坐下来，喘了口气]",
            "[主席抬头看了看天色]",
        ],
        "red": [
            "[主席打了个哈欠，看了看回去的路]",
            "[老人家站起来拍拍裤腿，有点累了]",
            "[主席眯起眼看了看西斜的太阳]",
        ],
    },
}

# 离开语（按场景）
EXIT_TEMPLATES = {
    "shuwu": [
        "{name}，{event}。今天聊了不少，你回去再好好想想。下次再来，我让卫士给你泡杯好茶。",
        "{name}，我马上有个会要开。{summary}你先回去，有什么想不明白的，随时来找我。",
    ],
    "keting": [
        "{name}，坐久了也乏了。我让警卫员送你出去。今天聊的这些，你回去琢磨琢磨。",
        "{name}，天不早了，{event}。{summary}下次来了接着聊。",
    ],
    "xiaolu": [
        "{name}，走了一圈也差不多了，该回去了。你也回去歇着吧。{summary}",
        "{name}，风大了，回屋吧。今天散步聊的这些，你记住就好。下次再走。",
    ],
    "shuxia": [
        "{name}，太阳快落山了，该回了。{summary}你回去再好好思考一下，欢迎下次再来。",
        "{name}，树下坐久了腿都麻了。起来活动活动，你也回去吧。改天再聊。",
    ],
}

# 称呼随机池
GREETING_NAMES = ["小鬼", "小同志", "年轻人", "你这个小鬼头", "同志"]

# 随机事件（按场景）
RANDOM_EVENTS = {
    "shuwu": ["我马上有客人要来", "待会儿有个会", "这份文件还没批完", "我有点累了，需要休息下"],
    "keting": ["我有点乏了，想眯一会儿", "警卫员该来送晚饭了", "天黑了该开灯了"],
    "xiaolu": ["风有点凉了", "该回去办公了", "走了这么远也该歇歇了"],
    "shuxia": ["太阳快落山了", "蚊子多了", "起风了，怕要变天"],
}


# ═══════════════════════════════════════════════════════════════════
# 事物清单
# ═══════════════════════════════════════════════════════════════════

SCENE_ENTITIES = {
    "shuwu": {
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
            "window": {
                "name": "窗外",
                "desc": "窗外透进阳光，能看到院子里斑驳的树影（隔着窗，看得见出不去）",
                "triggers": ["窗外", "院子", "外面", "树影"],
                "reachable": False,
            },
        },
    },
    "keting": {
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
                "desc": "窗外能看到院子里的树影（隔着窗，看得见出不去）",
                "triggers": ["窗外", "院子", "外面"],
                "reachable": False,
            },
        },
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
            "locust_tree": {"name": "老槐树", "desc": "几棵老槐树，树冠如盖，投下斑驳树影", "triggers": ["树", "槐树", "大树"]},
            "flower": {"name": "路边花", "desc": "路边开着不知名的小花", "triggers": ["花", "好看"]},
        },
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
            "tree": {"name": "大树", "desc": "树冠如盖的大树，挡住了午后的太阳", "triggers": ["树", "大树", "树荫"]},
            "pond": {"name": "池塘", "desc": "远处的池塘，芦苇在微风里轻轻摇着", "triggers": ["池塘", "水", "鱼"]},
            "field": {"name": "菜地", "desc": "远处有一片菜地，绿油油的", "triggers": ["菜地", "菜", "种地", "庄稼"]},
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
# 过渡场景
# ═══════════════════════════════════════════════════════════════════

TRANSITIONS = {
    ("shuwu", "xiaolu"): {
        "scene": "菊香书屋门廊",
        "text": (
            "主席放下手里的文件，站起身说：'走，陪我出去走走。'"
            "你跟着他走出菊香书屋，穿过门廊……"
        ),
        "duration_ms": 2500,
    },
    ("xiaolu", "shuwu"): {
        "scene": "菊香书屋门廊",
        "text": (
            "走了一圈，主席在一棵树下停下来看了看，转身往回走。"
            "你跟着他穿过门廊，回到菊香书屋……"
        ),
        "duration_ms": 2500,
    },
    ("keting", "shuxia"): {
        "scene": "丰泽园庭院入口",
        "text": (
            "主席从藤椅上站起来，拿起蒲扇：'屋里闷，到树下坐坐。'"
            "你们走出丰泽园客厅，穿过小院子……"
        ),
        "duration_ms": 2500,
    },
    ("shuxia", "keting"): {
        "scene": "傍晚庭院入口",
        "text": (
            "太阳偏西了，主席拍拍裤腿站起来：'天晚了，进屋吧。'"
            "你们穿过院子，暮色里走回丰泽园客厅……"
        ),
        "duration_ms": 2500,
    },
    ("keting", "xiaolu"): {
        "scene": "丰泽园庭院入口",
        "text": (
            "主席从藤椅上起身：'走，到书屋外的小路上转转。'"
            "你们穿过庭院，来到中南海的小路上……"
        ),
        "duration_ms": 2500,
    },
    ("xiaolu", "keting"): {
        "scene": "丰泽园庭院入口",
        "text": (
            "沿着小路走了一阵，主席说：'走，去客厅坐坐。'"
            "你们穿过庭院，走进丰泽园客厅……"
        ),
        "duration_ms": 2500,
    },
    ("shuwu", "shuxia"): {
        "scene": "庭院小径",
        "text": (
            "主席放下文件，伸了个懒腰：'屋里闷，出去透透气。'"
            "你们沿着小径走到丰泽园外的大树下……"
        ),
        "duration_ms": 2500,
    },
    ("shuxia", "shuwu"): {
        "scene": "庭院小径",
        "text": (
            "主席拍拍裤腿上的草屑：'该回去办公了。'"
            "你们沿着小径走回菊香书屋……"
        ),
        "duration_ms": 2500,
    },
    ("shuwu", "keting"): {
        "scene": "走廊",
        "text": (
            "主席批完最后一份文件：'走，到客厅坐坐，这儿太闷。'"
            "你们从书房走过走廊，来到客厅……"
        ),
        "duration_ms": 2000,
    },
    ("xiaolu", "shuxia"): {
        "scene": "庭院小径",
        "text": (
            "沿着小路走了一阵，主席指指前面的大树：'那儿凉快，过去坐会儿。'"
            "你们沿小路走向丰泽园外的大树……"
        ),
        "duration_ms": 2500,
    },
}

# 同类型切换文字
SAME_TYPE_TRANSITION = {
    "indoor": "你跟着主席来到了{name}。",
    "outdoor": "你和主席走到了{name}。",
}

# 场景主动切换面板文案（问题 1：顶栏地点图标 → 弹层）
SCENE_SWITCH_TEMPLATES = {
    "indoor_to_outdoor": "主席，我们出去走走好吗？",
    "outdoor_to_indoor": "主席，外面风大，我们回屋吧？",
}

# 切换目标（当前 indoor → 室外目标；当前 outdoor → 室内目标）
SWITCH_TARGETS = {
    "to_outdoor": [("xiaolu", "🌳"), ("shuxia", "🌿")],
    "to_indoor": [("shuwu", "📚"), ("keting", "🛋️")],
}


# ═══════════════════════════════════════════════════════════════════
# 场景切换检测关键词
# ═══════════════════════════════════════════════════════════════════

SCENE_SWITCH_KEYWORDS = {
    "outdoor": ["出去走走", "到外面", "出去透透气", "散散步", "走走", "外面坐坐", "出去", "透透气"],
    "indoor": ["进屋", "进去坐", "回屋", "回去", "到屋里", "进去"],
}


# ═══════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════

def get_scene(scene_id: str) -> dict:
    """获取场景定义，无效 ID 返回默认场景。"""
    return SCENES.get(scene_id, SCENES[DEFAULT_SCENE])


def pick_action(scene_id: str, fatigue_level: str = "green") -> str:
    """选择动作：场景动作 70% 概率，通用动作 30%。疲劳时混入疲劳专属动作。"""
    scene = get_scene(scene_id)
    scene_type = scene["type"]

    if random.random() < 0.7:
        pool = list(scene["actions"])
    else:
        pool = list(COMMON_ACTIONS)

    # 疲劳时混入疲劳动作
    if fatigue_level != "green" and random.random() < 0.4:
        indoor_outdoor = "indoor" if scene_type.startswith("indoor") else "outdoor"
        fatigue_pool = FATIGUE_ACTIONS.get(indoor_outdoor, {}).get(fatigue_level, [])
        if fatigue_pool:
            pool = fatigue_pool

    return random.choice(pool)


def pick_idle_actions(scene_id: str, fatigue_level: str = "green", count: int = 3) -> list[str]:
    """返回 count 个冷场动作。"""
    actions = []
    seen = set()
    for _ in range(count * 2):
        action = pick_action(scene_id, fatigue_level)
        if action not in seen:
            actions.append(action)
            seen.add(action)
        if len(actions) >= count:
            break
    return actions


def pick_exit_message(scene_id: str, summary: str = "") -> str:
    """按场景生成离开语。"""
    templates = EXIT_TEMPLATES.get(scene_id, EXIT_TEMPLATES[DEFAULT_SCENE])
    template = random.choice(templates)
    name = random.choice(GREETING_NAMES)
    event = random.choice(RANDOM_EVENTS.get(scene_id, [""]))
    if summary:
        summary = summary + " "
    return template.format(name=name, event=event, summary=summary)


def detect_switch_intent(user_text: str, current_scene: str) -> str | None:
    """检测用户消息中的场景切换意图。返回目标场景 ID 或 None。"""
    scene = get_scene(current_scene)
    is_indoor = scene["type"].startswith("indoor")

    if is_indoor:
        for kw in SCENE_SWITCH_KEYWORDS["outdoor"]:
            if kw in user_text:
                return "xiaolu"  # 默认去小路
    else:
        for kw in SCENE_SWITCH_KEYWORDS["indoor"]:
            if kw in user_text:
                return "shuwu"  # 默认回书屋

    return None


def get_transition(from_scene: str, to_scene: str) -> dict | None:
    """获取两个场景之间的过渡信息。"""
    key = (from_scene, to_scene)
    if key in TRANSITIONS:
        return TRANSITIONS[key]

    # 同类型切换
    from_type = get_scene(from_scene)["type"]
    to_type = get_scene(to_scene)["type"]
    if from_type[0:3] == to_type[0:3]:  # indoor↔indoor 或 outdoor↔outdoor
        template = SAME_TYPE_TRANSITION.get(
            "indoor" if from_type.startswith("indoor") else "outdoor",
            "你跟着主席来到了{name}。"
        )
        return {
            "scene": "",
            "text": template.format(name=get_scene(to_scene)["name"]),
            "duration_ms": 1500,
        }

    # 兜底：跨类型未定义组合 → 通用过渡（纯文字，可无图）
    return {
        "scene": "",
        "text": f"你和主席来到了{get_scene(to_scene)['name']}。",
        "duration_ms": 1500,
    }


def get_scene_entities_flat(scene_id: str) -> list[str]:
    """展平场景事物列表，用于 LLM 提示词注入。"""
    entities = SCENE_ENTITIES.get(scene_id, {})
    flat = []
    for category in entities.values():
        if isinstance(category, dict):
            for item in category.values():
                if isinstance(item, dict) and "name" in item:
                    flat.append(f"{item['name']}（{item.get('desc', '')}）")
    return flat


def get_switch_options(scene_id: str) -> dict:
    """返回主动切换面板数据：文案 + 目标列表（问题 1）。"""
    scene = get_scene(scene_id)
    is_indoor = scene["type"].startswith("indoor")
    key = "to_outdoor" if is_indoor else "to_indoor"
    prompt = SCENE_SWITCH_TEMPLATES["indoor_to_outdoor" if is_indoor else "outdoor_to_indoor"]
    targets = [
        {"id": sid, "emoji": emoji, "name": SCENES[sid]["name"]}
        for sid, emoji in SWITCH_TARGETS[key]
    ]
    return {"prompt": prompt, "is_indoor": is_indoor, "targets": targets}
