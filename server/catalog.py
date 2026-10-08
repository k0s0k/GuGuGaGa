from functools import lru_cache
from content.part1 import PROBLEMS as PART1
from content.part2 import PROBLEMS as PART2
from content.part3 import PROBLEMS as PART3
from .adapters import enrich

CATEGORY_ORDER = ["数组", "链表", "哈希表", "字符串", "双指针", "滑动窗口", "前缀和", "矩阵", "栈与队列", "二叉树", "回溯", "贪心", "动态规划", "二分查找", "单调栈", "单调队列", "堆", "图论", "技巧"]
PROBLEMS = [{**p, "category": "回溯" if p["category"] == "回溯算法" else p["category"]} for p in PART1 + PART2 + PART3]
BY_ID = {p["id"]: p for p in PROBLEMS}


def summaries():
    fields = ("id", "title", "slug", "difficulty", "category", "approach", "time", "space")
    return [{**{key: problem[key] for key in fields}, "order": i + 1} for i, problem in enumerate(PROBLEMS)]


@lru_cache(maxsize=100)
def detail(problem_id):
    if problem_id not in BY_ID:
        raise ValueError("题目不存在")
    return enrich(BY_ID[problem_id])
