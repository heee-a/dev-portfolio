"""手写数据结构：链表操作、最小栈、LRU 缓存、Trie。"""

from __future__ import annotations

from collections import OrderedDict


class ListNode:
    def __init__(self, val: int, nxt: "ListNode | None" = None):
        self.val = val
        self.next = nxt


def reverse_list(head: ListNode | None) -> ListNode | None:
    """反转单链表（迭代三指针）。面试点：递归版空间 O(n) 是追问坑。"""
    prev = None
    while head:
        head.next, prev, head = prev, head, head.next
    return prev


def has_cycle(head: ListNode | None) -> bool:
    """Floyd 快慢指针判环：慢走 1 快走 2，相遇即有环。O(1) 空间。"""
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow is fast:
            return True
    return False


def middle_node(head: ListNode | None) -> ListNode | None:
    """快慢指针找中点：快走 2 慢走 1，快指针到尾时慢指针在中点。"""
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
    return slow


class MinStack:
    """最小栈：push/pop/top 均 O(1)，get_min 也 O(1)。

    要点：辅助栈与主栈同步压入“当前最小值”，弹栈同步弹出。
    """

    def __init__(self) -> None:
        self._stack: list[int] = []
        self._mins: list[int] = []

    def push(self, val: int) -> None:
        self._stack.append(val)
        self._mins.append(min(val, self._mins[-1] if self._mins else val))

    def pop(self) -> int:
        self._mins.pop()
        return self._stack.pop()

    def top(self) -> int:
        return self._stack[-1]

    def get_min(self) -> int:
        return self._mins[-1]


class LRUCache:
    """LRU 缓存：OrderedDict 实现均 O(1)。

    面试加分：手写双向链表 + 哈希表版本，并说清 OrderedDict.move_to_end 的语义。
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._data: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self._data:
            return -1
        self._data.move_to_end(key)               # 访问即提升为最新
        return self._data[key]

    def put(self, key: int, value: int) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)        # 淘汰最久未使用


class Trie:
    """前缀树：词表检索/前缀匹配 O(单词长度)，输入联想的底层结构。"""

    def __init__(self) -> None:
        self.children: dict[str, "Trie"] = {}
        self.is_word = False

    def insert(self, word: str) -> None:
        node = self
        for ch in word:
            node = node.children.setdefault(ch, Trie())
        node.is_word = True

    def search(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def _walk(self, s: str) -> "Trie | None":
        node = self
        for ch in s:
            node = node.children.get(ch)
            if node is None:
                return None
        return node
