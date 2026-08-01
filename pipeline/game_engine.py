"""游戏化引擎：考考你 — 嵌入对话流的问答系统。"""
import random

QUESTIONS = [
    # -- 哲学 --
    {"id": 1, "q": "《矛盾论》写于哪一年？", "opts": ["1936年", "1937年", "1938年"], "answer": 1, "hint": "1937年8月，和《实践论》同年写的。", "category": "哲学"},
    {"id": 2, "q": "《实践论》的核心观点是什么？", "opts": ["理论指导实践", "实践是检验真理的唯一标准", "实践出真知"], "answer": 1, "hint": "实践是检验真理的唯一标准——这句话的根在《实践论》。", "category": "哲学"},
    {"id": 3, "q": "矛盾的特殊性是什么意思？", "opts": ["每个矛盾都不一样", "矛盾无处不在", "矛盾可以转化"], "answer": 0, "hint": "具体问题具体分析——这就是矛盾特殊性的要义。", "category": "哲学"},
    {"id": 4, "q": "辩证法有哪三大规律？", "opts": ["对立统一、量变质变、否定之否定", "矛盾、发展、运动", "正反合、因果、必然"], "answer": 0, "hint": "对立统一是核心，量变质变和否定之否定是展开。", "category": "哲学"},
    {"id": 5, "q": "实事求是最早出自哪里？", "opts": ["《汉书》", "《改造我们的学习》", "《实践论》"], "answer": 1, "hint": "1941年在延安整风时正式提出，但这个词的根在《汉书》。", "category": "哲学"},
    {"id": 6, "q": "主要矛盾和次要矛盾的区分关键是？", "opts": ["看哪个先出现", "看哪个起支配作用", "看哪个更难解决"], "answer": 1, "hint": "抓主要矛盾——谁起支配和决定作用，谁就是主要的。", "category": "哲学"},

    # -- 党史 --
    {"id": 7, "q": "遵义会议是哪一年召开的？", "opts": ["1934年", "1935年", "1936年"], "answer": 1, "hint": "1935年1月，长征路上的转折点。", "category": "党史"},
    {"id": 8, "q": "中共一大最初有几位代表？", "opts": ["11位", "12位", "13位"], "answer": 2, "hint": "13位代表，代表全国50多名党员。", "category": "党史"},
    {"id": 9, "q": "延安整风运动的核心内容是？", "opts": ["反对主观主义、宗派主义、党八股", "反对官僚主义", "反对本本主义"], "answer": 0, "hint": "三风：学风、党风、文风。", "category": "党史"},
    {"id": 10, "q": "枪杆子里出政权是在哪次会议上提出的？", "opts": ["遵义会议", "八七会议", "古田会议"], "answer": 1, "hint": "1927年八七会议，大革命失败后的反思。", "category": "党史"},
    {"id": 11, "q": "红军长征走了多少里？", "opts": ["一万五千里", "二万五千里", "三万里"], "answer": 1, "hint": "二万五千里——中央红军从江西到陕北的距离。", "category": "党史"},
    {"id": 12, "q": "新中国成立是几月几号？", "opts": ["9月21日", "10月1日", "10月10日"], "answer": 1, "hint": "1949年10月1日，天安门城楼上。", "category": "党史"},

    # -- 历史 --
    {"id": 13, "q": "秦皇汉武中的汉武指谁？", "opts": ["汉高祖刘邦", "汉武帝刘彻", "汉光武帝刘秀"], "answer": 1, "hint": "汉武帝刘彻——略输文采那位。", "category": "历史"},
    {"id": 14, "q": "《资治通鉴》是谁编的？", "opts": ["司马迁", "司马光", "班固"], "answer": 1, "hint": "北宋司马光，编了19年。", "category": "历史"},
    {"id": 15, "q": "中国历史上第一个统一的封建王朝是？", "opts": ["周朝", "秦朝", "汉朝"], "answer": 1, "hint": "秦始皇统一六国，建立了第一个中央集权王朝。", "category": "历史"},
    {"id": 16, "q": "成吉思汗的原名叫什么？", "opts": ["忽必烈", "铁木真", "窝阔台"], "answer": 1, "hint": "铁木真——只识弯弓射大雕那位。", "category": "历史"},
    {"id": 17, "q": "太平天国起义的领袖是谁？", "opts": ["洪秀全", "石达开", "李自成"], "answer": 0, "hint": "洪秀全，从广西金田村起兵。", "category": "历史"},
    {"id": 18, "q": "辛亥革命推翻了哪个朝代？", "opts": ["明朝", "清朝", "元朝"], "answer": 1, "hint": "1911年，孙中山领导的辛亥革命结束了清朝。", "category": "历史"},

    # -- 诗词 --
    {"id": 19, "q": "俱往矣，数风流人物，还看今朝出自哪首词？", "opts": ["《沁园春·长沙》", "《沁园春·雪》", "《浪淘沙·北戴河》"], "answer": 1, "hint": "《沁园春·雪》，1945年在重庆谈判时发表，轰动一时。", "category": "诗词"},
    {"id": 20, "q": "雄关漫道真如铁，而今迈步从头越写的是什么关？", "opts": ["山海关", "娄山关", "嘉峪关"], "answer": 1, "hint": "娄山关——长征中打的一场硬仗，在贵州。", "category": "诗词"},
    {"id": 21, "q": "天若有情天亦老的下一句是？", "opts": ["人间正道是沧桑", "月如无恨月长圆", "海枯石烂不变心"], "answer": 0, "hint": "人间正道是沧桑——化用了李贺的诗。", "category": "诗词"},
    {"id": 22, "q": "北国风光，千里冰封，万里雪飘描写的是哪条河？", "opts": ["长江", "黄河", "黑龙江"], "answer": 1, "hint": "望长城内外，惟余莽莽；大河上下，顿失滔滔——大河就是黄河。", "category": "诗词"},
    {"id": 23, "q": "毛泽东的第一首公开发表的诗是哪首？", "opts": ["《七律·长征》", "《沁园春·雪》", "《七绝·改西乡隆盛诗赠父亲》"], "answer": 2, "hint": "孩儿立志出乡关——17岁时写的，改自日本西乡隆盛的诗。", "category": "诗词"},
    {"id": 24, "q": "一万年太久，只争朝夕出自哪首词？", "opts": ["《满江红·和郭沫若同志》", "《念奴娇·鸟儿问答》", "《水调歌头·游泳》"], "answer": 0, "hint": "1963年写的《满江红》，回应郭沫若的。", "category": "诗词"},

    # -- 军事 --
    {"id": 25, "q": "四渡赤水是哪一年？", "opts": ["1934年", "1935年", "1936年"], "answer": 1, "hint": "1935年1-3月，长征中最精彩的军事行动。", "category": "军事"},
    {"id": 26, "q": "三大战役不包括哪个？", "opts": ["辽沈战役", "淮海战役", "渡江战役"], "answer": 2, "hint": "三大战役是辽沈、淮海、平津。渡江战役在后。", "category": "军事"},
    {"id": 27, "q": "敌进我退，敌驻我扰，敌疲我打，敌退我追是哪个时期的战术？", "opts": ["抗日战争", "井冈山时期", "解放战争"], "answer": 1, "hint": "井冈山时期的游击战十六字诀。", "category": "军事"},
    {"id": 28, "q": "平型关大捷发生在哪一年？", "opts": ["1936年", "1937年", "1938年"], "answer": 1, "hint": "1937年9月，八路军首战告捷。", "category": "军事"},
    {"id": 29, "q": "长征途中哪次战役损失最大？", "opts": ["四渡赤水", "湘江战役", "强渡大渡河"], "answer": 1, "hint": "湘江战役——红军从8万锐减到3万。", "category": "军事"},
    {"id": 30, "q": "集中优势兵力，各个歼灭敌人是哪篇文章提出的？", "opts": ["《论持久战》", "《集中优势兵力，各个歼灭敌人》", "《中国革命战争的战略问题》"], "answer": 1, "hint": "1946年9月，解放战争初期写的专门指示。", "category": "军事"},
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

STREAK_PRAISE = {
    3: "连对三道！小鬼，你读了不少书嘛。",
    5: "五道全对！看来你是真下了功夫的。",
    7: "不得了，你这是把我的书都翻过了？",
}

SCENE_BIAS = {
    "shuwu":  {"党史": 0.50, "哲学": 0.30},
    "keting":  {"历史": 0.50, "诗词": 0.30},
    "xiaolu":  {"军事": 0.50, "党史": 0.30},
    "shuxia":  {"诗词": 0.50, "哲学": 0.30},
}

def pick_question(scene_id: str, asked_ids: set) -> dict | None:
    bias = SCENE_BIAS.get(scene_id, {})
    available = [q for q in QUESTIONS if q["id"] not in asked_ids]
    if not available:
        return None
    weights = [bias.get(q.get("category", ""), 0.20) for q in available]
    return random.choices(available, weights=weights, k=1)[0]


def check_answer(question_id: int, user_answer: int) -> dict:
    q = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if not q:
        return {"correct": False, "msg": "这道题好像有点问题...", "streak": 0}
    correct = q["answer"] == user_answer
    if correct:
        msg = random.choice(PRAISE) + " " + q.get("hint", "")
    else:
        correct_opt = q["opts"][q["answer"]]
        msg = random.choice(CORRECT_MSG) + " 答案是" + correct_opt + "。" + q.get("hint", "")
    return {"correct": correct, "msg": msg, "correct_answer": q["answer"]}


def get_question(question_id: int) -> dict | None:
    return next((q for q in QUESTIONS if q["id"] == question_id), None)


def should_quiz(round_count: int, quiz_count: int) -> bool:
    if round_count < 8:
        return False
    if quiz_count > 0 and (round_count / max(quiz_count, 1)) < 15:
        return False
    return True
