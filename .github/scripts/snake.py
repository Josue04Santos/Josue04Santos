#!/usr/bin/env python3
"""Gera uma cobrinha que percorre o mapa de contribuicoes e CRESCE a cada bloco comido.

Saidas: dist/snake.svg (tema claro) e dist/snake-dark.svg (tema escuro).
Uso: GITHUB_TOKEN=... GITHUB_USER=login python snake.py
"""
import json
import os
import random
import urllib.request

USER = os.environ.get("GITHUB_USER", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

CELL = 12      # tamanho do quadradinho
GAP = 3        # espaco entre quadradinhos
PITCH = CELL + GAP
PAD = 16       # margem
STEP = 0.09    # segundos por passo da cobra
START_LEN = 4  # tamanho inicial (cabeca + 3)
PAUSE = 2.0    # pausa antes de reiniciar

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
THEMES = {
    "snake.svg": {
        "cells": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "border": "#1b1f230f",
        "head": "#6f42c1",
        "body": "#8a63d2",
    },
    "snake-dark.svg": {
        "cells": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "border": "#ffffff0d",
        "head": "#b180ff",
        "body": "#9b6bf2",
    },
}


def fetch_calendar():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { weekday contributionLevel contributionCount } }
          }
        }
      }
    }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = {}
    for w, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[(w, day["weekday"])] = LEVELS.index(day["contributionLevel"])
    return grid, len(weeks)


def fake_calendar():
    random.seed(4)
    grid = {(w, d): (random.choice([0] * 6 + [1, 2, 3, 4])) for w in range(53) for d in range(7)}
    return grid, 53


def xy(w, d):
    return PAD + w * PITCH, PAD + d * PITCH


def build(grid, nweeks):
    # Caminho em serpentina coluna a coluna (sobe e desce), comecando fora do mapa a esquerda
    cells = [c for c in grid]
    route = []
    for w in range(nweeks):
        days = range(7) if w % 2 == 0 else range(6, -1, -1)
        for d in days:
            if (w, d) in grid:
                route.append((w, d))
    foods = [c for c in route if grid[c] > 0]
    max_len = START_LEN + len(foods)

    pre = [(-k, 0) for k in range(3, 0, -1)]
    last_w, last_d = route[-1]
    post = [(last_w + k, last_d) for k in range(1, max_len + 2)]
    path = pre + route + post
    n = len(path)
    dur = (n - 1) * STEP + max_len * STEP + PAUSE

    # instante (desde o inicio do ciclo) em que a cabeca chega a cada celula
    t_at = {c: (i * STEP) for i, c in enumerate(path) if c in grid}
    eat_times = [t_at[c] for c in foods]
    return path, foods, eat_times, max_len, dur, cells


def svg(theme, grid, nweeks, path, foods, eat_times, max_len, dur):
    width = PAD * 2 + nweeks * PITCH - GAP
    height = PAD * 2 + 7 * PITCH - GAP
    pts = " ".join(f"{x + CELL / 2:.1f},{y + CELL / 2:.1f}" for x, y in (xy(w, d) for w, d in path))
    motion_len = (len(path) - 1) * STEP
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<desc>Mapa de contribuicoes com cobrinha que cresce a cada bloco comido</desc>',
        f'<defs><path id="route" d="M{pts.replace(" ", " L")}"/></defs>',
        f'<rect width="0" height="0"><animate id="loop" attributeName="x" from="0" to="0" dur="{dur:.2f}s" begin="0s;loop.end"/></rect>',
    ]
    food_set = set(foods)
    eat_at = dict(zip(foods, eat_times))
    for (w, d), lvl in sorted(grid.items()):
        x, y = xy(w, d)
        color = theme["cells"][lvl]
        rect = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}" stroke="{theme["border"]}"'
        if (w, d) in food_set:
            t = eat_at[(w, d)]
            out.append(
                rect + ">"
                f'<set attributeName="fill" to="{color}" begin="loop.begin"/>'
                f'<set attributeName="fill" to="{theme["cells"][0]}" begin="loop.begin+{t:.2f}s"/>'
                "</rect>"
            )
        else:
            out.append(rect + "/>")

    # segmentos: cauda desenhada primeiro, cabeca por ultimo (fica por cima)
    for i in range(max_len - 1, -1, -1):
        size = CELL if i == 0 else max(CELL - 2 - i * 0.04, 7)
        off = size / 2
        color = theme["head"] if i == 0 else theme["body"]
        seg = [f'<rect x="{-off:.1f}" y="{-off:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{size / 2.6:.1f}" fill="{color}" opacity="0">']
        seg.append(
            f'<animateMotion dur="{motion_len:.2f}s" '
            f'begin="loop.begin+{i * STEP:.2f}s" fill="freeze" calcMode="linear"><mpath href="#route"/></animateMotion>'
        )
        t = i * STEP if i < START_LEN else max(eat_times[i - START_LEN], i * STEP)
        seg.append(f'<set attributeName="opacity" to="0" begin="loop.begin"/>')
        seg.append(f'<set attributeName="opacity" to="1" begin="loop.begin+{t + 0.01:.2f}s"/>')
        seg.append("</rect>")
        out.append("".join(seg))
    out.append("</svg>")
    return "\n".join(out)


def main():
    grid, nweeks = fetch_calendar() if TOKEN else fake_calendar()
    path, foods, eat_times, max_len, dur, _ = build(grid, nweeks)
    os.makedirs("dist", exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join("dist", name), "w") as f:
            f.write(svg(theme, grid, nweeks, path, foods, eat_times, max_len, dur))
    print(f"{len(foods)} dias com contribuicao; cobrinha cresce de {START_LEN} ate {max_len}; ciclo {dur:.1f}s")


if __name__ == "__main__":
    main()
