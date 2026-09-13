"""算法模块全量正确性测试：与内置 sorted/标准实现对照。pytest -q"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algorithms"))

import pytest

from data_structures import (LRUCache, ListNode, MinStack, Trie, has_cycle,
                             middle_node, reverse_list)
from dynamic_programming import (climb_stairs, coin_change, edit_distance, fib,
                                 knapsack_01, lcs, lis,
                                 longest_palindrome_subseq)
from graph import UnionFind, bfs, dfs, dijkstra, shortest_path_unweighted, topo_sort
from searching import binary_search, binary_search_left, binary_search_right, \
    find_peak, search_rotated
from sorting import ALGORITHMS
from strings import (group_anagrams, kmp_search,
                     length_of_longest_substring, longest_palindrome)


@pytest.fixture(params=sorted(ALGORITHMS))
def sorter(request):
    return ALGORITHMS[request.param]


CASES = [
    [], [1], [2, 1], [5, 3, 8, 1, 9, 2], [3, 3, 1, 3],
    [9, 8, 7, 6, 5, 4, 3, 2, 1], [1, 2, 3, 4, 5], [-2, 5, 0, -7, 3, 3],
]


def test_sorting_matches_builtin(sorter):
    for case in CASES:
        assert sorter(case) == sorted(case)


# ---------------- searching ----------------
@pytest.fixture()
def sorted_arr():
    return [1, 3, 3, 3, 7, 9, 12]


def test_binary_search(sorted_arr):
    assert binary_search(sorted_arr, 7) == 4
    assert binary_search(sorted_arr, 1) == 0
    assert binary_search(sorted_arr, 5) == -1
    assert binary_search([], 3) == -1


def test_boundaries(sorted_arr):
    assert binary_search_left(sorted_arr, 3) == 1
    assert binary_search_right(sorted_arr, 3) == 4
    assert binary_search_right(sorted_arr, 3) - binary_search_left(sorted_arr, 3) == 3
    assert binary_search_left(sorted_arr, 100) == len(sorted_arr)


def test_find_peak_and_rotated():
    assert find_peak([1, 3, 8, 7, 2]) == 2
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 0) == 4
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 3) == -1


# ---------------- dp ----------------
def test_fib_and_climb():
    assert [fib(i) for i in range(7)] == [0, 1, 1, 2, 3, 5, 8]
    assert climb_stairs(4) == 5


def test_lis_lcs_edit():
    assert lis([10, 9, 2, 5, 3, 7, 101, 18]) == 4
    assert lcs("abcde", "ace") == 3
    assert edit_distance("horse", "ros") == 3
    assert edit_distance("", "abc") == 3


def test_knapsack_coin():
    assert knapsack_01([1, 3, 4], [15, 30, 20], 4) == 45   # 选 重量1+重量3
    assert knapsack_01([2], [10], 1) == 0
    assert coin_change([1, 2, 5], 11) == 3                 # 5+5+1
    assert coin_change([2], 3) == -1


def test_palindrome_subseq():
    assert longest_palindrome_subseq("bbbab") == 4
    assert longest_palindrome_subseq("cbbd") == 2


# ---------------- graph ----------------
GRAPH = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["E"], "E": []}


def test_bfs_dfs_order():
    assert bfs(GRAPH, "A") == ["A", "B", "C", "D", "E"]
    assert set(dfs(GRAPH, "A")) == {"A", "B", "C", "D", "E"}
    assert dfs(GRAPH, "A")[0] == "A"


def test_shortest_path():
    assert shortest_path_unweighted(GRAPH, "A", "E") == ["A", "B", "D", "E"]
    assert shortest_path_unweighted(GRAPH, "E", "A") is None


def test_topo_and_cycle():
    order = topo_sort({"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []})
    assert order.index("a") == 0 and order.index("d") == 3
    # 有环时 Kahn 算法无入度 0 的起点，返回空——这正是环检测方法
    assert topo_sort({"a": ["b"], "b": ["a"]}) == []


def test_dijkstra():
    g = {"A": [("B", 1), ("C", 4)], "B": [("C", 2), ("D", 5)],
         "C": [("D", 1)], "D": []}
    dist = dijkstra(g, "A")
    assert dist == {"A": 0.0, "B": 1.0, "C": 3.0, "D": 4.0}


def test_union_find():
    uf = UnionFind(["a", "b", "c", "d"])
    assert uf.union("a", "b") and uf.connected("a", "b")
    assert not uf.union("a", "b")
    assert uf.union("c", "d") and uf.components == 2
    assert not uf.connected("a", "c")


# ---------------- strings ----------------
def test_kmp():
    assert kmp_search("ababcababcabd", "ababcabd") == 5
    assert kmp_search("hello", "ll") == 2
    assert kmp_search("hello", "xyz") == -1
    assert kmp_search("abc", "") == 0


def test_palindrome_and_window():
    assert longest_palindrome("babad") in ("bab", "aba")
    assert longest_palindrome("cbbd") == "bb"
    assert length_of_longest_substring("abcabcbb") == 3
    assert length_of_longest_substring("pwwkew") == 3
    assert length_of_longest_substring("") == 0


def test_group_anagrams():
    groups = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert sorted(len(g) for g in groups) == [1, 2, 3]


# ---------------- data structures ----------------
def _build(values):
    head = None
    for v in reversed(values):
        head = ListNode(v, head)
    return head


def test_linked_list_ops():
    head = _build([1, 2, 3, 4])
    vals = []
    node = reverse_list(head)
    while node:
        vals.append(node.val)
        node = node.next
    assert vals == [4, 3, 2, 1]

    circle = ListNode(1)
    circle.next = ListNode(2, circle)
    assert has_cycle(circle)
    assert not has_cycle(_build([1, 2, 3]))

    assert middle_node(_build([1, 2, 3])).val == 2
    assert middle_node(_build([1, 2, 3, 4])).val == 3


def test_min_stack():
    ms = MinStack()
    for v in (3, 1, 2, 1):
        ms.push(v)
    assert ms.get_min() == 1
    assert ms.pop() == 1 and ms.get_min() == 1
    assert ms.pop() == 2 and ms.get_min() == 1
    assert ms.top() == 1


def test_lru_cache():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    c.put(3, 3)                       # 淘汰 key=2（最久未使用）
    assert c.get(2) == -1
    assert c.get(3) == 3


def test_trie():
    t = Trie()
    t.insert("apple")
    assert t.search("apple") and not t.search("app")
    assert t.starts_with("app")
    t.insert("app")
    assert t.search("app")
