"""查找算法：二分及其边界变体、峰值查找。"""

from __future__ import annotations


def binary_search(a: list[int], target: int) -> int:
    """标准二分：返回 target 下标，不存在返回 -1。

    要点：闭区间 [lo, hi] 与 mid 偏移，防死循环的关键是区间每次真实缩小。
    """
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def binary_search_left(a: list[int], target: int) -> int:
    """左边界：第一个 >= target 的下标（即 bisect_left）。全小于 target 时返回 len(a)。

    应用：有序数组中统计 target 出现次数 = right(target) - left(target)。
    """
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def binary_search_right(a: list[int], target: int) -> int:
    """右边界：第一个 > target 的下标（即 bisect_right）。"""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def find_peak(a: list[int]) -> int:
    """山脉/峰值查找：返回任意一个峰值（大于左右邻居）的下标。

    相邻元素不等的前提下 O(log n)：比较 mid 与 mid+1，向更高的一侧收缩。
    """
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < a[mid + 1]:
            lo = mid + 1
        else:
            hi = mid
    return lo


def search_rotated(a: list[int], target: int) -> int:
    """旋转有序数组查找（LeetCode 33）：每次二分后至少一半是有序的，
    判断 target 是否落在有序半段内来决定收缩方向。"""
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == target:
            return mid
        if a[lo] <= a[mid]:                       # 左半有序
            if a[lo] <= target < a[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                                     # 右半有序
            if a[mid] < target <= a[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1
