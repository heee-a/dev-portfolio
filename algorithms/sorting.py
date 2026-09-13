"""排序算法合集：六种经典实现的思路与复杂度对比。

| 算法 | 平均 | 最坏 | 空间 | 稳定 |
|---|---|---|---|---|
| 冒泡 | O(n²) | O(n²) | O(1) | ✔ |
| 插入 | O(n²) | O(n²) | O(1) | ✔ |
| 选择 | O(n²) | O(n²) | O(1) | ✘ |
| 归并 | O(n log n) | O(n log n) | O(n) | ✔ |
| 快排 | O(n log n) | O(n²) | O(log n) | ✘ |
| 堆排 | O(n log n) | O(n log n) | O(1) | ✘ |
"""

from __future__ import annotations


def bubble_sort(a: list[int]) -> list[int]:
    """冒泡：相邻逆序则交换，每轮把最大值“冒”到末尾。

    提前终止优化：某一轮无交换说明已有序，O(n) 最好情况。
    """
    arr = list(a)
    for i in range(len(arr) - 1):
        swapped = False
        for j in range(len(arr) - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def insertion_sort(a: list[int]) -> list[int]:
    """插入：像整理扑克牌，把新元素插入左侧已排序区间的正确位置。

    近似有序的数据上接近 O(n)，是混合排序（如 Timsort）的组成部分。
    """
    arr = list(a)
    for i in range(1, len(arr)):
        key, j = arr[i], i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr


def selection_sort(a: list[int]) -> list[int]:
    """选择：每轮从未排序区选最小值，放到已排序区末尾。交换次数最少（≤n-1）。"""
    arr = list(a)
    for i in range(len(arr) - 1):
        m = min(range(i, len(arr)), key=lambda j: arr[j])
        arr[i], arr[m] = arr[m], arr[i]
    return arr


def merge_sort(a: list[int]) -> list[int]:
    """归并：分治，两半各自排序后线性合并。稳定、可外部排序，代价 O(n) 辅助空间。"""
    if len(a) <= 1:
        return list(a)
    mid = len(a) // 2
    left, right = merge_sort(a[:mid]), merge_sort(a[mid:])
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        out.append(left[i] if left[i] <= right[j] else right[j])  # <= 保证稳定
        i, j = (i + 1, j) if left[i] <= right[j] else (i, j + 1)
    out.extend(left[i:] or right[j:])
    return out


def quick_sort(a: list[int]) -> list[int]:
    """快排：选基准分区（小于/大于），递归两侧。

    经典面试点：最坏 O(n²) 出现在已排序 + 固定取首元素为基准时；
    这里取中间元素规避常见退化场景。原地版本（Lomuto/Hoare 分区）见面试追问题。
    """
    if len(a) <= 1:
        return list(a)
    pivot = a[len(a) // 2]
    lt = [x for x in a if x < pivot]
    eq = [x for x in a if x == pivot]
    gt = [x for x in a if x > pivot]
    return quick_sort(lt) + eq + quick_sort(gt)


def _sift(arr: list[int], start: int, end: int) -> None:
    """max-heap 下沉调整。"""
    root = start
    while (child := 2 * root + 1) < end:
        if child + 1 < end and arr[child + 1] > arr[child]:
            child += 1
        if arr[root] >= arr[child]:
            break
        arr[root], arr[child] = arr[child], arr[root]
        root = child


def heap_sort(a: list[int]) -> list[int]:
    """堆排：原地建 max-heap，反复取堆顶放到末尾。空间 O(1) 的 O(n log n)。"""
    arr = list(a)
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):          # 自底向上建堆 O(n)
        _sift(arr, i, n)
    for end in range(n - 1, 0, -1):
        arr[0], arr[end] = arr[end], arr[0]
        _sift(arr, 0, end)
    return arr


ALGORITHMS = {"bubble": bubble_sort, "insertion": insertion_sort,
              "selection": selection_sort, "merge": merge_sort,
              "quick": quick_sort, "heap": heap_sort}
