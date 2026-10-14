"""问题二情形6与关键参数的灵敏度分析，用于模型检验。"""

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "求解" / "问题二" / "结果"
OUT.mkdir(parents=True, exist_ok=True)


def certified(price, ctest, p):
    return (price + ctest) / max(1e-12, 1 - p)


def profit(dec, p1, p2, q, price1, price2, c1, c2, c_a, c_t, sell, loss, dis):
    t1, t2, tf, u = dec
    good = 1.0
    cert_once = 0.0
    untested = 0.0
    eff_all = 0.0
    for t, p, price, c in ((t1, p1, price1, c1), (t2, p2, price2, c2)):
        if t:
            v = certified(price, c, p)
            cert_once += v
            eff_all += v
        else:
            good *= 1 - p
            untested += price
            eff_all += price
    rho = (1 - q) * good
    m = 1.0 / rho
    f = m - 1.0
    comp = cert_once + m * untested if u else m * eff_all
    cost = comp + c_a * m + (c_t * m if tf else loss * f) + (dis * f if u else 0)
    return sell - cost


def main():
    base = {
        "p1": 0.05, "p2": 0.05, "q": 0.05,
        "price1": 4, "price2": 18, "c1": 2, "c2": 3,
        "c_a": 6, "c_t": 3, "sell": 56,
    }
    rows = []
    for loss in (10, 20, 30, 50):
        for dis in (5, 20, 40):
            scores = []
            for dec in itertools.product([0, 1], repeat=4):
                pi = profit(dec, **base, loss=loss, dis=dis)
                scores.append((pi, dec))
            pi, dec = max(scores, key=lambda z: z[0])
            rows.append(
                {
                    "调换损失": loss,
                    "拆解费用": dis,
                    "零件1": "检测" if dec[0] else "不检测",
                    "零件2": "检测" if dec[1] else "不检测",
                    "成品": "检测" if dec[2] else "不检测",
                    "不合格品": "拆解" if dec[3] else "不拆解",
                    "单顾客期望利润": round(pi, 3),
                    "百件期望利润": round(pi * 100, 2),
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "情形6参数灵敏度.csv", index=False, encoding="utf-8-sig")
    with open(OUT / "灵敏度指标.json", "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, ensure_ascii=False, indent=2)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
