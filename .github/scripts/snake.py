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
STEP = 0.11    # segundos por passo da cobra
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
    """Simula uma partida de Snake: a cobra vai atras da comida mais proxima,
    desvia do proprio corpo, prefere seguir reto e cresce a cada bloco comido."""
    import heapq

    random.seed(7)
    W, H = nweeks, 7
    inside = lambda c: 0 <= c[0] < W and 0 <= c[1] < H
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    remaining = {c for c, lvl in grid.items() if lvl > 0}
    # entrada pela esquerda, na linha do meio
    path = [(-3, 3), (-2, 3), (-1, 3)]
    foods, eat_steps = [], []
    length = START_LEN

    def body_free_after(cell, dist):
        # celula ocupada pelo corpo so libera depois que a cauda passar
        n = len(path)
        for j in range(1, min(length, n) + 1):
            if path[n - j] == cell:
                return dist >= length - j + 1
        return True

    def plan(targets, ghost=False):
        head = path[-1]
        prev = path[-2]
        d0 = (head[0] - prev[0], head[1] - prev[1])
        pq = [(0.0, 0, head, d0)]
        seen = {}
        parent = {}
        while pq:
            cost, dist, cell, d = heapq.heappop(pq)
            if (cell, d) in seen:
                continue
            seen[(cell, d)] = cost
            if cell in targets and dist > 0:
                out = []
                key = (cell, d)
                while key in parent:
                    out.append(key[0])
                    key = parent[key]
                return out[::-1]
            for nd in dirs:
                if nd == (-d[0], -d[1]):
                    continue
                nc = (cell[0] + nd[0], cell[1] + nd[1])
                if not inside(nc) or (not ghost and not body_free_after(nc, dist + 1)):
                    continue
                turn = 0.35 if nd != d else 0.0          # prefere seguir reto
                jitter = random.random() * 0.15            # um pouco de "mao humana"
                ncost = cost + 1 + turn + jitter
                if (nc, nd) not in seen:
                    parent[(nc, nd)] = (cell, d)
                    heapq.heappush(pq, (ncost, dist + 1, nc, nd))
        return None

    guard = 0
    while remaining and guard < 5000:
        guard += 1
        route = plan(remaining)
        if not route:
            # encurralada: passa por cima do proprio corpo (como um jogador que arrisca)
            route = plan(remaining, ghost=True)
        if not route:
            break
        for c in route:
            path.append(c)
            if c in remaining:
                remaining.discard(c)
                foods.append(c)
                eat_steps.append(len(path) - 1)
                length += 1
                break

    # terminou: sai pela direita
    h = path[-1]
    while h[1] != 3:
        h = (h[0], h[1] + (1 if h[1] < 3 else -1)) if body_free_after((h[0], h[1] + (1 if h[1] < 3 else -1)), 1) else (h[0] + 1, h[1])
        path.append(h)
    for _ in range(W - h[0] + length + 2):
        h = (h[0] + 1, h[1])
        path.append(h)

    max_len = length
    n = len(path)
    dur = (n - 1) * STEP + PAUSE
    eat_times = [k * STEP for k in eat_steps]
    return path, foods, eat_times, max_len, dur, list(grid)


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
        size = 15 if i == 0 else max(14 - i * 0.12, 9)
        off = size / 2
        color = theme["head"] if i == 0 else theme["body"]
        seg = [f'<rect x="{-off:.1f}" y="{-off:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{size / 3.2:.1f}" fill="{color}" opacity="0">']
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
