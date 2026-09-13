"""图算法：BFS/DFS/拓扑排序/Dijkstra/并查集。

统一使用邻接表 dict[str, list[str | tuple[str, w]]] 表示。
"""

from __future__ import annotations

import heapq
from collections import deque


def bfs(graph: dict[str, list[str]], start: str) -> list[str]:
    """广度优先：无权图最短路径的唯一可靠解法（按层扩展）。"""
    visited, order = {start}, []
    q = deque([start])
    while q:
        node = q.popleft()
        order.append(node)
        for nxt in graph.get(node, []):
            if nxt not in visited:
                visited.add(nxt)
                q.append(nxt)
    return order


def dfs(graph: dict[str, list[str]], start: str) -> list[str]:
    """深度优先（显式栈，避免大图递归爆栈）。"""
    visited, order = set(), []
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for nxt in reversed(graph.get(node, [])):
            if nxt not in visited:
                stack.append(nxt)
    return order


def shortest_path_unweighted(graph: dict[str, list[str]],
                             start: str, goal: str) -> list[str] | None:
    """BFS 求无权最短路径（记录前驱回溯）。面试点：BFS 首次到达即最短。"""
    prev: dict[str, str | None] = {start: None}
    q = deque([start])
    while q:
        node = q.popleft()
        if node == goal:
            path = []
            while node is not None:
                path.append(node)
                node = prev[node]
            return path[::-1]
        for nxt in graph.get(node, []):
            if nxt not in prev:
                prev[nxt] = node
                q.append(nxt)
    return None


def topo_sort(graph: dict[str, list[str]]) -> list[str]:
    """拓扑排序（Kahn 入度法）。存在环时返回部分结果——可用来做环检测。"""
    indegree: dict[str, int] = {u: 0 for u in graph}
    for u, vs in graph.items():
        for v in vs:
            indegree.setdefault(v, 0)
            indegree[v] += 1
    q = deque(u for u, d in indegree.items() if d == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, []):
            indegree[v] -= 1
            if indegree[v] == 0:
                q.append(v)
    return order


def dijkstra(graph: dict[str, list[tuple[str, float]]],
             start: str) -> dict[str, float]:
    """Dijkstra：非负权最短路，堆优化 O((V+E) log V)。

    面试点：为什么不能有负权？——出堆即定案的贪心性质被破坏。
    """
    dist: dict[str, float] = {start: 0.0}
    heap: list[tuple[float, str]] = [(0.0, start)]
    done: set[str] = set()
    while heap:
        d, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


class UnionFind:
    """并查集：路径压缩 + 按秩合并，近似 O(α(n)) 每操作。

    应用：连通分量、Kruskal 最小生成树、朋友圈问题。
    """

    def __init__(self, items: list[str]):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}
        self.components = len(items)

    def find(self, x: str) -> str:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:             # 路径压缩
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> bool:
        """合并成功（原本不连通）返回 True。"""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        self.components -= 1
        return True

    def connected(self, a: str, b: str) -> bool:
        return self.find(a) == self.find(b)
