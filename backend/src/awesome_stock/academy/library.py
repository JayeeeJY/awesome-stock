"""Validated, static Academy documents with no market or model dependency."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AcademyDocument:
    document_id: str
    category: str
    category_label: str
    title: str
    short_title: str
    lead: str
    definition: str
    reading_points: tuple[str, ...]
    misreads: tuple[str, ...]
    checklist: tuple[str, ...]
    diagram: str
    formula: str | None = None

    def __post_init__(self) -> None:
        if self.category not in {"technical", "options"}:
            raise ValueError("academy category is invalid")
        if self.diagram not in {"price_volume", "moving_average", "rsi", "macd", "bollinger", "option_contract", "option_payoff", "option_greeks"}:
            raise ValueError("academy diagram is invalid")
        if len(self.reading_points) < 3 or len(self.misreads) < 2 or len(self.checklist) < 4:
            raise ValueError("academy document is incomplete")


@dataclass(frozen=True)
class AcademyLibrary:
    documents: tuple[AcademyDocument, ...]

    def __post_init__(self) -> None:
        identifiers = tuple(item.document_id for item in self.documents)
        if len(self.documents) != 8 or len(set(identifiers)) != len(identifiers):
            raise ValueError("academy library must contain eight unique documents")
        if {item.category for item in self.documents} != {"technical", "options"}:
            raise ValueError("academy library categories are incomplete")

    def document(self, document_id: str) -> AcademyDocument:
        for item in self.documents:
            if item.document_id == document_id:
                return item
        raise KeyError(document_id)


def build_academy_library() -> AcademyLibrary:
    """Return the reviewed Community learning set; all examples are illustrative."""

    return AcademyLibrary((
        AcademyDocument(
            "price-volume", "technical", "技术分析", "K线与成交量：先读价格，再看参与度", "K线与成交量",
            "K线记录一段时间内的开、高、低、收；成交量补充市场参与程度。两者合看，比单独猜一根蜡烛更可靠。",
            "实体表达开盘与收盘的距离，影线表达盘中触及但未能维持的价格区域。成交量是该周期成交数量，不等于净买入或净卖出。",
            ("先确定周期；日线结论不能直接替代周线趋势。", "价格突破并伴随相对放量，说明更多参与者接受了新价格区域。", "缩量回撤可能表示抛压减弱，也可能只是交易兴趣下降，需要结合位置判断。"),
            ("单根阳线或阴线不能独立证明趋势反转。", "放量只说明成交活跃，不自动等于主力买入，也不保证后续方向。"),
            ("确认观察周期与复权口径。", "标出最近的结构高低点。", "比较成交量与自身近期均值，而非只看绝对值。", "写下失效条件，避免事后解释。"),
            "price_volume",
        ),
        AcademyDocument(
            "moving-average", "technical", "技术分析", "移动平均线：用平滑换取方向感", "移动平均线",
            "移动平均线压低短期噪声，帮助观察一段时间内的价格方向；它是滞后工具，不是提前知道未来的信号。",
            "简单移动平均线对窗口内价格等权；指数移动平均线让近期价格权重更高，因此通常反应更快。",
            ("价格位于上升均线上方，通常表示当前方向偏强，但不等于低风险。", "短期均线穿越长期均线描述动量变化，确认速度越快也越容易出现噪声。", "均线斜率比某一瞬间的上下位置更能说明趋势是否持续。"),
            ("横盘市场中交叉会频繁反复，不能机械追随。", "均线参数没有跨市场通用的最佳值，必须与持有周期一致。"),
            ("先定义持有周期，再选均线窗口。", "观察斜率、价格位置和结构是否一致。", "用成交量或波动指标做第二重确认。", "记录信号失效后如何退出。"),
            "moving_average", "SMA(n) = 最近 n 个收盘价之和 ÷ n",
        ),
        AcademyDocument(
            "rsi", "technical", "技术分析", "RSI：动量强弱，不是买卖按钮", "RSI",
            "RSI 衡量一段时间内上涨与下跌动量的相对强弱，用来观察动量是否极端、是否与价格结构出现分歧。",
            "RSI 通常在 0–100 之间波动，常见窗口为 14。70 与 30 是观察区而不是自动交易线，50 附近可辅助观察多空动量平衡。",
            ("70 以上表示近期上涨动量较强，不代表价格必须立即回落。", "30 以下表示近期下跌动量较强，不代表价格必然马上反弹。", "价格创新高而 RSI 未创新高属于看跌背离线索；背离需要价格结构确认。"),
            ("强趋势中 RSI 可以长期停留在高位或低位。", "不同周期的 RSI 可能给出相反线索，不能脱离时间尺度比较。"),
            ("先识别趋势，顺势优先、逆势谨慎。", "观察 RSI 所在区域和变化方向。", "把背离与结构位、成交量共同核对。", "在计划中写明入场、失效和风险边界。"),
            "rsi", "RSI = 100 − 100 ÷ (1 + 平均上涨幅度 ÷ 平均下跌幅度)",
        ),
        AcademyDocument(
            "macd", "technical", "技术分析", "MACD：观察趋势动量如何变化", "MACD",
            "MACD 比较快、慢两条指数移动平均线，并用信号线观察差值变化，适合确认趋势动量，不适合定义固定超买超卖区。",
            "常见参数以 12 期 EMA 减去 26 期 EMA 得到 MACD 线，再对 MACD 线计算 9 期 EMA 作为信号线；柱体表示两者差值。",
            ("MACD 上穿信号线表示向上动量相对增强，仍需看零轴和价格结构。", "零轴上方通常对应较强的中期上行动量，零轴下方反之。", "柱体收缩表示两线距离减小，即当前动量正在减弱。"),
            ("盘整期会出现多次来回交叉，交易成本可能吞噬信号。", "柱体变短表示动量减弱，不等于价格已经反转。"),
            ("确定当前是趋势还是盘整。", "同时读取零轴位置、交叉与柱体方向。", "用价格高低点核对背离。", "避免只凭一次交叉建立完整判断。"),
            "macd", "MACD = EMA(12) − EMA(26)；Signal = EMA(MACD, 9)",
        ),
        AcademyDocument(
            "bollinger", "technical", "技术分析", "布林带：把相对位置与波动放在一起", "布林带",
            "布林带以移动平均线为中轨，在上下加入与标准差相关的距离，用来观察价格的相对位置和波动扩张或收缩。",
            "常见设置是 20 期简单移动平均线，上下轨各距中轨 2 个标准差。带宽随近期波动变化，不是固定价格通道。",
            ("带宽收窄表示近期波动下降，之后可能扩张，但不能预知方向。", "价格沿上轨或下轨运行可能是强趋势延续，不应仅因触轨就反向。", "价格重新穿越中轨可以作为状态变化线索，需要趋势与成交量确认。"),
            ("触及上轨不自动代表高估，触及下轨也不自动代表低估。", "参数与周期改变会显著改变带宽，不应跨图直接比较。"),
            ("确认周期和参数。", "先看带宽变化，再看价格相对位置。", "辨别趋势运行还是区间摆动。", "用结构位和风险边界确认行动。"),
            "bollinger", "中轨 = SMA(20)；上下轨 = 中轨 ± 2 × 标准差",
        ),
        AcademyDocument(
            "option-contract", "options", "期权基础", "期权合约：先认清权利、义务与到期日", "期权合约基础",
            "期权买方支付权利金取得在约定时间按执行价买入或卖出标的的权利；卖方收取权利金并承担被履约时的义务。",
            "看涨期权对应买入标的的权利，看跌期权对应卖出标的的权利。合约还包含标的、执行价、到期日、乘数与行权方式。",
            ("买入期权的权利金会随内在价值、剩余时间、隐含波动率等因素变化。", "价内、平值、价外描述标的价与执行价的关系，不代表最终盈利。", "到期前平仓、到期行权和到期失效是不同结果，券商处理规则也可能不同。"),
            ("权利金较低不等于风险小，全部归零仍是 100% 损失。", "卖出期权不是稳定收租；裸卖可能承担很大甚至理论上无限的风险。"),
            ("核对合约标的、执行价、到期日和乘数。", "分别写出买方与卖方的权利义务。", "确认最大损失、保证金和流动性。", "了解券商的行权、指派和到期处理规则。"),
            "option_contract",
        ),
        AcademyDocument(
            "option-payoff", "options", "期权基础", "盈亏结构：到期图不是全过程", "盈亏结构",
            "到期盈亏图帮助看清不同标的价格下的结果，但到期前价格还会受到剩余时间与隐含波动率影响。",
            "买入看涨的到期盈亏约为 max(标的价−执行价, 0)−权利金；买入看跌约为 max(执行价−标的价, 0)−权利金。",
            ("买方最大损失通常为已付权利金，盈亏平衡点还要计入权利金和费用。", "备兑看涨限制部分上涨收益，但下跌风险仍主要来自持有标的。", "价差策略同时买卖期权以限制成本和风险，也会限制潜在收益。"),
            ("不要把到期折线当作今天的期权价格。", "组合腿数越多，流动性、价差、指派和执行复杂度越高。"),
            ("画出到期时每一腿的现金流。", "计算最大盈利、最大损失和盈亏平衡点。", "评估到期前时间与波动率变化。", "把交易费用、滑点和提前指派纳入计划。"),
            "option_payoff", "到期盈亏 = 各腿内在价值之和 − 净权利金 − 费用",
        ),
        AcademyDocument(
            "option-greeks", "options", "期权基础", "希腊字母：拆解期权价格的敏感度", "希腊字母",
            "希腊字母描述期权价格对不同输入变化的敏感度，是局部估计，不是收益承诺，也不是在所有价格和时间上固定不变。",
            "Delta 近似标的价格变动的影响；Gamma 描述 Delta 的变化；Theta 描述时间流逝影响；Vega 描述隐含波动率变化影响。",
            ("Delta 既不是固定胜率，也会随标的、时间和波动率变化。", "临近到期时，平值期权的 Gamma 与 Theta 风险可能更集中。", "Vega 较高意味着隐含波动率变化对期权价格影响更大，方向判断正确也可能亏损。"),
            ("把 Theta 简化为每天固定损耗会忽略周末、波动率和价格变化。", "只看单个 Greek 会遗漏其他变量以及它们之间的联动。"),
            ("先明确方向、时间和波动率假设。", "检查组合净 Delta、Gamma、Theta 与 Vega。", "在临近到期和事件前重新评估敏感度。", "使用情景范围而非单点结果制定退出计划。"),
            "option_greeks",
        ),
    ))
