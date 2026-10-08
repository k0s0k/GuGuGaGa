"""原创 Hot 100 题解：栈、堆、贪心、动态规划与技巧。"""

PROBLEMS = []


def add(id, title, slug, difficulty, category, summary, constraints, examples,
        method, params, returns, python, cpp, approach, steps, correctness,
        pitfalls, time, space, **extra):
    PROBLEMS.append(dict(id=id, title=title, slug=slug, difficulty=difficulty,
                         category=category, summary=summary, constraints=constraints,
                         examples=[dict(input=i, output=o, explanation=e) for i, o, e in examples],
                         method=method, params=[dict(name=n, type=t) for n, t in params],
                         returns=returns, python=python.strip(), cpp=cpp.strip(),
                         approach=approach, steps=steps, correctness=correctness,
                         pitfalls=pitfalls, time=time, space=space, **extra))


add(146, 'LRU 缓存', 'lru-cache', '中等', '链表',
    '实现容量固定的缓存。get(key) 返回缓存值，不存在返回 -1；put(key, value) 写入或更新。当容量不足时，移除最久没有被读取或更新的键。两种操作均须达到平均 O(1)。',
    ['1 ≤ capacity ≤ 3000', '键和值均为非负整数', 'get 和 put 共至多调用 200000 次'],
    [([['LRUCache','put','put','get','put','get','get'], [[2],[1,1],[2,2],[1],[3,3],[2],[3]]], [None,None,None,1,None,-1,3], '读取键 1 后，键 2 成为最久未使用项，被键 3 挤出。'),
     ([['LRUCache','put','put','get','put','get','get'], [[1],[1,5],[1,7],[1],[2,8],[1],[2]]], [None,None,None,7,None,-1,8], '更新已有键不会额外占用容量；容量为 1 时新键替换旧键。')],
    '', [('operations','string[]'),('arguments','int[][]')], 'design',
    '''from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        # 左端最久未使用，右端最近使用。
        self.data = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        # 读取也算一次使用，要更新先后顺序。
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: int, value: int) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        # 只在超容量时删除左端的最旧项。
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
''',
    '''class LRUCache {
    int capacity;
    // 链表头是最近使用项，尾是最久未使用项。
    list<pair<int, int>> items;
    unordered_map<int, list<pair<int, int>>::iterator> positions;
public:
    LRUCache(int capacity) : capacity(capacity) {}
    int get(int key) {
        auto found = positions.find(key);
        if (found == positions.end()) return -1;
        // splice 移动结点，不复制结点，也不使迭代器失效。
        items.splice(items.begin(), items, found->second);
        return found->second->second;
    }
    void put(int key, int value) {
        auto found = positions.find(key);
        if (found != positions.end()) {
            found->second->second = value;
            items.splice(items.begin(), items, found->second);
            return;
        }
        items.emplace_front(key, value);
        positions[key] = items.begin();
        // 淘汰时必须同时移除哈希表和链表中的记录。
        if ((int)items.size() > capacity) {
            positions.erase(items.back().first);
            items.pop_back();
        }
    }
};''',
    '用哈希表定位结点，用双向链表维护使用顺序。Python 的 OrderedDict 已封装这种能力；C++ 显式组合 list 和 unordered_map。',
    ['读取或更新已有键时，将它移动到最近使用的一端。', '插入新键并记录它在链表中的位置。', '超过容量时删除另一端的最旧键。'],
    '每次有效访问都把对应键放到最近使用端，其余键之间的相对顺序不变，因此另一端始终是 LRU。哈希表与链表同步更新，保证每个缓存键只有一份记录。',
    ['get 也必须更新顺序。', '覆盖已有键不应误删其他键。', 'C++ 不要用线性查找链表的位置。'],
    'get / put 平均 O(1)', 'O(capacity)', special='design', className='LRUCache')

add(20, '有效的括号', 'valid-parentheses', '简单', '栈与队列',
    '给定只包含 ()[]{} 的字符串。判断每个右括号能否与最近尚未配对的同类型左括号匹配，且最终没有剩余左括号。',
    ['1 ≤ s.length ≤ 10000', 's 只包含六种括号字符'],
    [(['([]){}'], True, '括号类型正确，嵌套顺序也正确。'), (['([)]'], False, '右圆括号出现时，最近的左括号是方括号。'), (['('], False, '存在未闭合的左括号。')],
    'isValid', [('s','string')], 'bool',
    '''class Solution:
    def isValid(self, s: str) -> bool:
        pairs = {')': '(', ']': '[', '}': '{'}
        stack = []
        for char in s:
            # 左括号等待后续配对，按出现顺序入栈。
            if char not in pairs:
                stack.append(char)
            else:
                # 右括号只能匹配最近尚未闭合的左括号。
                if not stack or stack.pop() != pairs[char]:
                    return False
        # 剩余左括号也会导致匹配失败。
        return not stack''',
    '''class Solution {
public:
    bool isValid(string s) {
        string pending;
        for (char c : s) {
            // 将左括号对应的右括号压栈，直接记录期望值。
            if (c == '(') pending.push_back(')');
            else if (c == '[') pending.push_back(']');
            else if (c == '{') pending.push_back('}');
            else {
                // 当前右括号必须等于最近的期望值。
                if (pending.empty() || pending.back() != c) return false;
                pending.pop_back();
            }
        }
        // 栈空意味着所有左括号均已闭合。
        return pending.empty();
    }
};''',
    '用栈保存尚未闭合的括号，利用后进先出顺序处理嵌套。',
    ['遇到左括号入栈。', '遇到右括号时检查栈顶是否同类型，并弹出。', '遍历结束检查栈是否为空。'],
    '在任何合法匹配中，右括号必须闭合最近未匹配的左括号。栈准确维护这一位置；局部不匹配无法被后续字符修复，最后栈为空则所有括号恰好配对。',
    ['先判断栈空再访问栈顶。', '只统计各种括号数量无法检查嵌套顺序。'], 'O(n)', 'O(n)')

add(155, '最小栈', 'min-stack', '中等', '栈与队列',
    '设计一个支持 push、pop、top 和 getMin 的栈。getMin 返回当前所有元素中的最小值，所有操作均为 O(1)。',
    ['元素在 32 位有符号整数范围内', 'pop、top 和 getMin 仅在非空栈上调用'],
    [([['MinStack','push','push','push','getMin','pop','top','getMin'], [[],[-2],[0],[-3],[],[],[],[]]], [None,None,None,None,-3,None,0,-2], '弹出 -3 后最小值恢复为 -2。'),
     ([['MinStack','push','push','pop','getMin'], [[],[2],[2],[],[]]], [None,None,None,None,2], '重复的最小值也需要正确维护。')],
    '', [('operations','string[]'),('arguments','int[][]')], 'design',
    '''class MinStack:
    def __init__(self):
        # 每项记录元素，以及截至该项的前缀最小值。
        self.stack = []

    def push(self, val: int) -> None:
        minimum = min(val, self.stack[-1][1]) if self.stack else val
        self.stack.append((val, minimum))

    def pop(self) -> None:
        # 同时移除数值和这一步的最小值快照。
        self.stack.pop()

    def top(self) -> int:
        return self.stack[-1][0]

    def getMin(self) -> int:
        # 栈顶保存了整个当前栈的最小值。
        return self.stack[-1][1]''',
    '''class MinStack {
    // 每项保存数值和对应的前缀最小值。
    vector<pair<int, int>> items;
public:
    MinStack() {}
    void push(int val) {
        int minimum = items.empty() ? val : min(val, items.back().second);
        items.emplace_back(val, minimum);
    }
    void pop() {
        // 弹出后自动恢复上一层的最小值。
        items.pop_back();
    }
    int top() { return items.back().first; }
    int getMin() {
        // 无需扫描栈，直接读取快照。
        return items.back().second;
    }
};''',
    '入栈时同时保存当前最小值，让每一层栈都有自己的最小值快照。',
    ['新元素的快照为它自己与上一层最小值的较小者。', '弹栈时将元素与快照一起弹出。', 'top 读数值，getMin 读快照。'],
    '空栈压入第一个元素时快照正确。若已有栈顶快照正确，新快照取它与新值的最小值，也正确。弹出仅恢复之前已正确的快照，因此所有操作均保持正确。',
    ['不能仅保存一个全局最小值，否则最小值弹出时无法恢复。', '重复最小值需要保留。'], '所有查询和弹出 O(1)，动态数组压入均摊 O(1)', 'O(n)', special='design', className='MinStack')

add(394, '字符串解码', 'decode-string', '中等', '栈与队列',
    '字符串中的 k[片段] 表示把片段重复 k 次；片段可以继续嵌套编码。输入保证格式有效，返回完全展开后的字符串。原始文字均为小写字母，数字只用于重复次数。',
    ['1 ≤ s.length ≤ 30', '1 ≤ 重复次数 ≤ 300', '展开后的长度不超过 100000'],
    [(['3[a2[c]]'], 'accaccacc', '内层 2[c] 先展开为 cc，再将 acc 重复 3 次。'), (['12[a]b'], 'aaaaaaaaaaaab', '重复次数可能有多位数字。'), (['abc'], 'abc', '普通字符直接保留。')],
    'decodeString', [('s','string')], 'string',
    '''class Solution:
    def decodeString(self, s: str) -> str:
        # 所有字符写入同一个缓冲区，栈只记录片段起点与次数。
        output = []
        stack = []
        number = 0
        for char in s:
            if char.isdigit():
                number = number * 10 + int(char)
            elif char == '[':
                stack.append((len(output), number))
                number = 0
            elif char == ']':
                start, count = stack.pop()
                # 片段的第一份已经写好，只补上剩余的 count-1 份。
                if count > 1:
                    output.extend(output[start:] * (count - 1))
            else:
                output.append(char)
        # count 为 1 时不复制，避免深层单次嵌套的重复工作。
        return ''.join(output)''',
    '''class Solution {
public:
    string decodeString(string s) {
        // 栈保存片段在唯一输出缓冲区中的起点与重复次数。
        vector<pair<int, int>> pending;
        string output;
        int number = 0;
        for (char c : s) {
            if (isdigit(c)) number = number * 10 + c - '0';
            else if (c == '[') {
                pending.emplace_back(output.size(), number);
                number = 0;
            } else if (c == ']') {
                auto [start, count] = pending.back();
                pending.pop_back();
                // 第一份已经存在；只追加尚缺少的份数。
                if (count > 1) {
                    string segment = output.substr(start);
                    for (int copy = 1; copy < count; ++copy) output += segment;
                }
            } else output.push_back(c);
        }
        // 重复一次时不截取片段，所有复制工作都对应输出增长。
        return output;
    }
};''',
    '单个输出缓冲区配合栈。左括号记住片段起点，右括号时片段已解码完成，只需要追加剩余的重复份数。',
    ['连续读取数字；遇到左括号把当前输出长度与重复次数入栈。', '普通字母直接追加到输出。', '遇到右括号，取出片段起点，将该片段额外复制 count-1 次；count=1 时不复制。'],
    '栈与括号嵌套一一对应。遇到右括号时，内层都已展开，起点之后的内容就是该片段的一份完整解码；再追加 count-1 份便正确实现当前层。输出缓冲区只增长，每次片段复制的成本不超过本次新增输出的常数倍，所以总工作量为输入长度加输出长度。',
    ['重复次数不是单个字符。', '遇到左括号后要清空累计次数。', '输出长度可能远大于输入，复杂度应考虑展开长度。'],
    'O(n + L)，L 为解码后的输出长度', 'O(n + L)')

add(739, '每日温度', 'daily-temperatures', '中等', '单调栈',
    '给定每天的温度，计算每一天需要等待多少天才会出现更高温度。之后没有更高温度时填 0。',
    ['1 ≤ temperatures.length ≤ 100000', '30 ≤ temperatures[i] ≤ 100'],
    [([[73,74,75,71,69,72,76,73]], [1,1,4,2,1,1,0,0], '第 3 天的 75 度要等 4 天才能遇到 76 度。'), ([[70,70,69]], [0,0,0], '相等温度不算更高。')],
    'dailyTemperatures', [('temperatures','int[]')], 'int[]',
    '''class Solution:
    def dailyTemperatures(self, temperatures: list[int]) -> list[int]:
        answer = [0] * len(temperatures)
        # 保存尚未找到更高温度的下标，温度从栈底到栈顶不增。
        pending = []
        for day, temperature in enumerate(temperatures):
            while pending and temperatures[pending[-1]] < temperature:
                previous = pending.pop()
                # 当前天是该下标右侧第一个更热的日子。
                answer[previous] = day - previous
            pending.append(day)
        # 留在栈里的日期没有答案，保持默认值 0。
        return answer''',
    '''class Solution {
public:
    vector<int> dailyTemperatures(vector<int>& temperatures) {
        vector<int> answer(temperatures.size(), 0), pending;
        // 栈中只存下标，方便计算等待天数。
        for (int day = 0; day < (int)temperatures.size(); ++day) {
            while (!pending.empty() && temperatures[pending.back()] < temperatures[day]) {
                int previous = pending.back();
                pending.pop_back();
                // 从左到右第一次遇到更高温度时确定答案。
                answer[previous] = day - previous;
            }
            pending.push_back(day);
        }
        // 没被弹出的下标保持 0。
        return answer;
    }
};''',
    '维护温度单调不增的下标栈；一个更高温度可以同时解决多天的等待问题。',
    ['初始化答案为 0。', '当前温度比栈顶高时，弹出栈顶并记录下标差。', '将当前下标入栈。'],
    '栈中的天数此前都未遇到更高温度。当前温度首次使某个栈顶出栈时，它就是该天下一个更高温度；等温不会出栈，所以严格更高的要求也被满足。',
    ['使用严格小于，不能把相同温度算作升温。', '栈存下标而非仅存温度。'], 'O(n)', 'O(n)')

add(84, '柱状图中最大的矩形', 'largest-rectangle-in-histogram', '困难', '单调栈',
    '柱状图每根柱子的宽度均为 1，高度由 heights 给出。选择连续若干根柱子，在它们覆盖的区域中找出最大矩形面积。',
    ['1 ≤ heights.length ≤ 100000', '0 ≤ heights[i] ≤ 10000'],
    [([[2,1,5,6,2,3]], 10, '选择高度 5、6 的两根柱子，矩形高度取 5，面积为 10。'), ([[2,2]], 4, '相邻等高柱子可以组成宽度为 2 的矩形。'), ([[0]], 0, '零高度没有正面积。')],
    'largestRectangleArea', [('heights','int[]')], 'int',
    '''class Solution:
    def largestRectangleArea(self, heights: list[int]) -> int:
        stack = []
        answer = 0
        for right in range(len(heights) + 1):
            # 最后的虚拟高度 -1 用来结算所有剩余柱子。
            height = heights[right] if right < len(heights) else -1
            while stack and heights[stack[-1]] >= height:
                middle = stack.pop()
                left = stack[-1] if stack else -1
                # middle 的高度可覆盖开区间 (left, right)。
                answer = max(answer, heights[middle] * (right - left - 1))
            if right < len(heights):
                # 等高项先弹出，使栈中高度严格递增。
                stack.append(right)
        return answer''',
    '''class Solution {
public:
    int largestRectangleArea(vector<int>& heights) {
        vector<int> pending;
        int answer = 0, n = heights.size();
        for (int right = 0; right <= n; ++right) {
            // 虚拟的 -1 高度触发最后一次清栈。
            int height = right == n ? -1 : heights[right];
            while (!pending.empty() && heights[pending.back()] >= height) {
                int middle = pending.back();
                pending.pop_back();
                int left = pending.empty() ? -1 : pending.back();
                // 左右边界不包含在矩形中，宽度需减 1。
                answer = max(answer, heights[middle] * (right - left - 1));
            }
            // 只保存真实下标，避免访问越界的哨兵。
            if (right < n) pending.push_back(right);
        }
        return answer;
    }
};''',
    '递增栈为每种候选高度寻找左右扩展范围。遇到不更高的柱子，就结算栈顶高度对应的面积。',
    ['下标入栈前，弹出所有高度大于等于当前高度的项。', '弹出后栈顶是左边界，当前下标是右边界，计算面积。', '末尾用虚拟负高度清空栈。'],
    '每个最优矩形的高度可取覆盖柱子的最小高度。该高度出栈时会评估它能覆盖的连续范围；等高项提前结算后，后面的等高项仍保留更宽范围的机会。因此最大面积不会遗漏。',
    ['宽度是 right - left - 1。', '必须处理遍历结束后仍在栈中的柱子。', '相同高度的处理规则要保持一致。'], 'O(n)', 'O(n)')

add(215, '数组中的第 K 个最大元素', 'kth-largest-element-in-an-array', '中等', '堆',
    '返回数组按从大到小排序后的第 k 个元素。重复元素分别计数，不要求返回不同值中的第 k 大。',
    ['1 ≤ k ≤ nums.length ≤ 100000', '-10000 ≤ nums[i] ≤ 10000'],
    [([[3,2,1,5,6,4],2], 5, '从大到小第二个值为 5。'), ([[3,2,3,1,2,4,5,5,6],4], 4, '重复的 5 占据两个排名。'), ([[7,7,7],2], 7, '所有数相同时直接命中等值区间。')],
    'findKthLargest', [('nums','int[]'),('k','int')], 'int',
    '''import random

class Solution:
    def findKthLargest(self, nums: list[int], k: int) -> int:
        target = len(nums) - k
        left, right = 0, len(nums) - 1
        while True:
            # 随机枢轴降低有序输入造成极端划分的风险。
            pivot = nums[random.randint(left, right)]
            smaller, index, greater = left, left, right
            while index <= greater:
                # 三路划分：小于、等于、大于枢轴。
                if nums[index] < pivot:
                    nums[smaller], nums[index] = nums[index], nums[smaller]
                    smaller += 1
                    index += 1
                elif nums[index] > pivot:
                    nums[index], nums[greater] = nums[greater], nums[index]
                    greater -= 1
                else:
                    index += 1
            # 只保留包含目标排名的一段。
            if target < smaller:
                right = smaller - 1
            elif target > greater:
                left = greater + 1
            else:
                return pivot''',
    '''class Solution {
public:
    int findKthLargest(vector<int>& nums, int k) {
        int target = (int)nums.size() - k;
        int left = 0, right = (int)nums.size() - 1;
        mt19937 generator(random_device{}());
        while (true) {
            // 随机选枢轴，避免固定端点对有序输入的偏置。
            int pivot = nums[uniform_int_distribution<int>(left, right)(generator)];
            int smaller = left, index = left, greater = right;
            while (index <= greater) {
                // 大数换到右侧后，新换来的数还需继续检查。
                if (nums[index] < pivot) swap(nums[smaller++], nums[index++]);
                else if (nums[index] > pivot) swap(nums[index], nums[greater--]);
                else ++index;
            }
            // 目标落入等值区间时可以立即返回。
            if (target < smaller) right = smaller - 1;
            else if (target > greater) left = greater + 1;
            else return pivot;
        }
    }
};''',
    '随机三路快速选择，只处理目标排名所在的一侧。等于枢轴的值聚在一起，使重复值很多时仍能快速收缩。',
    ['将第 k 大转换成升序下标 n-k。', '随机选值，把区间分成小于、等于、大于三段。', '根据目标下标缩小区间，命中中段时返回。'],
    '划分后，左段所有值小于枢轴，右段所有值大于枢轴，因此中段占据的排名已经确定。若目标不在中段，另一侧所有值都不可能位于目标排名，丢弃它不会改变答案。',
    ['第 k 大对应升序下标 n-k。', '交换右侧大数后不要立即递增 index。', '该算法会重排输入数组。'], '期望 O(n)，最坏 O(n²)', 'O(1)')

add(347, '前 K 个高频元素', 'top-k-frequent-elements', '中等', '堆',
    '找出数组中出现次数最多的 k 个不同元素。保证答案集合唯一，返回顺序不限。',
    ['1 ≤ nums.length ≤ 100000', '1 ≤ k ≤ 不同元素的数量', '出现频率前 k 名的集合唯一'],
    [([[1,1,1,2,2,3],2], [1,2], '1 和 2 的频率分别为 3 和 2。'), ([[4],1], [4], '仅一个元素。'), ([[-1,-1,2,2,2,3],1], [2], '可包含负数。')],
    'topKFrequent', [('nums','int[]'),('k','int')], 'int[]',
    '''from collections import Counter

class Solution:
    def topKFrequent(self, nums: list[int], k: int) -> list[int]:
        counts = Counter(nums)
        # 频率最大为 n，直接作为桶下标。
        buckets = [[] for _ in range(len(nums) + 1)]
        for value, count in counts.items():
            buckets[count].append(value)
        answer = []
        # 从高频桶向低频桶收集，不必给所有元素排序。
        for count in range(len(nums), 0, -1):
            for value in buckets[count]:
                answer.append(value)
                # 返回 k 个即可，题目保证边界处答案唯一。
                if len(answer) == k:
                    return answer
        return answer''',
    '''class Solution {
public:
    vector<int> topKFrequent(vector<int>& nums, int k) {
        unordered_map<int, int> counts;
        for (int value : nums) ++counts[value];
        // 第 f 个桶保存所有恰好出现 f 次的值。
        vector<vector<int>> buckets(nums.size() + 1);
        for (auto [value, count] : counts) buckets[count].push_back(value);
        vector<int> answer;
        // 降序遍历频率就等价于按出现次数选取。
        for (int count = nums.size(); count >= 1; --count) {
            for (int value : buckets[count]) {
                answer.push_back(value);
                // 不同值只进入一个桶，不会重复返回。
                if ((int)answer.size() == k) return answer;
            }
        }
        return answer;
    }
};''',
    '频率不超过数组长度，用桶排序的思路直接按频率分类，再从大到小取 k 个。',
    ['哈希表统计各值的出现次数。', '将各值放进对应频率的桶。', '倒序扫描桶并收集 k 个值。'],
    '每个不同元素恰好位于代表其频率的桶中。按桶下标递减访问时，后访问的元素频率不会超过先访问的元素，因此前 k 个即为所求集合。',
    ['需要的是高频元素，不是出现次数本身。', '结果顺序不限，不要额外排序增加复杂度。'], '平均 O(n)', 'O(n)', compare='unordered')

add(295, '数据流的中位数', 'find-median-from-data-stream', '困难', '堆',
    '不断向数据流加入整数。随时查询所有已加入数的中位数：奇数个时取排序后中间的值，偶数个时取中间两值的平均数。',
    ['-100000 ≤ num ≤ 100000', '查询时至少已有一个数', '至多调用 50000 次'],
    [([['MedianFinder','addNum','addNum','findMedian','addNum','findMedian'], [[],[1],[2],[],[3],[]]], [None,None,None,1.5,None,2.0], '前两个数的平均值为 1.5，加入 3 后中位数为 2。'),
     ([['MedianFinder','addNum','addNum','findMedian'], [[],[-1],[-1],[]]], [None,None,None,-1.0], '负数与重复值正常处理。')],
    '', [('operations','string[]'),('arguments','int[][]')], 'design',
    '''import heapq

class MedianFinder:
    def __init__(self):
        # lower 用相反数模拟大顶堆，保存较小的一半。
        self.lower = []
        self.upper = []

    def addNum(self, num: int) -> None:
        heapq.heappush(self.lower, -num)
        # 较小半区的最大值转移到较大半区，维持大小顺序。
        heapq.heappush(self.upper, -heapq.heappop(self.lower))
        if len(self.upper) > len(self.lower):
            heapq.heappush(self.lower, -heapq.heappop(self.upper))

    def findMedian(self) -> float:
        # lower 与 upper 等长，或 lower 恰好多一个。
        if len(self.lower) > len(self.upper):
            return float(-self.lower[0])
        return (-self.lower[0] + self.upper[0]) / 2''',
    '''class MedianFinder {
    // 大顶堆存较小的一半，小顶堆存较大的一半。
    priority_queue<int> lower;
    priority_queue<int, vector<int>, greater<int>> upper;
public:
    MedianFinder() {}
    void addNum(int num) {
        lower.push(num);
        // 搬移分界元素以保证 lower 中的数不大于 upper 中的数。
        upper.push(lower.top());
        lower.pop();
        if (upper.size() > lower.size()) {
            lower.push(upper.top());
            upper.pop();
        }
    }
    double findMedian() {
        // 奇数个时，额外的一个元素固定放在 lower。
        if (lower.size() > upper.size()) return lower.top();
        return ((double)lower.top() + upper.top()) / 2.0;
    }
};''',
    '双堆分别保存较小和较大的一半。堆顶正好位于中位数分界线上。',
    ['把新值放入小半区，再将该半区最大值移到大半区。', '若大半区数量更多，将其最小值移回。', '根据总数奇偶读取一个堆顶或两个堆顶的平均值。'],
    '插入和搬移始终保持 lower 的任意元素不大于 upper 的任意元素；数量调整保证 lower 等长或多一个。因此奇数时 lower 堆顶为正中元素，偶数时两堆顶就是中间两项。',
    ['Python 的大顶堆需取负号，弹出时再取回。', 'C++ 求平均值时要避免整数除法。'], '加入 O(log n)，查询 O(1)', 'O(n)', special='design', className='MedianFinder')

add(121, '买卖股票的最佳时机', 'best-time-to-buy-and-sell-stock', '简单', '贪心',
    'prices[i] 是第 i 天的股价。最多进行一次买入和一次卖出，且买入必须早于卖出。返回能获得的最大利润，也可以不交易并获得 0。',
    ['1 ≤ prices.length ≤ 100000', '0 ≤ prices[i] ≤ 10000'],
    [([[7,1,5,3,6,4]], 5, '价格为 1 时买入，价格为 6 时卖出。'), ([[7,6,4,3,1]], 0, '持续下跌时选择不交易。'), ([[3]], 0, '只有一天不能完成交易。')],
    'maxProfit', [('prices','int[]')], 'int',
    '''class Solution:
    def maxProfit(self, prices: list[int]) -> int:
        lowest = prices[0]
        answer = 0
        for i in range(1, len(prices)):
            price = prices[i]
            # 如果今天卖出，最好的买入价是此前最低价。
            answer = max(answer, price - lowest)
            # 再将今天纳入历史，供后面的卖出日使用。
            lowest = min(lowest, price)
        # 利润初值为 0，自动包含不交易的选择。
        return answer''',
    '''class Solution {
public:
    int maxProfit(vector<int>& prices) {
        int lowest = prices[0], answer = 0;
        for (int i = 1; i < (int)prices.size(); ++i) {
            // 今天卖出时只能使用之前的最低买价。
            answer = max(answer, prices[i] - lowest);
            // 更新历史最低价，留给下一天使用。
            lowest = min(lowest, prices[i]);
        }
        // 没有正收益时保留不交易的 0。
        return answer;
    }
};''',
    '从左向右枚举卖出日，同时维护此前最低买入价。',
    ['最低价初始化为第一天。', '每天先尝试按历史最低价买入、今天卖出。', '再更新最低价。'],
    '对于固定卖出日，最低的合法历史买价一定产生最大利润。算法遍历全部卖出日，取这些最优利润的最大值，覆盖了所有可能的最优交易。',
    ['不能直接取全局最高价减最低价，买卖先后顺序可能不合法。', '下跌时返回 0。'], 'O(n)', 'O(1)')

add(55, '跳跃游戏', 'jump-game', '中等', '贪心',
    '你从数组下标 0 出发，nums[i] 表示在位置 i 最多向右跳多少格。判断是否能到达最后一个下标。',
    ['1 ≤ nums.length ≤ 10000', '0 ≤ nums[i] ≤ 100000'],
    [([[2,3,1,1,4]], True, '可从下标 0 跳到 1，再跳到末尾。'), ([[3,2,1,0,4]], False, '所有可达路线都无法越过下标 3。'), ([[0]], True, '起点已经是终点。')],
    'canJump', [('nums','int[]')], 'bool',
    '''class Solution:
    def canJump(self, nums: list[int]) -> bool:
        farthest = 0
        for index, jump in enumerate(nums):
            # 扫描到覆盖范围外，说明此前所有位置都无法到达这里。
            if index > farthest:
                return False
            # 当前位置可达，可以用它扩展覆盖范围。
            farthest = max(farthest, index + jump)
            if farthest >= len(nums) - 1:
                return True
        # 非空数组会在上述成功或失败分支返回。
        return True''',
    '''class Solution {
public:
    bool canJump(vector<int>& nums) {
        int farthest = 0;
        for (int i = 0; i < (int)nums.size(); ++i) {
            // 超出已有覆盖范围的位置不可用来继续跳跃。
            if (i > farthest) return false;
            // 合并所有可达位置提供的向右覆盖范围。
            farthest = max(farthest, i + nums[i]);
            // 一旦覆盖终点，便无需继续扫描。
            if (farthest >= (int)nums.size() - 1) return true;
        }
        return true;
    }
};''',
    '只维护当前可达的最远位置。能够跳到远处也意味着可以选择落在中间任意位置，所以可达区间连续。',
    ['从下标 0 开始扫描。', '若当前下标超出最远可达范围，返回 false。', '否则扩展范围，覆盖末尾时返回 true。'],
    '归纳维护区间 [0, farthest] 中所有位置均可达。扫描可达位置时，它新增的跳跃区间与旧区间相接，更新后仍连续可达；扫描到范围外则不存在更早的可达位置能跨过缺口。',
    ['最大跳跃长度允许少跳，不必每次跳满。', '只有一个元素时，无需跳跃。'], 'O(n)', 'O(1)')

add(45, '跳跃游戏 II', 'jump-game-ii', '中等', '贪心',
    '从下标 0 出发，nums[i] 是该位置允许的最大向右跳跃距离。保证能够到达末尾，返回所需的最少跳跃次数。',
    ['1 ≤ nums.length ≤ 10000', '0 ≤ nums[i] ≤ 1000', '保证末尾可达'],
    [([[2,3,1,1,4]], 2, '先到下标 1，再到下标 4。'), ([[0]], 0, '已经到达末尾。'), ([[1,1,1]], 2, '每次只能前进一步。')],
    'jump', [('nums','int[]')], 'int',
    '''class Solution:
    def jump(self, nums: list[int]) -> int:
        jumps = 0
        end = 0
        farthest = 0
        # 不扫描末尾，避免到达后再多计一次跳跃。
        for index in range(len(nums) - 1):
            farthest = max(farthest, index + nums[index])
            if index == end:
                # 当前跳数覆盖的范围已扫描完，必须进入下一层。
                jumps += 1
                end = farthest
                # 下一层最远范围已包含终点，可立即返回。
                if end >= len(nums) - 1:
                    return jumps
        return jumps''',
    '''class Solution {
public:
    int jump(vector<int>& nums) {
        int jumps = 0, end = 0, farthest = 0;
        // 末尾不需要发起跳跃。
        for (int i = 0; i < (int)nums.size() - 1; ++i) {
            farthest = max(farthest, i + nums[i]);
            if (i == end) {
                // 一次性合并本层所有位置能覆盖的下一层。
                ++jumps;
                end = farthest;
                // 首次覆盖终点的层数就是最少跳数。
                if (end >= (int)nums.size() - 1) break;
            }
        }
        return jumps;
    }
};''',
    '把相同跳数可覆盖的范围看成一层。扫描完一层后，进入由这一层共同扩展出的下一层。',
    ['end 标记当前层最右端。', '扫描本层时累计下一层最右端 farthest。', '扫描至 end 时跳数加一并更新边界。'],
    '0 次跳跃只覆盖起点；某层中所有位置再跳一次能覆盖的并集正是下一层范围。因此逐层扩展等价于广度优先搜索，首次覆盖终点时得到最少跳数。',
    ['不要遍历到最后一个下标再加一次跳数。', '该题保证可达，不能直接把此算法用于任意不可达输入。'], 'O(n)', 'O(1)')

add(763, '划分字母区间', 'partition-labels', '中等', '贪心',
    '将小写字母字符串切成尽可能多的连续片段，要求每个字母最多出现在一个片段中。返回各片段长度。',
    ['1 ≤ s.length ≤ 500', '仅包含小写英文字母'],
    [(['ababcbacadefegdehijhklij'], [9,7,8], '前三段分别覆盖各自所有字母的出现位置。'), (['aaaa'], [4], '重复字母不能分在不同片段。'), (['abc'], [1,1,1], '每个字符都能单独成段。')],
    'partitionLabels', [('s','string')], 'int[]',
    '''class Solution:
    def partitionLabels(self, s: str) -> list[int]:
        # 一个字母所在片段必须覆盖它的最后一次出现。
        last = {char: index for index, char in enumerate(s)}
        answer = []
        start = end = 0
        for index, char in enumerate(s):
            end = max(end, last[char])
            # 扫描至所有已见字母的最晚位置，当前片段可以结束。
            if index == end:
                answer.append(end - start + 1)
                start = index + 1
        # 总在最早合法边界切分，片段数最多。
        return answer''',
    '''class Solution {
public:
    vector<int> partitionLabels(string s) {
        // 字母表固定为 26 个，用数组记录最后下标。
        vector<int> last(26, -1);
        for (int i = 0; i < (int)s.size(); ++i) last[s[i] - 'a'] = i;
        vector<int> answer;
        int start = 0, end = 0;
        for (int i = 0; i < (int)s.size(); ++i) {
            // 扩展到当前片段所有字母必须覆盖的最远位置。
            end = max(end, last[s[i] - 'a']);
            if (i == end) {
                // 到达最早合法切点，立即分段。
                answer.push_back(end - start + 1);
                start = i + 1;
            }
        }
        return answer;
    }
};''',
    '先记录每个字母的最后位置，再贪心选择最早合法切分点。',
    ['统计每个字母的最后下标。', '扫描片段，持续扩展它必须到达的右边界。', '当前位置等于边界时输出长度，并开启下一段。'],
    '边界之前切分会把某个已出现字母的后续出现分到另一段，因此不合法。到达边界后已出现字母都不会再出现，立即切分合法且不会减少后续可分段数量，所以最早切分可取得最多段。',
    ['长度需要加 1。', '边界需取最大值，不能直接覆盖为当前字母的最后位置。'], 'O(n)', 'O(1)，不计输出；字母表固定为 26')

add(70, '爬楼梯', 'climbing-stairs', '简单', '动态规划',
    '楼梯有 n 级，每次可以走 1 级或 2 级。计算从地面恰好走到第 n 级的不同步长序列数量。',
    ['1 ≤ n ≤ 45'],
    [([3], 3, '步长序列为 1+1+1、1+2、2+1。'), ([1], 1, '只有一步走 1 级。'), ([45], 1836311903, '快速倍增只需处理 n 的二进制位数次。')],
    'climbStairs', [('n','int')], 'int',
    '''class Solution:
    def climbStairs(self, n: int) -> int:
        # 台阶方案数为 F(n+1)，维护相邻斐波那契数 F(k)、F(k+1)。
        first, second = 0, 1
        bit = 1 << (n.bit_length() - 1)
        while bit:
            # 快速倍增恒等式：F(2k)、F(2k+1)。
            even = first * (2 * second - first)
            odd = first * first + second * second
            # 读入一位，相当于把下标变为 2k 或 2k+1。
            if n & bit:
                first, second = odd, even + odd
            else:
                first, second = even, odd
            bit >>= 1
        return second''',
    '''class Solution {
public:
    int climbStairs(int n) {
        // 一对数始终表示 F(k)、F(k+1)。
        long long first = 0, second = 1;
        int bit = 1;
        while (bit <= n / 2) bit <<= 1;
        while (bit > 0) {
            // 用倍增公式一次把下标翻倍。
            long long even = first * (2 * second - first);
            long long odd = first * first + second * second;
            if (n & bit) {
                first = odd;
                second = even + odd;
            } else {
                first = even;
                second = odd;
            }
            // 从最高位到最低位处理 n，最终需要 F(n+1)。
            bit >>= 1;
        }
        return (int)second;
    }
};''',
    '最后一步来自 n-1 或 n-2 级，所以方案数是 F(n+1)。利用斐波那契的快速倍增公式，将线性递推加速为对数次运算。',
    ['定义 F(0)=0、F(1)=1，则 n 级楼梯的方案数是 F(n+1)。', '维护 F(k)、F(k+1)，计算 F(2k)=F(k)·(2F(k+1)-F(k)) 和 F(2k+1)=F(k)²+F(k+1)²。', '从高位读取 n 的二进制位，将 k 更新为 2k 或 2k+1；最后返回第二个数。'],
    '最后一步分类得到楼梯递推，与 F(n+1) 初值一致。倍增公式由斐波那契加法公式推导而来；每次按二进制前缀更新后，数对仍对应相邻斐波那契数，读完 n 后第二项恰为 F(n+1)。',
    ['返回 F(n+1)，不是 F(n)。', 'C++ 中间乘法使用 long long。', '复杂度按本题固定范围内的整数运算计；任意精度大整数另有位运算成本。'], 'O(log n)', 'O(1)')

add(118, '杨辉三角', 'pascals-triangle', '简单', '动态规划',
    '生成杨辉三角的前 numRows 行。每行两端都是 1，内部每个数等于上一行左上方与右上方两个数之和。',
    ['1 ≤ numRows ≤ 30'],
    [([5], [[1],[1,1],[1,2,1],[1,3,3,1],[1,4,6,4,1]], '每一行依赖前一行。'), ([1], [[1]], '只有顶端的一个 1。')],
    'generate', [('numRows','int')], 'int[][]',
    '''class Solution:
    def generate(self, numRows: int) -> list[list[int]]:
        answer = []
        for row_index in range(numRows):
            # 先将本行所有位置置为 1，自动处理两端。
            row = [1] * (row_index + 1)
            for column in range(1, row_index):
                # 内部元素来自上一行的两个相邻元素。
                row[column] = answer[-1][column - 1] + answer[-1][column]
            # 每行是独立列表，避免行之间共享存储。
            answer.append(row)
        return answer''',
    '''class Solution {
public:
    vector<vector<int>> generate(int numRows) {
        vector<vector<int>> answer;
        for (int i = 0; i < numRows; ++i) {
            // 两端默认为 1。
            vector<int> row(i + 1, 1);
            for (int j = 1; j < i; ++j) {
                // 用已经构造好的上一行计算内部位置。
                row[j] = answer.back()[j - 1] + answer.back()[j];
            }
            // 本行完成后再加入结果，保持上一行含义清晰。
            answer.push_back(row);
        }
        return answer;
    }
};''',
    '按照定义逐行构造，结果本身作为后续计算所需的状态。',
    ['第 i 行创建 i+1 个 1。', '内部位置由上一行两个相邻数相加得到。', '将本行加入结果。'],
    '第一行正确。若上一行正确，本行两端按定义为 1，内部均按杨辉三角规则计算，因此整行正确。逐行归纳得到所有结果。',
    ['行下标从 0 开始时，第 i 行长度为 i+1。', '不要更新两端的 1。'], 'O(numRows²)，与输出规模相同', 'O(numRows²) 输出空间，构造单行额外 O(numRows)')

add(198, '打家劫舍', 'house-robber', '中等', '动态规划',
    '一排房屋分别有 nums[i] 金额。不能同时选择相邻两间房，求可获得的最大总金额。',
    ['1 ≤ nums.length ≤ 100', '0 ≤ nums[i] ≤ 400'],
    [([[2,7,9,3,1]], 12, '选择下标 0、2、4，金额为 2+9+1。'), ([[2,1,1,2]], 4, '选择首尾两间。'), ([[0]], 0, '金额可以为 0。')],
    'rob', [('nums','int[]')], 'int',
    '''class Solution:
    def rob(self, nums: list[int]) -> int:
        # before_previous、previous 分别对应前 i-2 和前 i-1 间的最优值。
        before_previous = previous = 0
        for money in nums:
            # 选择本间就不能选择上一间；不选本间则沿用之前最优值。
            current = max(previous, before_previous + money)
            before_previous, previous = previous, current
        # 状态只依赖前两项，无需保存整张表。
        return previous''',
    '''class Solution {
public:
    int rob(vector<int>& nums) {
        // 两个变量分别表示前两个前缀的最优收益。
        int beforePrevious = 0, previous = 0;
        for (int money : nums) {
            // 选本间或不选本间，取较大收益。
            int current = max(previous, beforePrevious + money);
            beforePrevious = previous;
            previous = current;
        }
        // 最后一个前缀就是整个数组。
        return previous;
    }
};''',
    '按是否选择当前房间分类，用两个变量滚动保存最优值。',
    ['空前缀收益为 0。', '当前最优值=max(前一间最优值, 前两间最优值+当前金额)。', '滚动更新两个前缀状态。'],
    '任何合法最优方案要么不选当前房间，收益来自前一前缀；要么选当前房间，必须跳过上一间，剩余来自前两间。两类覆盖全部可能，取最大即正确。',
    ['更新 previous 前先保存旧值。', '局部选择较大的相邻金额并不保证全局最优。'], 'O(n)', 'O(1)')

add(279, '完全平方数', 'perfect-squares', '中等', '动态规划',
    '给定正整数 n，允许重复使用 1、4、9、16 等完全平方数。返回凑出 n 所需的最少项数。',
    ['1 ≤ n ≤ 10000'],
    [([12], 3, '12=4+4+4。'), ([13], 2, '13=4+9。'), ([7], 4, '7=4+1+1+1，无法用三项表示。'), ([1], 1, '1 本身就是平方数。')],
    'numSquares', [('n','int')], 'int',
    '''from math import isqrt

class Solution:
    def numSquares(self, n: int) -> int:
        # 先判断答案是否为 1。
        if isqrt(n) ** 2 == n:
            return 1
        reduced = n
        while reduced % 4 == 0:
            reduced //= 4
        # 三平方定理：4^a(8b+7) 形式恰好需要 4 项。
        if reduced % 8 == 7:
            return 4
        for first in range(1, isqrt(n) + 1):
            remaining = n - first * first
            if isqrt(remaining) ** 2 == remaining:
                return 2
        # 排除 1、2、4 后，只可能是 3。
        return 3''',
    '''class Solution {
    bool isSquare(int value) {
        int root = (int)sqrt(value);
        return root * root == value;
    }
public:
    int numSquares(int n) {
        // 自身是平方数时，一项即达到最小值。
        if (isSquare(n)) return 1;
        int reduced = n;
        while (reduced % 4 == 0) reduced /= 4;
        // 三平方定理给出了不能由三项表示的完整判据。
        if (reduced % 8 == 7) return 4;
        for (int first = 1; first * first <= n; ++first) {
            if (isSquare(n - first * first)) return 2;
        }
        // 四平方定理保证答案不超过 4，剩余情况只能为 3。
        return 3;
    }
};''',
    '用四平方定理限定答案为 1 到 4，再用三平方定理判定 4，枚举一个平方数判定 2。此题归入动态规划学习组，但采用渐进复杂度更好的数论解法。',
    ['若 n 是完全平方数，返回 1。', '不断除去因子 4，若剩余数模 8 等于 7，返回 4。', '枚举第一个平方数，检查余数是否也是平方数；成功返回 2，否则返回 3。'],
    '拉格朗日四平方定理保证任意正整数最多用四项表示。勒让德三平方定理指出，仅 4^a(8b+7) 不能用三个平方数表示，因此这类数答案为 4。其他数至多需要 3 项；直接检查 1 项及穷举 2 项后，剩余答案必为 3。',
    ['先判断一项，否则两个平方数检查中的零可能模糊最小项数。', '判断 4 时必须除尽因子 4。', 'Python 使用 isqrt 做精确整数平方根。'], 'O(√n)', 'O(1)')

add(322, '零钱兑换', 'coin-change', '中等', '动态规划',
    '每种面额的硬币有无限枚，求凑出 amount 所需的最少硬币数。无法恰好凑出时返回 -1。',
    ['1 ≤ coins.length ≤ 12', '1 ≤ coins[i] ≤ 2³¹-1', '0 ≤ amount ≤ 10000'],
    [([[1,2,5],11], 3, '5+5+1 使用三枚硬币。'), ([[2],3], -1, '无法凑出奇数金额。'), ([[1],0], 0, '金额为零时不需要硬币。')],
    'coinChange', [('coins','int[]'),('amount','int')], 'int',
    '''class Solution:
    def coinChange(self, coins: list[int], amount: int) -> int:
        # 可行解至多用 amount 枚，amount+1 表示不可达。
        unreachable = amount + 1
        dp = [0] + [unreachable] * amount
        for value in range(1, amount + 1):
            for coin in coins:
                if coin <= value:
                    # 枚举最后一枚硬币，它之前的金额更小。
                    dp[value] = min(dp[value], dp[value - coin] + 1)
        # 不可达状态不能直接作为硬币数返回。
        return dp[amount] if dp[amount] != unreachable else -1''',
    '''class Solution {
public:
    int coinChange(vector<int>& coins, int amount) {
        // 正面额保证任何可行方案不超过 amount 枚。
        vector<int> dp(amount + 1, amount + 1);
        dp[0] = 0;
        for (int value = 1; value <= amount; ++value) {
            for (int coin : coins) {
                // 最后一枚硬币为 coin，剩余方案已经计算。
                if (coin <= value) dp[value] = min(dp[value], dp[value - coin] + 1);
            }
        }
        // 保持初始哨兵意味着目标金额始终不可达。
        return dp[amount] == amount + 1 ? -1 : dp[amount];
    }
};''',
    '完全背包的最少数量问题。dp[x] 表示凑出 x 的最少硬币数，枚举最后一枚硬币进行转移。',
    ['初始化 dp[0]=0，其余为不可达。', '按金额递增枚举所有不超过当前金额的硬币。', '用 dp[x-coin]+1 更新 dp[x]。'],
    '最优方案必有最后一枚硬币 coin；去掉它后的部分必须是金额 x-coin 的最优方案，否则可以替换成更短方案。遍历所有最后面额并取最小，覆盖全部最优可能。',
    ['不能总取当前最大面额，一般面额下贪心会失败。', 'amount=0 应返回 0。', '哨兵加一要避免溢出，使用 amount+1 即可。'], 'O(amount × m)，m 为面额种数', 'O(amount)')

add(139, '单词拆分', 'word-break', '中等', '动态规划',
    '判断字符串 s 能否拆成若干个字典单词，要求按顺序拼接后恰好等于 s。字典中的单词可重复使用。',
    ['1 ≤ s.length ≤ 300', '1 ≤ wordDict.length ≤ 1000', '1 ≤ 单词长度 ≤ 20', '输入均为小写字母，字典单词互不相同'],
    [(['leetcode',['leet','code']], True, 'leet 与 code 可顺序拼接。'), (['catsandog',['cats','dog','sand','and','cat']], False, '没有合法拆分能覆盖整个字符串。'), (['aaaa',['a']], True, '同一个字典单词可多次使用。')],
    'wordBreak', [('s','string'),('wordDict','string[]')], 'bool',
    '''class Solution:
    def wordBreak(self, s: str, wordDict: list[str]) -> bool:
        trie = {}
        for word in wordDict:
            node = trie
            for char in word:
                node = node.setdefault(char, {})
            node['#'] = True
        # reachable[i] 表示前 i 个字符能够完整拆分。
        reachable = [False] * (len(s) + 1)
        reachable[0] = True
        for start in range(len(s)):
            if not reachable[start]:
                continue
            node = trie
            for end in range(start, len(s)):
                # 逐字符走字典树，避免创建和哈希大量切片。
                if s[end] not in node:
                    break
                node = node[s[end]]
                if '#' in node:
                    reachable[end + 1] = True
        # 必须覆盖整个字符串，而非仅匹配某个前缀。
        return reachable[-1]''',
    '''class Solution {
    struct Node {
        vector<int> next;
        bool terminal;
        Node() : next(26, -1), terminal(false) {}
    };
public:
    bool wordBreak(string s, vector<string>& wordDict) {
        vector<Node> trie(1);
        for (const string& word : wordDict) {
            int node = 0;
            for (char c : word) {
                int letter = c - 'a';
                if (trie[node].next[letter] == -1) {
                    int child = trie.size();
                    trie.emplace_back();
                    trie[node].next[letter] = child;
                }
                node = trie[node].next[letter];
            }
            trie[node].terminal = true;
        }
        // 可达前缀才可以作为下一个单词的起点。
        vector<bool> reachable(s.size() + 1, false);
        reachable[0] = true;
        for (int start = 0; start < (int)s.size(); ++start) {
            if (!reachable[start]) continue;
            int node = 0;
            for (int end = start; end < (int)s.size(); ++end) {
                // 字典树分支不存在时，更长子串也无需检查。
                node = trie[node].next[s[end] - 'a'];
                if (node == -1) break;
                if (trie[node].terminal) reachable[end + 1] = true;
            }
        }
        // 终点可达才代表完整拆分。
        return reachable.back();
    }
};''',
    '用字典树加速单词匹配，再用可达性动态规划判断哪些前缀能够拆分。',
    ['构造字典树，在每个完整单词结点标记终点。', '令空前缀可达，从每个可达下标沿字典树向后匹配。', '匹配到完整单词时标记其后一个下标可达。'],
    '可达下标表示其前缀存在合法拆分。从这个下标沿树读到一个单词，就能把它接到已有拆分之后，因此所有标记均合法；反过来，任何合法拆分的每个单词都在树中，按顺序会逐一标记所有边界，包括终点。',
    ['只能从可达下标开始匹配，不能忽略前面的字符。', '可重复使用字典词，不要在匹配后删除单词。', '字典树扩容后不要继续使用失效的 C++ 引用。'], 'O(W + n·L)，W 为字典总字符数，L 为最大单词长度', 'O(W + n)')

add(300, '最长递增子序列', 'longest-increasing-subsequence', '中等', '动态规划',
    '从数组中按原顺序选择若干元素，可以跳过元素。返回所能得到的严格递增子序列的最大长度。',
    ['1 ≤ nums.length ≤ 2500', '-10000 ≤ nums[i] ≤ 10000'],
    [([[10,9,2,5,3,7,101,18]], 4, '例如 2、3、7、18。'), ([[7,7,7]], 1, '相等元素不能扩展严格递增序列。'), ([[1]], 1, '一个元素本身就是长度为 1 的递增序列。')],
    'lengthOfLIS', [('nums','int[]')], 'int',
    '''from bisect import bisect_left

class Solution:
    def lengthOfLIS(self, nums: list[int]) -> int:
        # tails[i] 是长度为 i+1 的递增子序列能够拥有的最小结尾。
        tails = []
        for value in nums:
            index = bisect_left(tails, value)
            if index == len(tails):
                # 大于所有结尾时，最长长度可以增加一。
                tails.append(value)
            else:
                # 替换为更小的结尾，为后续扩展创造条件。
                tails[index] = value
        return len(tails)''',
    '''class Solution {
public:
    int lengthOfLIS(vector<int>& nums) {
        // 下标 i 记录长度 i+1 的子序列最小结尾。
        vector<int> tails;
        for (int value : nums) {
            auto position = lower_bound(tails.begin(), tails.end(), value);
            // 相等值只替换，不能增加严格递增序列的长度。
            if (position == tails.end()) tails.push_back(value);
            else *position = value;
        }
        // tails 本身未必是原数组的子序列，但长度就是答案。
        return tails.size();
    }
};''',
    '维护各长度的最小结尾，用二分找到当前值应该改善哪一种长度。较小的结尾始终更有利于后续扩展。',
    ['tails[i] 表示长度 i+1 的最小结尾。', '找到第一个大于等于当前值的位置，并替换。', '若不存在这样的位置，在末尾追加，答案加一。'],
    '若第一个不小于 value 的位置为 i，则长度 i 的最小结尾严格小于 value，可接上它形成长度 i+1；更长序列的最小结尾不小于 value，不能接上它。替换只改善结尾，不损失可行长度，归纳可知最终长度最优。',
    ['严格递增要找第一个大于等于的位置，而非第一个大于的位置。', 'tails 保存的是最优结尾，不保证整体就是一条真实子序列。'], 'O(n log n)', 'O(n)')

add(152, '乘积最大子数组', 'maximum-product-subarray', '中等', '动态规划',
    '在非空整数数组中选择一个非空连续子数组，返回其元素乘积的最大值。',
    ['1 ≤ nums.length ≤ 20000', '-10 ≤ nums[i] ≤ 10', '任意子数组的乘积都在 32 位有符号整数范围内'],
    [([[2,3,-2,4]], 6, '选择连续的 2、3。'), ([[-2,0,-1]], 0, '不能跳过 0 将两个负数相乘。'), ([[-2,3,-4]], 24, '负数可以把之前的最小乘积变成最大值。')],
    'maxProduct', [('nums','int[]')], 'int',
    '''class Solution:
    def maxProduct(self, nums: list[int]) -> int:
        # 同时保存以当前位置结尾的最大和最小乘积。
        largest = smallest = answer = nums[0]
        for index in range(1, len(nums)):
            value = nums[index]
            # 必须先保存旧状态，负数会交换大小关系。
            from_largest = largest * value
            from_smallest = smallest * value
            largest = max(value, from_largest, from_smallest)
            smallest = min(value, from_largest, from_smallest)
            # 最优子数组可以结束在任何位置。
            answer = max(answer, largest)
        return answer''',
    '''class Solution {
public:
    int maxProduct(vector<int>& nums) {
        // 状态必须包含最小乘积，因为再乘负数可能成为最大。
        int largest = nums[0], smallest = nums[0], answer = nums[0];
        for (int i = 1; i < (int)nums.size(); ++i) {
            int value = nums[i];
            int fromLargest = largest * value, fromSmallest = smallest * value;
            // 也可以从当前元素重新开始一段。
            largest = max({value, fromLargest, fromSmallest});
            smallest = min({value, fromLargest, fromSmallest});
            // 记录所有结尾位置中最大的结果。
            answer = max(answer, largest);
        }
        return answer;
    }
};''',
    '每个位置同时维护最大与最小的结尾乘积，处理负数引起的大小反转。',
    ['用第一个数初始化最大、最小和答案。', '新状态从当前值、旧最大乘当前值、旧最小乘当前值中选取。', '用最大状态更新全局答案。'],
    '以当前位置结尾的子数组，要么只有当前值，要么由前一位置结尾的子数组扩展。乘正数保持顺序、乘负数颠倒顺序、乘零归零，因此旧最大与旧最小足以覆盖所有候选极值。',
    ['不能只保存最大乘积。', '用同一轮已更新状态去算最小值会出错。', '子数组要求连续且非空。'], 'O(n)', 'O(1)')

add(416, '分割等和子集', 'partition-equal-subset-sum', '中等', '动态规划',
    '把正整数数组中的每个元素恰好分配给两个子集之一。判断能否使两个子集的元素和相同。',
    ['1 ≤ nums.length ≤ 200', '1 ≤ nums[i] ≤ 100'],
    [([[1,5,11,5]], True, '一组为 11，另一组为 1+5+5。'), ([[1,2,3,5]], False, '总和为奇数，不可能均分。'), ([[2]], False, '同一个元素不能使用两次。')],
    'canPartition', [('nums','int[]')], 'bool',
    '''class Solution:
    def canPartition(self, nums: list[int]) -> bool:
        total = sum(nums)
        if total % 2:
            return False
        target = total // 2
        # 第 j 位为 1 表示子集和 j 可达，初始只有和 0。
        reachable = 1
        mask = (1 << (target + 1)) - 1
        for value in nums:
            # 左移代表选择本元素；与旧状态合并代表可以不选。
            reachable |= reachable << value
            reachable &= mask
            # 位集一次并行更新多种金额，每个元素只使用一次。
            if (reachable >> target) & 1:
                return True
        return False''',
    '''class Solution {
public:
    bool canPartition(vector<int>& nums) {
        int total = accumulate(nums.begin(), nums.end(), 0);
        if (total % 2) return false;
        int target = total / 2;
        // 题目最大目标为 10000，用位集并行保存所有可达和。
        bitset<10001> reachable;
        reachable[0] = true;
        for (int value : nums) {
            // 右侧取本轮之前的状态，不会把同一元素重复使用。
            reachable |= reachable << value;
            // 只需检查目标位，无需读取整个状态数组。
            if (reachable[target]) return true;
        }
        return false;
    }
};''',
    '总和必须为偶数，问题转化为是否存在和为 total/2 的子集。用位集优化 0/1 背包，将整排布尔状态并行更新。',
    ['总和为奇数直接失败。', '用二进制位表示可达金额，初始只有第 0 位为 1。', '每个数 v 更新 reachable |= reachable << v，最后检查目标位。'],
    '处理一个元素时，所有旧可达和可选择不加它，也可恰好加它一次；两组状态的并集就是新可达集合。位移与按位或精确实现这一转移，最终目标位为 1 当且仅当有一半总和的子集。',
    ['只能每个元素使用一次，不能写成重复使用的完全背包。', 'C++ 位集容量依据本题最大总和确定。', 'Python 整数不是常数空间，位数随目标增长。'], 'Python O(n·⌈target/w⌉)，w 为大整数机器字位数；C++ O(n·⌈10001/w⌉)', 'Python O(target) 位；C++ 固定 10001 位')

add(32, '最长有效括号', 'longest-valid-parentheses', '困难', '动态规划',
    '给定只由左圆括号和右圆括号组成的字符串，求其中最长的、括号能够正确匹配的连续子串长度。',
    ['0 ≤ s.length ≤ 30000', '仅包含 ( 和 )'],
    [([')()())'], 4, '中间的 ()() 长度为 4。'), (['(()'], 2, '只有后两个字符构成完整匹配。'), ([''], 0, '空字符串没有有效括号。')],
    'longestValidParentheses', [('s','string')], 'int',
    '''class Solution:
    def longestValidParentheses(self, s: str) -> int:
        answer = 0
        left = right = 0
        for char in s:
            left += char == '('
            right += char == ')'
            if left == right:
                answer = max(answer, 2 * right)
            elif right > left:
                # 右括号过多，跨越这里的片段不可能有效。
                left = right = 0
        left = right = 0
        for index in range(len(s) - 1, -1, -1):
            left += s[index] == '('
            right += s[index] == ')'
            # 反向扫描补足正向扫描中左括号富余的情况。
            if left == right:
                answer = max(answer, 2 * left)
            elif left > right:
                left = right = 0
        # 两次只记录计数，无需下标栈或 DP 数组。
        return answer''',
    '''class Solution {
public:
    int longestValidParentheses(string s) {
        int answer = 0, left = 0, right = 0;
        for (char c : s) {
            if (c == '(') ++left;
            else ++right;
            if (left == right) answer = max(answer, 2 * right);
            // 正向中右括号富余时，重新选择候选起点。
            else if (right > left) left = right = 0;
        }
        left = right = 0;
        for (int i = (int)s.size() - 1; i >= 0; --i) {
            if (s[i] == '(') ++left;
            else ++right;
            // 反向处理左括号富余导致正向无法结算的子串。
            if (left == right) answer = max(answer, 2 * left);
            else if (left > right) left = right = 0;
        }
        // 最大值综合两个方向的所有合法候选。
        return answer;
    }
};''',
    '使用左右两次计数扫描，在 O(n) 时间内进一步把辅助空间降到常数。正向处理多余右括号，反向处理多余左括号。',
    ['正向扫描，左右括号数相等时更新答案，右括号更多时清零。', '反向扫描采用对称规则，左括号更多时清零。', '返回两个方向记录的最大长度。'],
    '正向清零后的任意前缀均满足左括号不少于右括号，计数相等时整段必合法。若最优段因其前面存在多余左括号而未在正向结算，反向会在这些左括号处建立边界并结算该段。两次扫描互补覆盖所有最长合法段。',
    ['只做正向扫描会漏掉 (() 这类输入。', '反向清零条件与正向相反。', '要求连续子串，不能将不相邻匹配对随意相加。'], 'O(n)', 'O(1)')

add(62, '不同路径', 'unique-paths', '中等', '动态规划',
    '在 m 行 n 列的网格中，从左上角走到右下角，每步只能向右或向下移动一格。返回不同移动路径的数量。',
    ['1 ≤ m, n ≤ 100', '答案不超过 2×10⁹'],
    [([3,7], 28, '共需 8 步，选择其中 2 步向下。'), ([1,5], 1, '单行只能一路向右。'), ([1,1], 1, '无需移动的空路径也算一种。')],
    'uniquePaths', [('m','int'),('n','int')], 'int',
    '''class Solution:
    def uniquePaths(self, m: int, n: int) -> int:
        total = m + n - 2
        choose = min(m - 1, n - 1)
        answer = 1
        # 路径等价于在全部移动中选择哪些位置向下。
        for index in range(1, choose + 1):
            # 逐步计算 C(total-choose+index, index)，每步都能整除。
            answer = answer * (total - choose + index) // index
        # 使用较少的那种移动次数，减少乘除次数。
        return answer''',
    '''class Solution {
public:
    int uniquePaths(int m, int n) {
        int total = m + n - 2, choose = min(m - 1, n - 1);
        long long answer = 1;
        // 组合数决定所有向下（或向右）移动的位置。
        for (int i = 1; i <= choose; ++i) {
            // 先乘再除，每一步都是一个整数的组合数。
            answer = answer * (total - choose + i) / i;
        }
        // 用 long long 保存中间乘积，最后结果满足 int 范围。
        return (int)answer;
    }
};''',
    '每条路径恰好包含 m-1 次向下和 n-1 次向右，因此等价于计算组合数 C(m+n-2, m-1)。采用整数递推避免阶乘溢出。',
    ['总步数为 m+n-2。', '利用组合数对称性取较小的选择数。', '通过乘除递推逐步计算组合数。'],
    '任意一组向下步的位置唯一确定一条路径，任意合法路径也唯一对应这组位置，两者构成一一映射。乘除递推正是组合数的阶乘约分形式，所以结果等于路径数。',
    ['位置数是 m+n-2，不是 m+n。', '先整除可能丢失精度，应先乘再除。', '直接算阶乘容易溢出。'], 'O(min(m,n)) 次整数运算', 'O(1)')

add(64, '最小路径和', 'minimum-path-sum', '中等', '动态规划',
    '非负整数网格中，每步只能向右或向下移动。从左上角到右下角，返回沿途所有格子的最小总和，包含起点与终点。',
    ['1 ≤ 行数, 列数 ≤ 200', '0 ≤ grid[i][j] ≤ 200'],
    [([[[1,3,1],[1,5,1],[4,2,1]]], 7, '沿上边到最右列再向下，和为 1+3+1+1+1。'), ([[[5]]], 5, '只有一个格子时答案就是它本身。'), ([[[1,2,3]]], 6, '单行只能向右走。')],
    'minPathSum', [('grid','int[][]')], 'int',
    '''class Solution:
    def minPathSum(self, grid: list[list[int]]) -> int:
        # 直接把网格改写为到该位置的最小路径和，节省辅助空间。
        for row in range(len(grid)):
            for column in range(len(grid[0])):
                if row == 0 and column == 0:
                    continue
                if row == 0:
                    # 第一行只能从左边进入。
                    grid[row][column] += grid[row][column - 1]
                elif column == 0:
                    grid[row][column] += grid[row - 1][column]
                else:
                    # 其他格子仅可能来自上方或左方。
                    grid[row][column] += min(grid[row - 1][column], grid[row][column - 1])
        return grid[-1][-1]''',
    '''class Solution {
public:
    int minPathSum(vector<vector<int>>& grid) {
        // 按行更新原网格，已经处理的位置保存最优前缀和。
        for (int row = 0; row < (int)grid.size(); ++row) {
            for (int column = 0; column < (int)grid[0].size(); ++column) {
                if (row == 0 && column == 0) continue;
                // 边界格子只有一个合法来源。
                if (row == 0) grid[row][column] += grid[row][column - 1];
                else if (column == 0) grid[row][column] += grid[row - 1][column];
                // 内部格子选择累计和较小的来源。
                else grid[row][column] += min(grid[row - 1][column], grid[row][column - 1]);
            }
        }
        return grid.back().back();
    }
};''',
    '将原网格原地作为动态规划表，每个位置等于自身值加上两种来路中较小的累计和。',
    ['起点保留自己的值。', '第一行与第一列沿唯一来路累计。', '其他位置取上方和左方较小值，再加当前格子值。'],
    '到达一个格子的最后一步只能来自上或左。对于固定来路，最小代价应由该来源的最小路径扩展；否则替换成更短的来源路径可改善结果。按行更新时两处来源已算好，因此递推得到全局最小和。',
    ['此解法会修改 grid，需要保留原网格时请先复制。', '起点不能重复加一次。', '第一行和第一列需要单独处理。'], 'O(mn)', 'O(1) 辅助空间，原地修改输入')

add(5, '最长回文子串', 'longest-palindromic-substring', '中等', '字符串',
    '在字符串 s 中找到一个最长的连续回文子串。回文是正读与倒读相同的字符串；若有多个最长结果，返回任意一个。',
    ['1 ≤ s.length ≤ 1000', 's 只包含英文字母与数字'],
    [(['babad'], 'bab', 'bab 和 aba 都是合法的最长结果。'), (['cbbd'], 'bb', '需要处理偶数长度回文。'), (['a'], 'a', '单字符也是回文。')],
    'longestPalindrome', [('s','string')], 'string',
    '''class Solution:
    def longestPalindrome(self, s: str) -> str:
        # 插入分隔符后，奇数和偶数长度回文都变成单中心问题。
        text = '#' + '#'.join(s) + '#'
        radius = [0] * len(text)
        center = right = 0
        best_center = best_radius = 0
        for index in range(len(text)):
            if index < right:
                mirror = 2 * center - index
                # 镜像半径只可复用到当前已知右边界。
                radius[index] = min(right - index, radius[mirror])
            while (index - radius[index] - 1 >= 0
                   and index + radius[index] + 1 < len(text)
                   and text[index - radius[index] - 1] == text[index + radius[index] + 1]):
                radius[index] += 1
            if index + radius[index] > right:
                center, right = index, index + radius[index]
            if radius[index] > best_radius:
                best_center, best_radius = index, radius[index]
        # 转换串半径恰好等于原串回文长度。
        start = (best_center - best_radius) // 2
        return s[start:start + best_radius]''',
    '''class Solution {
public:
    string longestPalindrome(string s) {
        // 分隔符不在题目字符集中，可以统一奇偶长度。
        string text = "#";
        for (char c : s) { text.push_back(c); text.push_back('#'); }
        vector<int> radius(text.size(), 0);
        int center = 0, right = 0, bestCenter = 0, bestRadius = 0;
        for (int i = 0; i < (int)text.size(); ++i) {
            // 利用关于 center 的镜像，跳过已知相等的范围。
            if (i < right) radius[i] = min(right - i, radius[2 * center - i]);
            while (i - radius[i] - 1 >= 0 && i + radius[i] + 1 < (int)text.size()
                   && text[i - radius[i] - 1] == text[i + radius[i] + 1]) ++radius[i];
            if (i + radius[i] > right) { center = i; right = i + radius[i]; }
            if (radius[i] > bestRadius) { bestCenter = i; bestRadius = radius[i]; }
        }
        // 映射回原字符串：起点减半，长度取转换串半径。
        int start = (bestCenter - bestRadius) / 2;
        return s.substr(start, bestRadius);
    }
};''',
    'Manacher 算法复用回文的镜像半径。把字符间插入 # 后，所有回文都围绕单个位置展开；已知回文内部的大部分比较可以跳过。',
    ['构造 #a#b#...#，radius[i] 表示以 i 为中心向一侧覆盖的长度。', '维护当前最靠右回文的中心 center 与右端 right；i 在其中时，从镜像位置复用 min(radius[mirror], right-i)。', '只对未知部分继续比较，更新最右边界和最大半径。', '原串起点为 (bestCenter-bestRadius)//2，长度为 bestRadius。'],
    '已知回文关于中心对称，镜像位置的半径在 right 边界以内可完整复用；超过边界的部分尚未证明，逐字符扩展后得到准确半径。每个中心都取得真实最长半径，因此最大者就是最长回文。未越界的复用无需重复比较，所有成功的未知扩展共同推动 right 最多走 O(n) 步，所以总时间为线性。',
    ['复用半径必须被 right-i 截断。', '需要区分转换串下标和原串下标。', '多个最长回文都应视为正确答案。'], 'O(n)', 'O(n)', compare='palindrome')

add(1143, '最长公共子序列', 'longest-common-subsequence', '中等', '动态规划',
    '给定两个字符串，求它们最长公共子序列的长度。子序列允许删除字符，但不能改变保留字符的相对顺序，不要求连续。',
    ['1 ≤ text1.length, text2.length ≤ 1000', '只包含小写字母'],
    [(['abcde','ace'], 3, '公共子序列 ace 长度为 3。'), (['abc','def'], 0, '没有公共字符。'), (['aaa','aa'], 2, '重复字符按下标分别匹配。')],
    'longestCommonSubsequence', [('text1','string'),('text2','string')], 'int',
    '''class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        if len(text1) < len(text2):
            text1, text2 = text2, text1
        # 短字符串作为列，使滚动数组尽可能小。
        dp = [0] * (len(text2) + 1)
        for first in text1:
            diagonal = 0
            for column, second in enumerate(text2, 1):
                previous_row = dp[column]
                if first == second:
                    # 相同字符接到左上角的公共子序列后。
                    dp[column] = diagonal + 1
                else:
                    dp[column] = max(dp[column], dp[column - 1])
                # 保存覆盖前的值，供下一列作为左上角。
                diagonal = previous_row
        return dp[-1]''',
    '''class Solution {
public:
    int longestCommonSubsequence(string text1, string text2) {
        if (text1.size() < text2.size()) swap(text1, text2);
        // 一行状态，列数取两个字符串中的较短长度。
        vector<int> dp(text2.size() + 1, 0);
        for (char first : text1) {
            int diagonal = 0;
            for (int column = 1; column <= (int)text2.size(); ++column) {
                int previousRow = dp[column];
                // 当前字符相同则匹配，否则舍弃一方最后字符。
                if (first == text2[column - 1]) dp[column] = diagonal + 1;
                else dp[column] = max(dp[column], dp[column - 1]);
                // 下一格需要尚未覆盖的上一行当前列。
                diagonal = previousRow;
            }
        }
        return dp.back();
    }
};''',
    '用前缀动态规划，相同字符匹配，不同字符舍弃其中一个。仅保存上一行并额外记录左上角。',
    ['空前缀与任意前缀的公共子序列长度为 0。', '末尾字符相同：取左上角+1；不同：取上方与左方较大值。', '逐行滚动，使用一个临时变量保存左上角旧值。'],
    '若两前缀末尾相同，可将这个共同末尾接到较短前缀的最优公共子序列后；若不同，最优子序列至少不使用其中一方末尾，因此来自删除一方末尾的两个子问题之一。递推覆盖所有情况。',
    ['子序列不要求连续，不要与最长公共子串混淆。', '更新前保存上一行的当前值。', 'dp[column-1] 已是当前行，而 dp[column] 更新前属于上一行。'], 'O(mn)', 'O(min(m,n)) 辅助空间')

add(72, '编辑距离', 'edit-distance', '中等', '动态规划',
    '每次可以插入一个字符、删除一个字符或替换一个字符。将 word1 转换成 word2，返回所需的最少操作次数。',
    ['0 ≤ word1.length, word2.length ≤ 500', '仅包含小写字母'],
    [(['horse','ros'], 3, '可替换 h 为 r，再删除多余的 r 与 e。'), (['','abc'], 3, '空串需要插入三个字符。'), (['same','same'], 0, '相同字符串无需操作。')],
    'minDistance', [('word1','string'),('word2','string')], 'int',
    '''class Solution:
    def minDistance(self, word1: str, word2: str) -> int:
        if len(word1) < len(word2):
            word1, word2 = word2, word1
        # 空串变为长度 j 的前缀，需要插入 j 个字符。
        dp = list(range(len(word2) + 1))
        for row, first in enumerate(word1, 1):
            diagonal = dp[0]
            dp[0] = row
            for column, second in enumerate(word2, 1):
                previous_row = dp[column]
                if first == second:
                    dp[column] = diagonal
                else:
                    # 上方对应删除，左方对应插入，左上对应替换。
                    dp[column] = 1 + min(previous_row, dp[column - 1], diagonal)
                # 在覆盖前保存左上角，避免混用两行状态。
                diagonal = previous_row
        return dp[-1]''',
    '''class Solution {
public:
    int minDistance(string word1, string word2) {
        if (word1.size() < word2.size()) swap(word1, word2);
        vector<int> dp(word2.size() + 1);
        // 空源前缀的代价为插入目标前缀全部字符。
        for (int j = 0; j < (int)dp.size(); ++j) dp[j] = j;
        for (int i = 1; i <= (int)word1.size(); ++i) {
            int diagonal = dp[0];
            dp[0] = i;
            for (int j = 1; j <= (int)word2.size(); ++j) {
                int previousRow = dp[j];
                if (word1[i - 1] == word2[j - 1]) dp[j] = diagonal;
                // 三种操作均消耗一步，选剩余子问题最小值。
                else dp[j] = 1 + min({previousRow, dp[j - 1], diagonal});
                // 下一列所需的左上角是当前列的旧值。
                diagonal = previousRow;
            }
        }
        return dp.back();
    }
};''',
    '前缀动态规划枚举最后一次编辑，用滚动数组压缩空间。编辑距离对称，可把较短字符串作为列。',
    ['初始化空串边界：转换为长度 j 的字符串需 j 次插入，反向需 j 次删除。', '末尾字符相同则继承左上角。', '末尾不同则在删除、插入、替换的代价中取最小，再加一。'],
    '两个末尾相同时可以不编辑这对字符。否则最优转换的最后一步必是删除、插入或替换，分别归约到三个更短的前缀问题。对全部选择取最小覆盖所有转换序列，故得到最少操作数。',
    ['空串是合法输入，边界不可遗漏。', '相同字符不额外增加一次操作。', '插入来源是当前行左侧，删除来源是上一行当前列。'], 'O(mn)', 'O(min(m,n)) 辅助空间')

add(136, '只出现一次的数字', 'single-number', '简单', '技巧',
    '非空整数数组中，恰有一个元素只出现一次，其余元素都出现两次。使用线性时间和常数额外空间找出唯一元素。',
    ['1 ≤ nums.length ≤ 30000', '-30000 ≤ nums[i] ≤ 30000', '除一个值出现一次外，其余值均出现两次'],
    [([[4,1,2,1,2]], 4, '成对出现的 1 和 2 被抵消。'), ([[-7]], -7, '唯一元素也可以是负数。')],
    'singleNumber', [('nums','int[]')], 'int',
    '''class Solution:
    def singleNumber(self, nums: list[int]) -> int:
        # 0 与任意整数异或，不改变整数。
        answer = 0
        for value in nums:
            # 异或满足交换律，相同的两个数最终互相抵消。
            answer ^= value
        # 所有出现两次的值归零，只留下唯一元素。
        return answer''',
    '''class Solution {
public:
    int singleNumber(vector<int>& nums) {
        // 以异或的单位元 0 开始累计。
        int answer = 0;
        for (int value : nums) {
            // a ^ a = 0，出现两次的元素会抵消。
            answer ^= value;
        }
        // 剩下的就是出现一次的值。
        return answer;
    }
};''',
    '将所有元素异或。成对的相同值抵消为 0，唯一值保留下来。',
    ['结果初始化为 0。', '依次与每个元素异或。', '返回累计结果。'],
    '异或满足结合律与交换律，可在逻辑上将所有成对相等元素移到一起。每对的异或为 0，0 与唯一元素的异或仍是该元素，所以算法正确。',
    ['此方法依赖其余元素恰好出现两次的条件。', '异或符号是 ^，不是乘方。'], 'O(n)', 'O(1)')

add(169, '多数元素', 'majority-element', '简单', '数组',
    '数组中保证存在一个出现次数严格大于数组长度一半的元素，返回这个元素。',
    ['1 ≤ nums.length ≤ 50000', '保证多数元素存在'],
    [([[2,2,1,1,1,2,2]], 2, '2 出现 4 次，严格超过 7 的一半。'), ([[9]], 9, '单个元素必为多数。')],
    'majorityElement', [('nums','int[]')], 'int',
    '''class Solution:
    def majorityElement(self, nums: list[int]) -> int:
        candidate = 0
        count = 0
        for value in nums:
            # 候选票数清零时，从当前值重新开始候选。
            if count == 0:
                candidate = value
            # 相同值投赞成票，不同值相互抵消。
            count += 1 if value == candidate else -1
        # 题目保证多数存在，因此最终候选无需二次验证。
        return candidate''',
    '''class Solution {
public:
    int majorityElement(vector<int>& nums) {
        int candidate = 0, count = 0;
        for (int value : nums) {
            // 先前票数全部抵消后，选一个新候选。
            if (count == 0) candidate = value;
            // 每次用一个不同元素抵消一个候选元素。
            count += value == candidate ? 1 : -1;
        }
        // 多数元素超过其余元素总数，必然存活。
        return candidate;
    }
};''',
    'Boyer–Moore 投票法不断抵消两个不同元素。多数元素数量超过其他元素总和，无法被完全抵消。',
    ['维护候选值和净票数。', '票数为零时换候选。', '相同值加一，不同值减一。'],
    '移除一对不同元素，不会改变原多数元素仍为剩余集合多数的性质。算法等价于持续做这样的成对移除，最终未抵消的候选只能是原多数元素。',
    ['严格超过一半，与最高频但未过半不同。', '若题目不保证多数存在，最终候选必须再统计验证。'], 'O(n)', 'O(1)')

add(75, '颜色分类', 'sort-colors', '中等', '双指针',
    '数组只含 0、1、2，分别代表三种颜色。原地重排，使所有 0 在前、1 在中、2 在后；不使用库排序。',
    ['1 ≤ nums.length ≤ 300', 'nums[i] 只能是 0、1、2'],
    [([[2,0,2,1,1,0]], [0,0,1,1,2,2], '原地将三种数分别聚集。'), ([[2,2,2]], [2,2,2], '全为一种颜色时无需改变结果。'), ([[1,0]], [0,1], '长度为 2 的边界情况。')],
    'sortColors', [('nums','int[]')], 'void',
    '''class Solution:
    def sortColors(self, nums: list[int]) -> None:
        zeros = index = 0
        twos = len(nums) - 1
        while index <= twos:
            if nums[index] == 0:
                # 0 放到左区间末尾，换来的值已知属于中间区。
                nums[zeros], nums[index] = nums[index], nums[zeros]
                zeros += 1
                index += 1
            elif nums[index] == 2:
                # 右端换来的元素尚未检查，index 不能前进。
                nums[index], nums[twos] = nums[twos], nums[index]
                twos -= 1
            else:
                # 1 留在中间，继续检查下一个未知位置。
                index += 1''',
    '''class Solution {
public:
    void sortColors(vector<int>& nums) {
        int zeros = 0, index = 0, twos = (int)nums.size() - 1;
        while (index <= twos) {
            if (nums[index] == 0) {
                // 左侧 [0, zeros) 始终全为 0。
                swap(nums[zeros++], nums[index++]);
            } else if (nums[index] == 2) {
                // 换来的值还未知，留在当前下标再次判断。
                swap(nums[index], nums[twos--]);
            } else {
                // 中间 [zeros, index) 始终全为 1。
                ++index;
            }
        }
    }
};''',
    '荷兰国旗三路划分。用左右边界收集 0 和 2，中间保留 1，扫描未知区域。',
    ['zeros 指向下一个 0 的位置，twos 指向下一个 2 的位置。', '遇 0 与 zeros 交换并同时前进；遇 2 与 twos 交换，仅缩小右边界。', '遇 1 直接前进，未知区间清空即完成。'],
    '循环始终保持 [0,zeros) 全是 0、[zeros,index) 全是 1、(twos,n) 全是 2，剩余 [index,twos] 未处理。每一步正确放置一个元素并缩小未知区间，因此结束时全数组有序。',
    ['交换右侧的 2 后不要递增 index。', '循环条件必须包含 index==twos 的最后一个未知元素。', '题目要求原地修改，返回值为 None/void。'], 'O(n)', 'O(1)', mutates=0)

add(31, '下一个排列', 'next-permutation', '中等', '双指针',
    '将数组原地改成按字典序紧接着它的排列。如果当前已是最大排列，则改成最小排列。数组可能含重复元素。',
    ['1 ≤ nums.length ≤ 100', '0 ≤ nums[i] ≤ 100'],
    [([[1,2,3]], [1,3,2], '这是字典序中最小的严格更大排列。'), ([[3,2,1]], [1,2,3], '最大排列回到最小排列。'), ([[1,1,5]], [1,5,1], '重复元素也按照字典序处理。'), ([[7]], [7], '单元素仅有一种排列。')],
    'nextPermutation', [('nums','int[]')], 'void',
    '''class Solution:
    def nextPermutation(self, nums: list[int]) -> None:
        pivot = len(nums) - 2
        # 找到最后一个上升位置，其右边必为非递增后缀。
        while pivot >= 0 and nums[pivot] >= nums[pivot + 1]:
            pivot -= 1
        if pivot >= 0:
            successor = len(nums) - 1
            while nums[successor] <= nums[pivot]:
                successor -= 1
            # 从右找第一个更大值，恰好是可用的最小增量。
            nums[pivot], nums[successor] = nums[successor], nums[pivot]
        left, right = pivot + 1, len(nums) - 1
        while left < right:
            # 后缀逆转为升序，得到固定前缀下最小的排列。
            nums[left], nums[right] = nums[right], nums[left]
            left += 1
            right -= 1''',
    '''class Solution {
public:
    void nextPermutation(vector<int>& nums) {
        int pivot = (int)nums.size() - 2;
        // 非递增后缀已经无法仅在内部变得更大。
        while (pivot >= 0 && nums[pivot] >= nums[pivot + 1]) --pivot;
        if (pivot >= 0) {
            int successor = (int)nums.size() - 1;
            while (nums[successor] <= nums[pivot]) --successor;
            // 用后缀中最小的更大值提升枢轴。
            swap(nums[pivot], nums[successor]);
        }
        // 枢轴不存在时逆转整个数组，否则只最小化后缀。
        reverse(nums.begin() + pivot + 1, nums.end());
    }
};''',
    '尽量只改变靠右的位置：提升最后一个可提升的数，再把后缀调成最小顺序。',
    ['从右找 nums[i]<nums[i+1] 的最后位置。', '从右找严格大于枢轴的第一个元素并交换。', '逆转枢轴右边的非递增后缀；若不存在枢轴则逆转全部。'],
    '非递增后缀已经是其元素的最大排列，要增大全排列必须改变更左位置。选择最后一个可提升位置保证前缀变化最小；选择后缀中最小的更大值保证该位置增量最小；后缀升序则使剩余部分最小，因此结果恰为下一个排列。',
    ['两个比较都需处理相等元素。', '完全降序时不存在枢轴，必须返回完全升序。', 'Python 使用切片逆转会引入线性辅助空间，此处用双指针。'], 'O(n)', 'O(1)', mutates=0)

add(287, '寻找重复数', 'find-the-duplicate-number', '中等', '双指针',
    '长度为 n+1 的数组中，每个值都在 1 到 n 之间。仅有一种值重复出现，它可能出现多次。不能修改数组，使用常数额外空间找出这个重复值。',
    ['1 ≤ n ≤ 100000', 'nums.length = n+1', '1 ≤ nums[i] ≤ n', '恰有一种值出现至少两次'],
    [([[1,3,4,2,2]], 2, '2 有两个来源下标。'), ([[3,1,3,4,2]], 3, '重复值为 3。'), ([[2,2,2,2,2]], 2, '同一个值可以重复超过两次。'), ([[1,1]], 1, '最小长度也会形成环。')],
    'findDuplicate', [('nums','int[]')], 'int',
    '''class Solution:
    def findDuplicate(self, nums: list[int]) -> int:
        slow = fast = 0
        while True:
            # 把 nums[i] 当作下一结点下标，快指针每次走两步。
            slow = nums[slow]
            fast = nums[nums[fast]]
            if slow == fast:
                break
        entrance = 0
        while entrance != slow:
            # 一个从起点出发，一个从相遇点出发，同时走一步。
            entrance = nums[entrance]
            slow = nums[slow]
        # 它们在环入口相遇，入口值就是重复数。
        return entrance''',
    '''class Solution {
public:
    int findDuplicate(vector<int>& nums) {
        int slow = 0, fast = 0;
        do {
            // 数组提供 next 指针，所有访问下标均在有效范围。
            slow = nums[slow];
            fast = nums[nums[fast]];
        } while (slow != fast);
        int entrance = 0;
        while (entrance != slow) {
            // 重置一个指针后等速移动，定位环入口。
            entrance = nums[entrance];
            slow = nums[slow];
        }
        // 起点 0 没有入边，环入口必须拥有两个不同来源。
        return entrance;
    }
};''',
    '把数组视为函数图 i→nums[i]。从 0 出发必然进入环，使用 Floyd 快慢指针找到环入口，即重复值。',
    ['从 0 出发，慢指针走一步，快指针走两步，直到相遇。', '将另一个指针放回 0，与慢指针同时每次走一步。', '第二次相遇的位置就是环入口。'],
    '所有值在 1..n 内，0 无入边，从 0 出发最终进入环。环入口同时被链外前驱和环内前驱指向，所以它的值至少出现两次，且题目保证只有一种重复值。设入环距离为 μ、环长为 λ，首次相遇时慢指针步数为 λ 的倍数；两指针分别从起点和相遇点再走 μ 步会同到入口。',
    ['本题值域保证 nums[nums[fast]] 不越界，普通任意数组不适用。', '答案是环入口的下标值，不是初次相遇点。', '初始指针相等，第一阶段要至少移动一次再判断。'], 'O(n)', 'O(1)')
